"""Item commands, snapshot reads and transaction-scoped availability checks."""

import hashlib
import json
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from math import ceil
from typing import Any

from fastapi import HTTPException

from app.core.errors import ConflictException, NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.mat_hang.cache import MatHangCache, filter_items
from app.modules.mat_hang.ports import MatHangRepository
from app.modules.mat_hang.schemas import (
    CatalogMeta,
    DanhMucMatHangResponse,
    ListMeta,
    MatHangCreate,
    MatHangListResponse,
    MatHangPatch,
    MatHangRead,
)


def generate_mat_hang_etag(item: Any) -> str:
    canonical = MatHangRead.model_validate(item).model_dump(mode="json")
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return f'"{digest}"'


def verify_if_match(if_match: str | None, current_etag: str) -> None:
    if not if_match or not if_match.strip():
        raise HTTPException(428, "Header 'If-Match' bắt buộc cho thao tác này")
    if if_match.strip().strip('"') != current_etag.strip().strip('"'):
        raise HTTPException(412, "Dữ liệu đã bị thay đổi; hãy tải lại")


class MatHangReader:
    def __init__(self, cache: MatHangCache):
        self.cache = cache

    async def danh_muc(self) -> DanhMucMatHangResponse:
        items = self.cache.snapshot().items
        return DanhMucMatHangResponse(data=list(items), meta=CatalogMeta(total=len(items)))

    async def list_mat_hang(
        self,
        *,
        q: str | None = None,
        loai_mat_hang: str | None = None,
        is_active: bool | None = None,
        don_vi_tinh: str | None = None,
        mau_sac: str | None = None,
        don_gia_min: int | None = None,
        don_gia_max: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort: str = "id",
    ) -> MatHangListResponse:
        records = filter_items(
            self.cache.snapshot(),
            q=q,
            loai_mat_hang=loai_mat_hang,
            is_active=is_active,
            don_vi_tinh=don_vi_tinh,
            mau_sac=mau_sac,
            don_gia_min=don_gia_min,
            don_gia_max=don_gia_max,
            sort=sort,
        )
        total = len(records)
        return MatHangListResponse(
            data=records[(page - 1) * page_size : page * page_size],
            meta=ListMeta(
                page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size)
            ),
        )

    async def get_mat_hang(self, item_id: int) -> tuple[MatHangRead, str]:
        item = self.cache.snapshot().by_id.get(item_id)
        if item is None:
            raise NotFoundException(message=f"Mặt hàng ID {item_id} không tồn tại")
        return item, generate_mat_hang_etag(item)


class InactiveMatHang(ConflictException):
    code = "mat_hang_ngung_hoat_dong"
    default_message = "Mặt hàng đã ngừng hoạt động, không thể sử dụng trong tài liệu mới"


class MatHangAvailabilityService:
    """Caller owns the transaction and keeps the shared row locks until commit."""

    def __init__(self, repository: MatHangRepository):
        self.repository = repository

    async def require_active_items(self, item_ids: Iterable[int]) -> None:
        await self.read_items(item_ids, lock=True)

    async def read_items(self, item_ids: Iterable[int], *, lock: bool) -> list[MatHangRead]:
        requested = set(item_ids)
        if not requested:
            return []
        if any(item_id > 2**31 - 1 for item_id in requested):
            raise NotFoundException(message="Mặt hàng không tồn tại")
        records = (
            await self.repository.lock_items(requested)
            if lock
            else await self.repository.read_items(requested)
        )
        if requested - {item.id for item in records}:
            raise NotFoundException(message="Một hoặc nhiều mặt hàng không tồn tại")
        if any(not item.is_active for item in records):
            raise InactiveMatHang()
        return records


class MatHangService:
    def __init__(
        self,
        repository: MatHangRepository,
        audit: AuditWriter,
        transaction: Transaction,
        cache: MatHangCache,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.cache = cache

    @asynccontextmanager
    async def _mutation(self) -> AsyncIterator[list[MatHangRead]]:
        # Same order for local writes and reloads: cache lock, then DB transaction.
        # Readers retain an immutable snapshot and never acquire this lock.
        async with self.cache.lock:
            self.cache.snapshot()
            prepared = None
            try:
                async with self.transaction:
                    changes: list[MatHangRead] = []
                    yield changes
                    prepared = self.cache.prepare(changes)
            except ConflictException:
                raise
            except BaseException:
                if prepared is not None:
                    # Commit outcome may be unknown (disconnect/cancellation).
                    self.cache.mark_unavailable()
                raise
            assert prepared is not None
            self.cache.publish(prepared)

    async def _audit(
        self, action: str, record: MatHangRead, actor: dict, before: MatHangRead | None = None
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="mat_hang",
                doi_tuong_id=record.id,
                thao_tac=action,
                du_lieu_sau=record.model_dump(mode="json"),
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
            )
        )

    async def create_mat_hang(self, payload: MatHangCreate, actor: dict) -> tuple[MatHangRead, str]:
        async with self._mutation() as changes:
            if await self.repository.find_duplicate(
                ma_mat_hang=payload.ma_mat_hang, sku=payload.sku
            ):
                raise ConflictException(message="Mã mặt hàng hoặc SKU đã tồn tại")
            record = await self.repository.add(payload)
            await self._audit("tao", record, actor)
            changes.append(record)
        return record, generate_mat_hang_etag(record)

    async def _locked_item(self, item_id: int, if_match: str | None) -> MatHangRead:
        record = await self.repository.get_for_update(item_id)
        if record is None:
            raise NotFoundException(message=f"Mặt hàng ID {item_id} không tồn tại")
        verify_if_match(if_match, generate_mat_hang_etag(record))
        return record

    async def patch_mat_hang(
        self, item_id: int, payload: MatHangPatch, if_match: str | None, actor: dict
    ) -> tuple[MatHangRead, str]:
        async with self._mutation() as changes:
            before = await self._locked_item(item_id, if_match)
            update = payload.model_dump(exclude_unset=True)
            immutable = {"ma_mat_hang", "sku", "loai_mat_hang", "don_vi_tinh"}
            changed = {
                key for key in immutable & update.keys() if update[key] != getattr(before, key)
            }
            if changed:
                refs = await self.repository.get_references(item_id)
                if (changed & {"ma_mat_hang", "sku"} and refs.has_any) or (
                    changed & {"loai_mat_hang", "don_vi_tinh"} and (refs.has_bom or refs.has_docs)
                ):
                    raise ConflictException(
                        message="Không thể thay đổi trường bất biến sau khi có tham chiếu"
                    )
            if await self.repository.find_duplicate(
                ma_mat_hang=update.get("ma_mat_hang"),
                sku=update.get("sku"),
                exclude_id=item_id,
            ):
                raise ConflictException(message="Mã mặt hàng hoặc SKU đã tồn tại")
            record = await self.repository.update(item_id, update)
            await self._audit("sua", record, actor, before)
            changes.append(record)
        return record, generate_mat_hang_etag(record)

    async def delete_mat_hang(self, item_id: int, if_match: str | None, actor: dict) -> None:
        async with self._mutation() as changes:
            before = await self._locked_item(item_id, if_match)
            record = before
            if before.is_active:
                record = await self.repository.update(item_id, {"is_active": False})
                await self._audit("vo_hieu_hoa", record, actor, before)
            changes.append(record)
