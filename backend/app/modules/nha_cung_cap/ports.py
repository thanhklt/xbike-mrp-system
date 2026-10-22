"""Persistence operations required by suppliers use cases."""

from typing import Protocol

from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapListQuery,
    SupplierCreate,
    SupplierResponse,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SupplierRepository(Protocol):
    async def list_suppliers(self, params: NhaCungCapListQuery) -> RecordPage[SupplierResponse]: ...

    async def lock_by_id(self, record_id: int) -> SupplierResponse | None: ...

    async def has_references(self, record_id: int) -> bool: ...

    async def update(self, record_id: int, changes: dict[str, str | None]) -> SupplierResponse: ...

    async def delete(self, record_id: int) -> None: ...

    async def list_entries(self, params: PageParams) -> RecordPage[SupplierResponse]: ...

    async def get_by_id(self, record_id: int) -> SupplierResponse | None: ...

    async def add(
        self, payload: SupplierCreate | NhaCungCapCreate
    ) -> CreatedRecord[SupplierResponse]: ...
