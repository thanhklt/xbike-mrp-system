"""Contract v3 order policy, frozen demand and atomic workflow transitions."""

import hashlib
import json
from datetime import datetime, timezone

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidAssignee,
    InvalidWorkflowState,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.san_xuat.ports import AssigneeReader, LenhContext, LenhSanXuatRepository
from app.modules.san_xuat.schemas import (
    LenhListResponse,
    LenhPatch,
    LenhQuery,
    LenhResponse,
    ListResponseMeta,
    ResponseMeta,
    VatTuLenhRead,
    VatTuLenhResponse,
)


class LenhMissingMaterials(ConflictException):
    code = "chua_du_vat_tu_da_cap"
    default_message = "Chưa cấp đủ vật tư qua phiếu xuất đã duyệt"


def generate_lenh_etag(context: LenhContext) -> str:
    representation = {
        "lenh": context.document.model_dump(mode="json"),
        "yeu_cau_trang_thai": context.request_state,
        "vat_tu": [line.model_dump() for line in context.materials],
    }
    digest = hashlib.sha256(
        json.dumps(
            representation, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return f'"{digest}"'


class LenhSanXuatService:
    def __init__(
        self,
        repository: LenhSanXuatRepository,
        audit: AuditWriter,
        transaction: Transaction,
        employees: AssigneeReader,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.employees = employees

    @staticmethod
    def _role(actor: dict, allowed: set[str]) -> None:
        if not allowed.intersection(actor.get("roles", [])):
            raise ForbiddenException()

    async def _context(self, order_id: int, actor: dict, *, lock: bool) -> LenhContext:
        self._role(actor, {"quan_ly", "nhan_vien"})
        if order_id > 2**31 - 1:
            raise NotFoundException()
        context = await self.repository.get_context(order_id, lock=lock)
        if context is None:
            raise NotFoundException()
        if "quan_ly" not in actor["roles"] and context.document.nhan_vien_id != int(actor["sub"]):
            raise ForbiddenException()
        return context

    @staticmethod
    def _match(context: LenhContext, if_match: str | None) -> None:
        if not if_match or not if_match.strip():
            raise PreconditionRequiredException()
        if if_match.strip() != generate_lenh_etag(context):
            raise PreconditionFailedException()

    @staticmethod
    def _source(context: LenhContext) -> None:
        if context.request_state not in {"da_gui", "cho_bo_sung_vat_tu", "dang_thuc_hien"}:
            raise InvalidWorkflowState(message="Yêu cầu nguồn chưa gửi hoặc đã đóng")

    @staticmethod
    def _response(context: LenhContext, request_id: str) -> tuple[LenhResponse, str]:
        return LenhResponse(
            data=context.document, meta=ResponseMeta(request_id=request_id)
        ), generate_lenh_etag(context)

    async def _audit(
        self,
        operation: str,
        actor: dict,
        before: LenhContext,
        after: LenhContext,
        reason: str | None = None,
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="lenh_san_xuat",
                doi_tuong_id=before.document.id,
                thao_tac=operation,
                du_lieu_truoc=before.document.model_dump(mode="json"),
                du_lieu_sau=after.document.model_dump(mode="json"),
                ly_do=reason,
            )
        )

    async def list_entries(
        self, params: LenhQuery, actor: dict, request_id: str
    ) -> LenhListResponse:
        self._role(actor, {"quan_ly", "nhan_vien"})
        employee_id = None if "quan_ly" in actor["roles"] else int(actor["sub"])
        page = await self.repository.list_orders(params, employee_id)
        return LenhListResponse(
            data=page.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=page.total,
                total_pages=(page.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def get_entry(
        self, order_id: int, actor: dict, request_id: str
    ) -> tuple[LenhResponse, str]:
        return self._response(await self._context(order_id, actor, lock=False), request_id)

    async def materials(
        self, order_id: int, actor: dict, request_id: str
    ) -> tuple[VatTuLenhResponse, str]:
        context = await self._context(order_id, actor, lock=False)
        ready = (
            context.document.trang_thai == "da_gui"
            and context.request_state in {"da_gui", "cho_bo_sung_vat_tu", "dang_thuc_hien"}
            and all(line.so_luong_da_cap >= line.so_luong_can for line in context.materials)
        )
        return VatTuLenhResponse(
            data=VatTuLenhRead(
                lenh_san_xuat_id=order_id, du_dieu_kien_bat_dau=ready, chi_tiet=context.materials
            ),
            meta=ResponseMeta(request_id=request_id),
        ), generate_lenh_etag(context)

    async def patch_entry(
        self, order_id: int, payload: LenhPatch, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[LenhResponse, str]:
        self._role(actor, {"quan_ly"})
        async with self.transaction:
            before = await self._context(order_id, actor, lock=True)
            self._match(before, if_match)
            if before.document.trang_thai != "nhap":
                raise InvalidWorkflowState()
            if payload.nhan_vien_id is not None:
                await self.employees.kiem_tra_nguoi_duoc_giao(payload.nhan_vien_id, lock=True)
            if payload.nhan_vien_id == before.document.nhan_vien_id:
                return self._response(before, request_id)
            await self.repository.update_order(order_id, {"nhan_vien_id": payload.nhan_vien_id})
            after = await self._context(order_id, actor, lock=True)
            await self._audit("sua", actor, before, after)
            return self._response(after, request_id)

    async def send(
        self, order_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[LenhResponse, str]:
        self._role(actor, {"quan_ly"})
        async with self.transaction:
            before = await self._context(order_id, actor, lock=True)
            self._match(before, if_match)
            if before.document.trang_thai != "nhap":
                raise InvalidWorkflowState()
            self._source(before)
            if before.document.nhan_vien_id is None:
                raise InvalidAssignee()
            await self.employees.kiem_tra_nguoi_duoc_giao(before.document.nhan_vien_id, lock=True)
            await self.repository.update_order(order_id, {"trang_thai": "da_gui"})
            after = await self._context(order_id, actor, lock=True)
            await self._audit("gui", actor, before, after)
            return self._response(after, request_id)

    async def start(
        self, order_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[LenhResponse, str]:
        self._role(actor, {"nhan_vien"})
        async with self.transaction:
            before = await self._context(order_id, actor, lock=True)
            self._match(before, if_match)
            if before.document.trang_thai != "da_gui":
                raise InvalidWorkflowState()
            self._source(before)
            if any(line.so_luong_da_cap < line.so_luong_can for line in before.materials):
                raise LenhMissingMaterials()
            await self.repository.update_order(
                order_id, {"trang_thai": "dang_thuc_hien", "started_at": datetime.now(timezone.utc)}
            )
            progress = await self.repository.start_request(before.document.yeu_cau_san_xuat_id)
            if progress is not None:
                previous, current = progress
                await self.audit.append(
                    CreationAudit(
                        nhan_vien_id=int(actor["sub"]),
                        loai_doi_tuong="yeu_cau_san_xuat",
                        doi_tuong_id=previous.id,
                        thao_tac="sua",
                        du_lieu_truoc=previous.model_dump(mode="json"),
                        du_lieu_sau=current.model_dump(mode="json"),
                    )
                )
            after = await self._context(order_id, actor, lock=True)
            await self._audit("bat_dau", actor, before, after)
            return self._response(after, request_id)

    async def cancel(
        self, order_id: int, reason: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[LenhResponse, str]:
        self._role(actor, {"quan_ly"})
        async with self.transaction:
            before = await self._context(order_id, actor, lock=True)
            self._match(before, if_match)
            if before.document.trang_thai in {"hoan_thanh", "da_huy"}:
                raise InvalidWorkflowState()
            if await self.repository.has_posted_dependency(
                order_id
            ) or await self.repository.has_active_children(order_id):
                raise PostedProductionDependency(
                    message="Lệnh đã ghi sổ vật tư/đầu ra hoặc còn lệnh con hoạt động"
                )
            await self.repository.update_order(order_id, {"trang_thai": "da_huy"})
            after = await self._context(order_id, actor, lock=True)
            await self._audit("huy", actor, before, after, reason)
            return self._response(after, request_id)
