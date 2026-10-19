"""Business logic, validation, transaction coordination and audit for mat_hang."""

import hashlib
import json
from math import ceil
from typing import Any

from fastapi import HTTPException, status

from app.core.errors import ConflictException, NotFoundException
from app.core.transactions import Transaction
from app.modules.catalog.models import Part as MatHang
from app.modules.mat_hang.ports import MatHangRepository
from app.modules.mat_hang.schemas import (
    ListMeta,
    MatHangCreate,
    MatHangListResponse,
    MatHangPatch,
    MatHangRead,
)

SORT_WHITELIST = {"id", "ma_mat_hang", "ten_mat_hang", "don_gia"}


def generate_mat_hang_etag(item: Any) -> str:
    """Generate a strong ETag from canonical representation."""
    canonical = {
        "id": item.id,
        "ma_mat_hang": item.ma_mat_hang,
        "sku": item.sku,
        "ten_mat_hang": item.ten_mat_hang,
        "loai_mat_hang": item.loai_mat_hang,
        "don_vi_tinh": item.don_vi_tinh,
        "mau_sac": item.mau_sac,
        "mo_ta": item.mo_ta,
        "don_gia": item.don_gia,
        "is_active": item.is_active,
    }
    raw = json.dumps(canonical, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f'"{digest}"'


def verify_if_match(if_match: str | None, current_etag: str) -> None:
    """Validate If-Match header against entity ETag."""
    if not if_match or not if_match.strip():
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Header 'If-Match' bắt buộc cho thao tác này.",
        )
    if if_match.strip().strip('"') != current_etag.strip().strip('"'):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Dữ liệu đã bị thay đổi bởi phiên khác (ETag không khớp).",
        )


def _to_snapshot(record: MatHang) -> dict:
    return {
        "id": record.id,
        "ma_mat_hang": record.ma_mat_hang,
        "sku": record.sku,
        "ten_mat_hang": record.ten_mat_hang,
        "loai_mat_hang": record.loai_mat_hang,
        "don_vi_tinh": record.don_vi_tinh,
        "mau_sac": record.mau_sac,
        "mo_ta": record.mo_ta,
        "don_gia": record.don_gia,
        "is_active": record.is_active,
    }


