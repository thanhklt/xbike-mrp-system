"""Persistence operations required by catalog use cases."""

from typing import Protocol

from app.modules.catalog.schemas import PartCreate, PartResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class CatalogRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[PartResponse]: ...

    async def get_by_id(self, record_id: int) -> PartResponse | None: ...

    async def add(self, payload: PartCreate) -> CreatedRecord[PartResponse]: ...
