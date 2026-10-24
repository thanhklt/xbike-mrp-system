"""Persistence operations required by receiving use cases."""

from datetime import datetime
from typing import NamedTuple, Protocol

from app.modules.phieu_nhap.schemas import (
    GoodsReceiptNoteCreate,
    GoodsReceiptNoteResponse,
    PhieuNhapListQuery,
    PhieuNhapRead,
    ReceiptItemCreate,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class ReceiptPart(NamedTuple):
    id: int
    loai_mat_hang: str
    is_active: bool | None


class ReceiptPosting(NamedTuple):
    id: int
    chi_tiet_phieu_nhap_id: int
    mat_hang_id: int
    so_luong_bien_dong: int
    loai_giao_dich: str


class ReceivingRepository(Protocol):
    async def lock_receipt(self, record_id: int) -> PhieuNhapRead | None: ...

    async def receipt_postings(self, record_id: int) -> list[ReceiptPosting]: ...

    async def patch_draft(
        self, record_id: int, changes: dict, items: list[ReceiptItemCreate] | None
    ) -> PhieuNhapRead: ...

    async def delete_draft(self, record_id: int) -> None: ...

    async def mark_completed(self, record_id: int) -> PhieuNhapRead: ...

    async def list_receipts(self, params: PhieuNhapListQuery) -> RecordPage[PhieuNhapRead]: ...

    async def get_receipt(self, record_id: int) -> PhieuNhapRead | None: ...

    async def lock_supplier(self, record_id: int) -> bool: ...

    async def lock_parts(self, ids: list[int]) -> list[ReceiptPart]: ...

    async def add_draft(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> PhieuNhapRead: ...

    async def list_entries(self, params: PageParams) -> RecordPage[GoodsReceiptNoteResponse]: ...

    async def get_by_id(self, record_id: int) -> GoodsReceiptNoteResponse | None: ...

    async def add(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> CreatedRecord[GoodsReceiptNoteResponse]: ...
