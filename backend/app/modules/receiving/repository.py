"""SQLAlchemy persistence for receiving; no commit or business policy."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.receiving.models import GoodsReceiptNote, ReceiptItem
from app.modules.receiving.schemas import GoodsReceiptNoteCreate, GoodsReceiptNoteResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyReceivingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[GoodsReceiptNoteResponse]:
        return await select_page(self.session, GoodsReceiptNote, GoodsReceiptNoteResponse, params)

    async def get_by_id(self, record_id: int) -> GoodsReceiptNoteResponse | None:
        return await select_by_id(
            self.session, GoodsReceiptNote, GoodsReceiptNoteResponse, record_id
        )

    async def add(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> CreatedRecord[GoodsReceiptNoteResponse]:
        record = GoodsReceiptNote(**payload.model_dump(exclude={"items"}), created_at=created_at)
        record.items = [ReceiptItem(**item.model_dump()) for item in payload.items]
        return await flush_created_record(
            self.session, record, GoodsReceiptNoteResponse, children=record.items
        )
