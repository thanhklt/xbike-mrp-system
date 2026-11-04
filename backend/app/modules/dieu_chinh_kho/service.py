"""Warehouse adjustment posting, failure tickets and ticket handling."""

from datetime import datetime, timezone
from hashlib import sha256

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    InvalidWorkflowState,
    NotFoundException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.schemas import CreationAudit
from app.modules.audit.service import AuditService
from app.modules.dieu_chinh_kho.errors import AdjustmentFailed
from app.modules.dieu_chinh_kho.ports import PhieuDieuChinhRepository, TicketDieuChinhRepository
from app.modules.dieu_chinh_kho.schemas import (
    INT_MAX,
    DongDieuChinhCreate,
    PhieuDieuChinhActionRead,
    PhieuDieuChinhActionResponse,
    PhieuDieuChinhCreate,
    PhieuDieuChinhListResponse,
    PhieuDieuChinhPatch,
    PhieuDieuChinhQuery,
    PhieuDieuChinhRead,
    PhieuDieuChinhResponse,
    TicketListQuery,
    TicketListResponse,
    TicketRead,
    TicketResponse,
)
from app.modules.inventory.ports import InventoryWriter, StockAdjustmentLine, StockShortage
from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta


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


class PhieuDieuChinhKhoService:
    def __init__(
        self,
        repository: PhieuDieuChinhRepository,
        tickets: TicketDieuChinhRepository,
        inventory: InventoryWriter,
        audit: AuditService,
        transaction: Transaction,
    ):
        self.repository = repository
        self.tickets = tickets
        self.inventory = inventory
        self.audit = audit
        self.transaction = transaction

    _require_manager = staticmethod(TicketDieuChinhService._require_manager)

    @staticmethod
    def response(record: PhieuDieuChinhRead, request_id: str) -> tuple[PhieuDieuChinhResponse, str]:
        etag = '"' + sha256(record.model_dump_json().encode()).hexdigest() + '"'
        return PhieuDieuChinhResponse(data=record, meta=ResponseMeta(request_id=request_id)), etag

    async def _action_response(
        self, record: PhieuDieuChinhRead, request_id: str, *, replay: bool
    ) -> tuple[PhieuDieuChinhActionResponse, str]:
        action = PhieuDieuChinhActionRead(
            **record.model_dump(),
            giao_dich_kho_ids=await self.repository.ledger_ids(record.id),
            da_ghi_so_truoc_do=replay,
        )
        return PhieuDieuChinhActionResponse(
            data=action, meta=ResponseMeta(request_id=request_id)
        ), self.response(record, request_id)[1]

    async def list_phieu(
        self, params: PhieuDieuChinhQuery, actor: dict, request_id: str
    ) -> PhieuDieuChinhListResponse:
        self._require_manager(actor)
        await self.repository.begin_read_snapshot()
        result = await self.repository.list_phieu(params)
        return PhieuDieuChinhListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def _get_phieu(self, phieu_id: int) -> PhieuDieuChinhRead:
        record = await self.repository.get_phieu(phieu_id) if phieu_id <= INT_MAX else None
        if record is None:
            raise NotFoundException()
        return record

    async def get_phieu(
        self, phieu_id: int, actor: dict, request_id: str
    ) -> tuple[PhieuDieuChinhResponse, str]:
        self._require_manager(actor)
        await self.repository.begin_read_snapshot()
        return self.response(await self._get_phieu(phieu_id), request_id)

    async def _lock_phieu(self, phieu_id: int, *, update: bool = False) -> PhieuDieuChinhRead:
        source_id = (
            await self.repository.peek_phieu_nhap_id(phieu_id) if phieu_id <= INT_MAX else None
        )
        if source_id is None:
            raise NotFoundException()
        await self.repository.lock_phieu_nhap(source_id, update=update)
        record = await self.repository.lock_phieu(phieu_id)
        if record is None:
            raise NotFoundException()
        return record

    def _check_etag(self, record: PhieuDieuChinhRead, if_match: str | None) -> None:
        if not if_match or not if_match.strip():
            raise PreconditionRequiredException()
        if if_match.strip() != self.response(record, "")[1]:
            raise PreconditionFailedException()

    @staticmethod
    def _require_draft(record: PhieuDieuChinhRead) -> None:
        if record.trang_thai != "nhap":
            raise InvalidWorkflowState()

    @staticmethod
    def _invalid_line(index: int, field: str, reason: str) -> None:
        error = InvalidInputException(message=reason)
        error.public_details = [{"field": f"chi_tiet[{index}].{field}", "reason": reason}]
        raise error

    async def _tinh_dong(self, phieu_nhap_id: int, inputs: list[DongDieuChinhCreate]) -> list[dict]:
        sources = await self.repository.nguon(
            phieu_nhap_id, [line.giao_dich_goc_id for line in inputs]
        )
        result = []
        for index, line in enumerate(inputs):
            source = sources.get(line.giao_dich_goc_id)
            if source is None:
                self._invalid_line(
                    index,
                    "giao_dich_goc_id",
                    "Giao dịch gốc phải là nhập vật tư của đúng phiếu nhập",
                )
            if source.so_luong_hieu_luc < 0:
                raise ConflictException(message="Lượng hiệu lực của nguồn không hợp lệ")
            delta = line.so_luong_dung - source.so_luong_hieu_luc
            if delta == 0:
                self._invalid_line(index, "so_luong_dung", "Biến động phải khác 0")
            if source.so_luong_hieu_luc > INT_MAX or not -INT_MAX - 1 <= delta <= INT_MAX:
                self._invalid_line(index, "so_luong_dung", "Số lượng vượt miền INT32")
            result.append(
                {
                    "mat_hang_id": source.mat_hang_id,
                    "giao_dich_goc_id": source.giao_dich_goc_id,
                    "chi_tiet_phieu_nhap_id": source.chi_tiet_phieu_nhap_id,
                    "so_luong_hieu_luc_truoc": source.so_luong_hieu_luc,
                    "so_luong_dung": line.so_luong_dung,
                    "so_luong_bien_dong": delta,
                }
            )
        return result

    @staticmethod
    def _same_lines(record: PhieuDieuChinhRead, lines: list[dict]) -> bool:
        old = [line.model_dump(exclude={"id"}) for line in record.chi_tiet]
        new = [
            {key: value for key, value in line.items() if key != "chi_tiet_phieu_nhap_id"}
            for line in lines
        ]
        return old == new

    async def _audit(
        self,
        action: str,
        before: PhieuDieuChinhRead | None,
        after: PhieuDieuChinhRead | None,
        actor_id: int,
    ) -> None:
        record = after if after is not None else before
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=actor_id,
                loai_doi_tuong="phieu_dieu_chinh_kho",
                doi_tuong_id=record.id,
                thao_tac=action,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else None,
            )
        )

    async def create(
        self, payload: PhieuDieuChinhCreate, actor: dict, request_id: str
    ) -> tuple[PhieuDieuChinhResponse, str]:
        self._require_manager(actor)
        async with self.transaction:
            state = await self.repository.lock_phieu_nhap(payload.phieu_nhap_id, update=False)
            if state is None:
                raise NotFoundException()
            if state != "hoan_thanh":
                raise InvalidWorkflowState()
            lines = await self._tinh_dong(payload.phieu_nhap_id, payload.chi_tiet)
            after = await self.repository.add_phieu(
                payload.phieu_nhap_id, int(actor["sub"]), payload.ly_do, lines
            )
            await self._audit("tao", None, after, int(actor["sub"]))
        return self.response(after, request_id)

    async def patch(
        self,
        phieu_id: int,
        payload: PhieuDieuChinhPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[PhieuDieuChinhResponse, str]:
        self._require_manager(actor)
        async with self.transaction:
            before = await self._lock_phieu(phieu_id)
            self._check_etag(before, if_match)
            self._require_draft(before)
            if payload.chi_tiet is not None:
                lines = await self._tinh_dong(before.phieu_nhap_id, payload.chi_tiet)
                if not self._same_lines(before, lines):
                    await self.repository.replace_lines(phieu_id, lines)
            if payload.ly_do is not None and payload.ly_do != before.ly_do:
                await self.repository.update_ly_do(phieu_id, payload.ly_do)
            after = await self._get_phieu(phieu_id)
            if before != after:
                await self._audit("sua", before, after, int(actor["sub"]))
        return self.response(after, request_id)

    async def delete(self, phieu_id: int, actor: dict, if_match: str | None) -> None:
        self._require_manager(actor)
        async with self.transaction:
            before = await self._lock_phieu(phieu_id)
            self._check_etag(before, if_match)
            self._require_draft(before)
            await self._audit("xoa_nhap", before, None, int(actor["sub"]))
            await self.repository.delete_draft(phieu_id)

    async def xac_nhan(
        self, phieu_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[PhieuDieuChinhActionResponse, str]:
        self._require_manager(actor)
        try:
            async with self.transaction:
                before = await self._lock_phieu(phieu_id, update=True)
                if before.trang_thai == "da_xac_nhan":
                    return await self._action_response(before, request_id, replay=True)
                self._check_etag(before, if_match)
                self._require_draft(before)
                checked_etag = self.response(before, "")[1]
                lines = await self._tinh_dong(
                    before.phieu_nhap_id,
                    [
                        DongDieuChinhCreate(
                            giao_dich_goc_id=line.giao_dich_goc_id, so_luong_dung=line.so_luong_dung
                        )
                        for line in before.chi_tiet
                    ],
                )
                if not self._same_lines(before, lines):
                    await self.repository.replace_lines(phieu_id, lines)
                await self.inventory.lock_balances([line["mat_hang_id"] for line in lines])
                posted_at = datetime.now(timezone.utc)
                await self.repository.mark_confirmed(phieu_id, posted_at)
                after = await self._get_phieu(phieu_id)
                await self.inventory.adjust_stock(
                    [
                        StockAdjustmentLine(line.id, line.mat_hang_id, line.so_luong_bien_dong)
                        for line in after.chi_tiet
                    ],
                    int(actor["sub"]),
                    posted_at,
                )
                await self._audit("xac_nhan", before, after, int(actor["sub"]))
                result = await self._action_response(after, request_id, replay=False)
            return result
        except StockShortage as shortage:
            # The inventory transaction has rolled back before any failure is persisted.
            return await self._ghi_nhan_loi(
                phieu_id, actor, checked_etag, lines, shortage, request_id
            )

    async def _ghi_nhan_loi(
        self,
        phieu_id: int,
        actor: dict,
        checked_etag: str,
        lines: list[dict],
        shortage: StockShortage,
        request_id: str,
    ) -> tuple[PhieuDieuChinhActionResponse, str]:
        async with self.transaction:
            before = await self._lock_phieu(phieu_id, update=True)
            if before.trang_thai == "da_xac_nhan":
                return await self._action_response(before, request_id, replay=True)
            self._require_draft(before)
            self._check_etag(before, checked_etag)
            if not self._same_lines(before, lines):
                await self.repository.replace_lines(phieu_id, lines)
            await self.repository.mark_failed(phieu_id)
            actor_id = int(actor["sub"])
            description = f"Phiếu {before.ma_phieu} không đủ tồn: " + "; ".join(
                f"mặt hàng {line['mat_hang_id']} thiếu {-line['so_luong_bien_dong'] - line['ton_hien_tai']}"
                for line in shortage.lines
            )
            ticket = await self.tickets.add_ticket(
                before.phieu_nhap_id,
                actor_id,
                description,
                [
                    {
                        "chi_tiet_phieu_nhap_id": line["chi_tiet_phieu_nhap_id"],
                        "mat_hang_id": line["mat_hang_id"],
                        "so_luong_hieu_luc_truoc": line["so_luong_hieu_luc_truoc"],
                        "so_luong_de_nghi": line["so_luong_dung"],
                        "so_luong_bien_dong": line["so_luong_bien_dong"],
                        "ton_kho_tai_thoi_diem": shortage.balances[line["mat_hang_id"]],
                    }
                    for line in lines
                ],
            )
            await self._audit("ghi_nhan_loi", before, await self._get_phieu(phieu_id), actor_id)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=actor_id,
                    loai_doi_tuong="ticket_loi_dieu_chinh",
                    doi_tuong_id=ticket.id,
                    thao_tac="ghi_nhan_loi",
                    du_lieu_sau=ticket.model_dump(mode="json"),
                )
            )
        raise AdjustmentFailed(
            message="Không đủ tồn để điều chỉnh; toàn bộ phiếu đã rollback.",
            details=shortage.lines,
            phieu_id=phieu_id,
            ticket_id=ticket.id,
        )
