"""Persistence operations required by finished_goods_issuing use cases."""

from datetime import datetime
from typing import Protocol

from app.modules.finished_goods_issuing.schemas import (
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class FinishedGoodsIssuingRepository(Protocol):
    async def list_entries(
        self, params: PageParams
    ) -> RecordPage[FinishedGoodsDispatchResponse]: ...

    async def get_by_id(self, record_id: int) -> FinishedGoodsDispatchResponse | None: ...

    async def add(
        self, payload: FinishedGoodsDispatchCreate, *, created_at: datetime
    ) -> CreatedRecord[FinishedGoodsDispatchResponse]: ...
