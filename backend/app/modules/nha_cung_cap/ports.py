"""Persistence operations required by suppliers use cases."""

from typing import Protocol

from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapListQuery,
    SupplierResponse,
)
from app.shared.records import CreatedRecord, RecordPage


class SupplierRepository(Protocol):
    async def list_suppliers(self, params: NhaCungCapListQuery) -> RecordPage[SupplierResponse]: ...

    async def get_by_id(self, record_id: int) -> SupplierResponse | None: ...

    async def add(self, payload: NhaCungCapCreate) -> CreatedRecord[SupplierResponse]: ...
