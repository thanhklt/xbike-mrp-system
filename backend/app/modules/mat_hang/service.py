"""Item commands, snapshot reads and transaction-scoped availability checks."""

from collections.abc import Iterable
from math import ceil
from typing import Any

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    NotFoundException,
)
from app.core.preconditions import make_etag, verify_if_match
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.bom.service import BomService, require_manager
from app.modules.mat_hang.cache import MatHangCache, filter_items
from app.modules.mat_hang.mutation import MatHangMutation
from app.modules.mat_hang.ports import MatHangRepository
from app.modules.mat_hang.schemas import (
    CatalogMeta,
    DanhMucMatHangResponse,
    ListMeta,
    MatHangCreate,
    MatHangListQuery,
    MatHangListResponse,
    MatHangPatch,
    MatHangRead,
)


def generate_mat_hang_etag(item: Any) -> str:
    return make_etag(MatHangRead.model_validate(item).model_dump(mode="json"))


class MatHangReader:
    def __init__(self, cache: MatHangCache, boms: BomService):
        self.cache = cache
        self.boms = boms

    @staticmethod
    def _require_reader(actor: dict) -> None:
        roles = actor.get("roles")
        if not isinstance(roles, (list, tuple, set, frozenset)) or not {
            "quan_tri_vien",
            "quan_ly",
            "nhan_vien",
        }.intersection(roles):
            raise ForbiddenException()

    async def danh_muc(self, actor: dict) -> DanhMucMatHangResponse:
        """UC-09: specs/use_cases/catalog/UC-09.md."""
        self._require_reader(actor)
        items = self.cache.snapshot().items
        return DanhMucMatHangResponse(data=list(items), meta=CatalogMeta(total=len(items)))

    async def list_mat_hang(self, params: MatHangListQuery, actor: dict) -> MatHangListResponse:
        """UC-09: combined filters and stable pagination, catalog/UC-09.md."""
        self._require_reader(actor)
        values = params.model_dump(exclude={"page", "page_size"})
        if params.is_active is not None:
            if params.loai_mat_hang == "linh_kien":
                raise InvalidInputException(message="Active state applies only to finished items")
            values["loai_mat_hang"] = "thanh_pham"
        records = filter_items(self.cache.snapshot(), **values)
        page, page_size = params.page, params.page_size
        total = len(records)
        return MatHangListResponse(
            data=records[(page - 1) * page_size : page * page_size],
            meta=ListMeta(
                page=page, page_size=page_size, total=total, total_pages=ceil(total / page_size)
            ),
        )

    async def get_mat_hang(self, item_id: int, actor: dict) -> tuple[MatHangRead, str]:
        """UC-09: specs/use_cases/catalog/UC-09.md, one item/context snapshot."""
        self._require_reader(actor)
        if not 0 < item_id <= 2**31 - 1:
            raise NotFoundException()
        return await self.boms.item_detail(item_id)


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
        mutation: MatHangMutation,
        boms: BomService,
    ):
        self.repository, self.audit, self.mutation, self.boms = repository, audit, mutation, boms

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
        """UC-10/16: item, initial formula and audit share a single mutation scope."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            await self.boms.lock_catalog()
            if await self.repository.find_duplicate(sku=payload.sku):
                raise ConflictException(message="SKU already exists")
            record = await self.repository.add(payload)
            if payload.bom is not None:
                await self.boms.create_initial_formula(record, payload.bom, actor)
            await self._audit("tao", record, actor)
            changes.append(record)
            result = await self.boms.item_detail(record.id)
        return result

    async def _locked_item(self, item_id: int, if_match: str | None) -> MatHangRead:
        await self.boms.lock_catalog()
        if not 0 < item_id <= 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.get_for_update(item_id)
        if record is None:
            raise NotFoundException()
        await self.boms.lock_item_versions(item_id)
        _, tag = await self.boms.item_detail(item_id)
        verify_if_match(if_match, tag)
        return record

    async def patch_mat_hang(
        self, item_id: int, payload: MatHangPatch, if_match: str | None, actor: dict
    ) -> tuple[MatHangRead, str]:
        """UC-11/12 dependent scope: state writes use the same BOM lifecycle rules."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            before = await self._locked_item(item_id, if_match)
            update = {
                key: value
                for key, value in payload.model_dump(exclude_unset=True).items()
                if value != getattr(before, key)
            }
            changed = bool(update)
            if "sku" in update or "don_vi_tinh" in update:
                refs = await self.repository.get_references(item_id)
                if "sku" in update and refs.has_any:
                    raise ConflictException(message="SKU cannot change after a reference or stock")
                if "don_vi_tinh" in update and (refs.has_bom or refs.has_docs):
                    raise ConflictException(message="Unit cannot change after a reference")
            if await self.repository.find_duplicate(sku=update.get("sku"), exclude_id=item_id):
                raise ConflictException(message="SKU already exists")
            active = update.pop("is_active", None)
            previous = before
            if active is False and before.loai_mat_hang == "linh_kien":
                raise InvalidInputException(message="Components cannot be stopped")
            if active is not None and active != before.is_active:
                if active:
                    await self.boms.reuse_last_for_item_in_transaction(item_id, actor)
                else:
                    await self.boms.stop_for_item_in_transaction(item_id, actor)
            if update:
                if active is not None and active != before.is_active:
                    previous, _ = await self.boms.item_detail(item_id)
                record = await self.repository.update(item_id, update)
                await self._audit("sua", record, actor, previous)
            result = await self.boms.item_detail(item_id)
            if changed:
                changes.append(result[0])
        return result

    async def delete_mat_hang(self, item_id: int, if_match: str | None, actor: dict) -> None:
        """UC-12/19: stop a finished item and its active formula; never hard-delete."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            before = await self._locked_item(item_id, if_match)
            if before.loai_mat_hang != "thanh_pham":
                raise InvalidInputException(message="Components cannot be stopped")
            if before.is_active:
                await self.boms.stop_for_item_in_transaction(item_id, actor)
                after, _ = await self.boms.item_detail(item_id)
                changes.append(after)
