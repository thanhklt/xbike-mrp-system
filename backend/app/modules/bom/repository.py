"""SQLAlchemy persistence for bom; no commit or business policy."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.bom.models import BOMHeader, BOMItem
from app.modules.bom.schemas import BOMHeaderCreate, BOMHeaderResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyBomRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[BOMHeaderResponse]:
        return await select_page(self.session, BOMHeader, BOMHeaderResponse, params)

    async def get_by_id(self, record_id: int) -> BOMHeaderResponse | None:
        return await select_by_id(self.session, BOMHeader, BOMHeaderResponse, record_id)

    async def add(self, payload: BOMHeaderCreate) -> CreatedRecord[BOMHeaderResponse]:
        record = BOMHeader(**payload.model_dump(exclude={"items"}))
        record.items = [BOMItem(**item.model_dump()) for item in payload.items]
        return await flush_created_record(
            self.session, record, BOMHeaderResponse, children=record.items
        )
