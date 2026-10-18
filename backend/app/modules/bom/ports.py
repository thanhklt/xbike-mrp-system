"""Persistence operations required by bom use cases."""

from typing import Protocol

from app.modules.bom.schemas import BOMHeaderCreate, BOMHeaderResponse
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class BomRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[BOMHeaderResponse]: ...

    async def get_by_id(self, record_id: int) -> BOMHeaderResponse | None: ...

    async def add(self, payload: BOMHeaderCreate) -> CreatedRecord[BOMHeaderResponse]: ...
