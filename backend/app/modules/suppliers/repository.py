"""SQLAlchemy persistence for suppliers; no commit or business policy."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemySupplierRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[SupplierResponse]:
        return await select_page(self.session, Supplier, SupplierResponse, params)

    async def get_by_id(self, record_id: int) -> SupplierResponse | None:
        return await select_by_id(self.session, Supplier, SupplierResponse, record_id)

    async def add(self, payload: SupplierCreate) -> CreatedRecord[SupplierResponse]:
        record = Supplier(**payload.model_dump(exclude={"items"}))
        return await flush_created_record(self.session, record, SupplierResponse)
