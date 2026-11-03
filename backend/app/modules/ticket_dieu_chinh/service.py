"""Ticket transitions, ownership and audit in one transaction."""

from datetime import datetime, timezone
from hashlib import sha256

from app.core.errors import (
    ForbiddenException,
    InvalidWorkflowState,
    NotFoundException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.schemas import CreationAudit
from app.modules.audit.service import AuditService
from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta
from app.modules.ticket_dieu_chinh.ports import TicketDieuChinhRepository
from app.modules.ticket_dieu_chinh.schemas import (
    INT_MAX,
    TicketListQuery,
    TicketListResponse,
    TicketRead,
    TicketResponse,
)


class TicketDieuChinhService:
    def __init__(
        self, repository: TicketDieuChinhRepository, audit: AuditService, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    @staticmethod
    def _require_manager(actor: dict) -> None:
        if "quan_ly" not in actor.get("roles", []):
            raise ForbiddenException()

    @staticmethod
    def response(record: TicketRead, request_id: str) -> tuple[TicketResponse, str]:
        etag = '"' + sha256(record.model_dump_json().encode()).hexdigest() + '"'
        return TicketResponse(data=record, meta=ResponseMeta(request_id=request_id)), etag

    async def list_tickets(
        self, params: TicketListQuery, actor: dict, request_id: str
    ) -> TicketListResponse:
        self._require_manager(actor)
        result = await self.repository.list_tickets(params)
        return TicketListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def get_ticket(
        self, ticket_id: int, actor: dict, request_id: str
    ) -> tuple[TicketResponse, str]:
        self._require_manager(actor)
        record = await self.repository.get_ticket(ticket_id) if ticket_id <= INT_MAX else None
        if record is None:
            raise NotFoundException()
        return self.response(record, request_id)

    async def _locked_ticket(self, ticket_id: int, actor: dict, if_match: str | None) -> TicketRead:
        self._require_manager(actor)
        record = await self.repository.lock_ticket(ticket_id) if ticket_id <= INT_MAX else None
        if record is None:
            raise NotFoundException()
        if not if_match or not if_match.strip():
            raise PreconditionRequiredException()
        if if_match.strip() != self.response(record, "")[1]:
            raise PreconditionFailedException()
        return record

    async def _audit(
        self, action: str, before: TicketRead, after: TicketRead, actor_id: int
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=actor_id,
                loai_doi_tuong="ticket_loi_dieu_chinh",
                doi_tuong_id=before.id,
                thao_tac=action,
                du_lieu_truoc=before.model_dump(mode="json"),
                du_lieu_sau=after.model_dump(mode="json"),
            )
        )

    async def claim_ticket(
        self, ticket_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[TicketResponse, str]:
        async with self.transaction:
            before = await self._locked_ticket(ticket_id, actor, if_match)
            if before.trang_thai != "cho_xu_ly":
                raise InvalidWorkflowState()
            actor_id = int(actor["sub"])
            after = await self.repository.claim_ticket(ticket_id, actor_id)
            await self._audit("nhan_xu_ly", before, after, actor_id)
        return self.response(after, request_id)

    async def resolve_ticket(
        self, ticket_id: int, result: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[TicketResponse, str]:
        async with self.transaction:
            before = await self._locked_ticket(ticket_id, actor, if_match)
            if before.trang_thai not in {"cho_xu_ly", "dang_xu_ly"}:
                raise InvalidWorkflowState()
            actor_id = int(actor["sub"])
            if before.trang_thai == "dang_xu_ly" and before.nguoi_xu_ly_id != actor_id:
                raise ForbiddenException()
            after = await self.repository.resolve_ticket(
                ticket_id, actor_id, result, datetime.now(timezone.utc)
            )
            await self._audit("giai_quyet", before, after, actor_id)
        return self.response(after, request_id)