class MatHangService:
    def __init__(self, repository: MatHangRepository, transaction: Transaction):
        self.repository = repository
        self.transaction = transaction

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
        is_desc = sort.startswith("-")
        sort_field = sort[1:] if is_desc else sort
        if sort_field not in SORT_WHITELIST:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Trường sắp xếp không hợp lệ. Cho phép: {', '.join(sorted(SORT_WHITELIST))}",
            )

        if don_gia_min is not None and don_gia_max is not None and don_gia_min > don_gia_max:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="don_gia_min không được lớn hơn don_gia_max",
            )

        records, total = await self.repository.list_items(
            q=q,
            loai_mat_hang=loai_mat_hang,
            is_active=is_active,
            don_vi_tinh=don_vi_tinh,
            mau_sac=mau_sac,
            don_gia_min=don_gia_min,
            don_gia_max=don_gia_max,
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            is_desc=is_desc,
        )

        total_pages = ceil(total / page_size) if total > 0 else 0
        return MatHangListResponse(
            data=[MatHangRead.model_validate(r) for r in records],
            meta=ListMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
            ),
        )

    async def get_mat_hang(self, item_id: int) -> tuple[MatHangRead, str]:
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundException(message=f"Mặt hàng ID {item_id} không tồn tại.")
        etag = generate_mat_hang_etag(item)
        return MatHangRead.model_validate(item), etag

    async def create_mat_hang(
        self, payload: MatHangCreate, actor: dict
    ) -> tuple[MatHangRead, str]:
        existing = await self.repository.find_duplicate(
            ma_mat_hang=payload.ma_mat_hang,
            sku=payload.sku,
        )
        if existing:
            raise ConflictException(message="Mã mặt hàng hoặc SKU đã tồn tại trong hệ thống.")

        actor_id = int(actor["sub"]) if "sub" in actor else None
        item = MatHang(
            ma_mat_hang=payload.ma_mat_hang,
            sku=payload.sku,
            ten_mat_hang=payload.ten_mat_hang,
            loai_mat_hang=payload.loai_mat_hang,
            don_vi_tinh=payload.don_vi_tinh,
            mau_sac=payload.mau_sac,
            mo_ta=payload.mo_ta,
            don_gia=payload.don_gia,
            is_active=payload.is_active,
        )

        async with self.transaction:
            await self.repository.add(item)
            await self.repository.init_stock(item.id)
            await self.repository.log_audit(
                actor_id=actor_id,
                thao_tac="tao",
                record_id=item.id,
                before=None,
                after=_to_snapshot(item),
            )

        etag = generate_mat_hang_etag(item)
        return MatHangRead.model_validate(item), etag

    async def patch_mat_hang(
        self,
        item_id: int,
        payload: MatHangPatch,
        if_match: str | None,
        actor: dict,
    ) -> tuple[MatHangRead, str]:
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundException(message=f"Mặt hàng ID {item_id} không tồn tại.")

        current_etag = generate_mat_hang_etag(item)
        verify_if_match(if_match, current_etag)

        ref_info = await self.repository.get_reference_info(item_id)
        update_data = payload.model_dump(exclude_unset=True)

        if "ma_mat_hang" in update_data and update_data["ma_mat_hang"] != item.ma_mat_hang:
            if ref_info["has_any_ref"]:
                raise ConflictException(
                    message="Mã mặt hàng không thể thay đổi sau khi đã được tham chiếu."
                )
            dup = await self.repository.find_duplicate(
                ma_mat_hang=update_data["ma_mat_hang"], exclude_id=item_id
            )
            if dup:
                raise ConflictException(
                    message=f"Mã mặt hàng '{update_data['ma_mat_hang']}' đã được sử dụng."
                )

        if "sku" in update_data and update_data["sku"] != item.sku:
            if ref_info["has_any_ref"]:
                raise ConflictException(
                    message="SKU không thể thay đổi sau khi đã được tham chiếu."
                )
            dup = await self.repository.find_duplicate(
                sku=update_data["sku"], exclude_id=item_id
            )
            if dup:
                raise ConflictException(
                    message=f"SKU '{update_data['sku']}' đã được sử dụng."
                )

        if "loai_mat_hang" in update_data and update_data["loai_mat_hang"] != item.loai_mat_hang:
            if ref_info["has_bom"] or ref_info["has_docs"]:
                raise ConflictException(
                    message="Loại mặt hàng bất biến khi đã có BOM hoặc chứng từ tham chiếu."
                )

        if "don_vi_tinh" in update_data and update_data["don_vi_tinh"] != item.don_vi_tinh:
            if ref_info["has_bom"] or ref_info["has_docs"]:
                raise ConflictException(
                    message="Đơn vị tính bất biến khi đã có BOM hoặc chứng từ tham chiếu."
                )

        before_dict = _to_snapshot(item)
        for key, value in update_data.items():
            setattr(item, key, value)

        actor_id = int(actor["sub"]) if "sub" in actor else None
        async with self.transaction:
            await self.repository.update(item)
            await self.repository.log_audit(
                actor_id=actor_id,
                thao_tac="sua",
                record_id=item.id,
                before=before_dict,
                after=_to_snapshot(item),
            )

        new_etag = generate_mat_hang_etag(item)
        return MatHangRead.model_validate(item), new_etag

    async def delete_mat_hang(
        self,
        item_id: int,
        if_match: str | None,
        actor: dict,
    ) -> None:
        item = await self.repository.get_by_id(item_id)
        if item is None:
            raise NotFoundException(message=f"Mặt hàng ID {item_id} không tồn tại.")

        current_etag = generate_mat_hang_etag(item)
        verify_if_match(if_match, current_etag)

        ref_info = await self.repository.get_reference_info(item_id)
        if ref_info["has_any_ref"] or ref_info["ton_kho_qty"] > 0:
            raise ConflictException(
                message="Không thể xóa mặt hàng đã có dữ liệu tham chiếu hoặc tồn kho."
            )

        before_dict = _to_snapshot(item)
        actor_id = int(actor["sub"]) if "sub" in actor else None
        async with self.transaction:
            await self.repository.delete(item)
            await self.repository.log_audit(
                actor_id=actor_id,
                thao_tac="xoa_nhap",
                record_id=item_id,
                before=before_dict,
                after=None,
            )
