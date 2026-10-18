"""FinishedGoodsIssuing use cases and atomic creation with audit."""

from datetime import datetime

from app.core.errors import IncorrectIssueType, NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.finished_goods_issuing.ports import FinishedGoodsIssuingRepository
from app.modules.finished_goods_issuing.schemas import (
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class FinishedGoodsIssuingService:
    def __init__(
        self,
        repository: FinishedGoodsIssuingRepository,
        audit: AuditWriter,
        transaction: Transaction,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_entries(
        self, params: PageParams
    ) -> PaginatedResponse[FinishedGoodsDispatchResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_entry(self, record_id: int) -> FinishedGoodsDispatchResponse:
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"phieu_xuat {record_id} not found")
        return record

    async def create_entry(
        self, payload: FinishedGoodsDispatchCreate, actor: dict
    ) -> FinishedGoodsDispatchResponse:
        if payload.loai_phieu != "xuat_thanh_pham":
            raise IncorrectIssueType()
        payload = payload.model_copy(update={"nhan_vien_id": int(actor["sub"])})
        async with self.transaction:
            created = await self.repository.add(payload, created_at=datetime.utcnow())
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="phieu_xuat",
                    doi_tuong_id=created.record.id,
                    du_lieu_sau=created.snapshot,
                )
            )
        return created.record
