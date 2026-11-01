"""Supplier use cases and atomic creation with audit."""

from app.core.errors import NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.nha_cung_cap.ports import SupplierRepository
from app.modules.nha_cung_cap.schemas import (
    ListResponseMeta,
    NhaCungCapCreate,
    NhaCungCapDetailResponse,
    NhaCungCapListQuery,
    NhaCungCapListResponse,
    NhaCungCapRead,
    ResponseMeta,
    SupplierResponse,
)


def detail_response(record: SupplierResponse, request_id: str) -> NhaCungCapDetailResponse:
    return NhaCungCapDetailResponse(
        data=NhaCungCapRead.model_validate(record), meta=ResponseMeta(request_id=request_id)
    )


class SupplierService:
    def __init__(
        self, repository: SupplierRepository, audit: AuditWriter, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_suppliers(
        self, params: NhaCungCapListQuery, request_id: str
    ) -> NhaCungCapListResponse:
        result = await self.repository.list_suppliers(params)
        return NhaCungCapListResponse(
            data=[NhaCungCapRead.model_validate(record) for record in result.items],
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def get_supplier(self, record_id: int, request_id: str) -> NhaCungCapDetailResponse:
        if record_id > 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"nha_cung_cap {record_id} not found")
        return detail_response(record, request_id)

    async def create_supplier(
        self, payload: NhaCungCapCreate, actor: dict, request_id: str
    ) -> NhaCungCapDetailResponse:
        async with self.transaction:
            created = await self.repository.add(payload)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="nha_cung_cap",
                    doi_tuong_id=created.record.id,
                    du_lieu_sau=created.snapshot,
                )
            )
        return detail_response(created.record, request_id)
