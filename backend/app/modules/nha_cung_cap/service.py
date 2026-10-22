"""Supplier use cases and atomic creation with audit."""

from hashlib import sha256

from app.core.errors import NotFoundException
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.nha_cung_cap.errors import (
    SupplierPreconditionFailed,
    SupplierPreconditionRequired,
    SupplierReferenced,
)
from app.modules.nha_cung_cap.ports import SupplierRepository
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapDetailResponse,
    NhaCungCapListQuery,
    NhaCungCapListResponse,
    NhaCungCapPatch,
    NhaCungCapRead,
    SupplierCreate,
    SupplierResponse,
)
from app.modules.users.schemas import ListResponseMeta, ResponseMeta
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


def supplier_etag(record: SupplierResponse) -> str:
    return f'"{sha256(record.model_dump_json().encode()).hexdigest()}"'


def detail_response(
    record: SupplierResponse, request_id: str
) -> tuple[NhaCungCapDetailResponse, str]:
    return NhaCungCapDetailResponse(
        data=NhaCungCapRead.model_validate(record), meta=ResponseMeta(request_id=request_id)
    ), supplier_etag(record)


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

    async def get_supplier(
        self, record_id: int, request_id: str
    ) -> tuple[NhaCungCapDetailResponse, str]:
        if record_id > 2**31 - 1:
            raise NotFoundException()
        return detail_response(await self.get_entry(record_id), request_id)

    async def create_supplier(
        self, payload: NhaCungCapCreate, actor: dict, request_id: str
    ) -> tuple[NhaCungCapDetailResponse, str]:
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

    async def _lock_current(self, record_id: int, if_match: str | None) -> SupplierResponse:
        if record_id > 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.lock_by_id(record_id)
        if record is None:
            raise NotFoundException()
        if if_match is None:
            raise SupplierPreconditionRequired()
        if if_match.strip() != supplier_etag(record):
            raise SupplierPreconditionFailed()
        return record

    async def patch_supplier(
        self,
        record_id: int,
        payload: NhaCungCapPatch,
        if_match: str | None,
        actor: dict,
        request_id: str,
    ) -> tuple[NhaCungCapDetailResponse, str]:
        async with self.transaction:
            before = await self._lock_current(record_id, if_match)
            changes = {
                key: value
                for key, value in payload.model_dump(exclude_unset=True).items()
                if getattr(before, key) != value
            }
            if "ma_ncc" in changes and await self.repository.has_references(record_id):
                raise SupplierReferenced()
            after = before
            if changes:
                after = await self.repository.update(record_id, changes)
                await self.audit.append(
                    CreationAudit(
                        nhan_vien_id=int(actor["sub"]),
                        loai_doi_tuong="nha_cung_cap",
                        doi_tuong_id=record_id,
                        thao_tac="sua",
                        du_lieu_truoc=before.model_dump(mode="json"),
                        du_lieu_sau=after.model_dump(mode="json"),
                    )
                )
        return detail_response(after, request_id)

    async def delete_supplier(self, record_id: int, if_match: str | None, actor: dict) -> None:
        async with self.transaction:
            before = await self._lock_current(record_id, if_match)
            if await self.repository.has_references(record_id):
                raise SupplierReferenced()
            await self.repository.delete(record_id)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=int(actor["sub"]),
                    loai_doi_tuong="nha_cung_cap",
                    doi_tuong_id=record_id,
                    thao_tac="xoa_nhap",
                    du_lieu_truoc=before.model_dump(mode="json"),
                    du_lieu_sau=None,
                )
            )

    async def list_entries(self, params: PageParams) -> PaginatedResponse[SupplierResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_entry(self, record_id: int) -> SupplierResponse:
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"nha_cung_cap {record_id} not found")
        return record

    async def create_entry(self, payload: SupplierCreate, actor: dict) -> SupplierResponse:
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
        return created.record
