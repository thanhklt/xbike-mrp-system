"""Persistence operations required by production use cases."""

from datetime import datetime
from typing import Protocol

from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class ProductionRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[WorkOrderResponse]: ...

    async def get_by_id(self, record_id: int) -> WorkOrderResponse | None: ...

    async def add(
        self, payload: WorkOrderCreate, *, created_at: datetime
    ) -> CreatedRecord[WorkOrderResponse]: ...
