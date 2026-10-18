"""Production use cases and atomic creation with audit."""

from datetime import datetime

from app.core.errors import NotFoundException, WorkflowNotImplemented
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.production.ports import ProductionRepository
from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class ProductionService:
    def __init__(
        self, repository: ProductionRepository, audit: AuditWriter, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_entries(self, params: PageParams) -> PaginatedResponse[WorkOrderResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_entry(self, record_id: int) -> WorkOrderResponse:
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"lenh_san_xuat {record_id} not found")
        return record

    async def create_entry(self, payload: WorkOrderCreate, actor: dict) -> WorkOrderResponse:
        async with self.transaction:
            created = await self.repository.add(payload, created_at=datetime.utcnow())
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="lenh_san_xuat",
                    doi_tuong_id=created.record.id,
                    du_lieu_sau=created.snapshot,
                )
            )
        return created.record

    async def update_work_order_status(self, wo_id: int) -> None:
        raise WorkflowNotImplemented()
