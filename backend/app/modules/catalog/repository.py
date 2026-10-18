"""SQLAlchemy persistence for catalog; no commit or business policy."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.catalog.models import Part
from app.modules.catalog.schemas import PartCreate, PartResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyCatalogRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[PartResponse]:
        return await select_page(self.session, Part, PartResponse, params)

    async def get_by_id(self, record_id: int) -> PartResponse | None:
        return await select_by_id(self.session, Part, PartResponse, record_id)

    async def add(self, payload: PartCreate) -> CreatedRecord[PartResponse]:
        record = Part(**payload.model_dump(exclude={"items"}))
        return await flush_created_record(self.session, record, PartResponse)
