"""Persistence operations required by receiving use cases."""

from datetime import datetime
from typing import Protocol

from app.modules.receiving.schemas import GoodsReceiptNoteCreate, GoodsReceiptNoteResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class ReceivingRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[GoodsReceiptNoteResponse]: ...

    async def get_by_id(self, record_id: int) -> GoodsReceiptNoteResponse | None: ...

    async def add(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> CreatedRecord[GoodsReceiptNoteResponse]: ...
