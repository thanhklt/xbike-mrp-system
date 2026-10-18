"""Persistence operations required by material_issuing use cases."""

from datetime import datetime
from typing import Protocol

from app.modules.material_issuing.schemas import (
    MaterialIssueRequestCreate,
    MaterialIssueRequestResponse,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class MaterialIssuingRepository(Protocol):
    async def list_entries(
        self, params: PageParams
    ) -> RecordPage[MaterialIssueRequestResponse]: ...

    async def get_by_id(self, record_id: int) -> MaterialIssueRequestResponse | None: ...

    async def add(
        self, payload: MaterialIssueRequestCreate, *, created_at: datetime
    ) -> CreatedRecord[MaterialIssueRequestResponse]: ...
