"""Supplier use cases and atomic creation with audit."""

from app.core.errors import ForbiddenException, NotFoundException
from app.core.preconditions import make_etag, verify_if_match
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
    NhaCungCapPatch,
    NhaCungCapRead,
    ResponseMeta,
    SupplierResponse,
)


def detail_response(record: SupplierResponse, request_id: str) -> NhaCungCapDetailResponse:
    return NhaCungCapDetailResponse(
        data=NhaCungCapRead.model_validate(record), meta=ResponseMeta(request_id=request_id)
    )


def require_supplier_role(actor: dict, *, write: bool = False) -> None:
    roles = actor.get("roles")
    allowed = {"quan_ly"} if write else {"quan_ly", "quan_tri_vien"}
    if not isinstance(roles, (list, tuple, set, frozenset)) or not allowed.intersection(roles):
        raise ForbiddenException()


def supplier_etag(record: SupplierResponse) -> str:
    return make_etag(NhaCungCapRead.model_validate(record).model_dump(mode="json"))


class SupplierService:
    def __init__(
        self, repository: SupplierRepository, audit: AuditWriter, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_suppliers(
        self, params: NhaCungCapListQuery, actor: dict, request_id: str
    ) -> NhaCungCapListResponse:
        """UC-13: specs/use_cases/catalog/UC-13.md."""
        require_supplier_role(actor)
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
        self, record_id: int, actor: dict, request_id: str
    ) -> tuple[NhaCungCapDetailResponse, str]:
        """UC-13: current supplier detail and strong validator."""
        require_supplier_role(actor)
        if not 0 < record_id <= 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.get_by_id(record_id)
        if record is None:
            raise NotFoundException(message=f"nha_cung_cap {record_id} not found")
        return detail_response(record, request_id), supplier_etag(record)

    async def create_supplier(
        self, payload: NhaCungCapCreate, actor: dict, request_id: str
    ) -> tuple[NhaCungCapDetailResponse, str]:
        """UC-14: specs/use_cases/catalog/UC-14.md, atomic create and audit."""
        require_supplier_role(actor, write=True)
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
        return detail_response(created.record, request_id), supplier_etag(created.record)

    async def patch_supplier(
        self,
        record_id: int,
        payload: NhaCungCapPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[NhaCungCapDetailResponse, str]:
        """UC-44: specs/use_cases/catalog/UC-44.md; lock, compare, diff and audit atomically."""
        require_supplier_role(actor, write=True)
        if not 0 < record_id <= 2**31 - 1:
            raise NotFoundException()
        async with self.transaction:
            before = await self.repository.get_for_update(record_id)
            if before is None:
                raise NotFoundException()
            verify_if_match(if_match, supplier_etag(before))
            values = {
                key: value
                for key, value in payload.model_dump(exclude_unset=True).items()
                if value != getattr(before, key)
            }
            after = before
            if values:
                after = await self.repository.update(record_id, values)
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
        return detail_response(after, request_id), supplier_etag(after)
