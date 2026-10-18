"""SQLAlchemy persistence for production; no commit or business policy."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.production.models import WorkOrder, WorkOrderItem
from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyProductionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[WorkOrderResponse]:
        return await select_page(self.session, WorkOrder, WorkOrderResponse, params)

    async def get_by_id(self, record_id: int) -> WorkOrderResponse | None:
        return await select_by_id(self.session, WorkOrder, WorkOrderResponse, record_id)

    async def add(
        self, payload: WorkOrderCreate, *, created_at: datetime
    ) -> CreatedRecord[WorkOrderResponse]:
        record = WorkOrder(**payload.model_dump(exclude={"items"}), created_at=created_at)
        record.items = [WorkOrderItem(**item.model_dump()) for item in payload.items]
        return await flush_created_record(
            self.session, record, WorkOrderResponse, children=record.items
        )
