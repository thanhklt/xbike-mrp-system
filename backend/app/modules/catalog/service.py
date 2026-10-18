"""Catalog use cases and atomic creation with audit."""

from app.core.errors import NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.catalog.ports import CatalogRepository
from app.modules.catalog.schemas import PartCreate, PartResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class CatalogService:
    def __init__(self, repository: CatalogRepository, audit: AuditWriter, transaction: Transaction):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_entries(self, params: PageParams) -> PaginatedResponse[PartResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_entry(self, record_id: int) -> PartResponse:
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"mat_hang {record_id} not found")
        return record

    async def create_entry(self, payload: PartCreate, actor: dict) -> PartResponse:
        async with self.transaction:
            created = await self.repository.add(payload)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="mat_hang",
                    doi_tuong_id=created.record.id,
                    du_lieu_sau=created.snapshot,
                )
            )
        return created.record
