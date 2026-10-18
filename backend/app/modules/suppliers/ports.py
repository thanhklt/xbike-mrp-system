"""Persistence operations required by suppliers use cases."""

from typing import Protocol

from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SupplierRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[SupplierResponse]: ...

    async def get_by_id(self, record_id: int) -> SupplierResponse | None: ...

    async def add(self, payload: SupplierCreate) -> CreatedRecord[SupplierResponse]: ...
