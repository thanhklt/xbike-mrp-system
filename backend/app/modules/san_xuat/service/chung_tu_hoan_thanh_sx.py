"""UC-30 completion policy, optimistic concurrency and atomic audit."""

from datetime import datetime, timezone

from app.core.errors import (
    ForbiddenException,
    InvalidWorkflowState,
    NotFoundException,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.san_xuat.ports import ChungTuHoanThanhRepository, YeuCauSanXuatRepository
from app.modules.san_xuat.schemas import (
    ChungTuCreate,
    ChungTuDetailResponse,
    ChungTuRead,
    ResponseMeta,
    YeuCauRead,
)
from app.modules.san_xuat.service.common import canonical_hash


def generate_chung_tu_etag(record: ChungTuRead) -> str:
    return f'"{canonical_hash(record.model_dump(mode="json"))}"'


def _require_employee(actor: dict) -> None:
    roles = actor.get("roles", [])
    if "nhan_vien" not in roles or "quan_ly" in roles:
        raise ForbiddenException()


def _require_scope(request: YeuCauRead, actor: dict) -> None:
    if "quan_ly" in actor.get("roles", []):
        return
    _require_employee(actor)
    if request.nhan_vien_duoc_giao_id != int(actor["sub"]):
        raise ForbiddenException()


class ChungTuHoanThanhService:
    def __init__(
        self, repository: ChungTuHoanThanhRepository, requests: YeuCauSanXuatRepository,
        audit: AuditWriter, transaction: Transaction,
    ):
        self.repository = repository
        self.requests = requests
        self.audit = audit
        self.transaction = transaction

    async def _request(self, resource_id: int, actor: dict, *, lock: bool = False) -> YeuCauRead:
        if resource_id > 2**31 - 1:
            raise NotFoundException()
        record = await (
            self.requests.get_for_update(resource_id) if lock
            else self.requests.get_by_id(resource_id)
        )
        if record is None:
            raise NotFoundException()
        _require_scope(record, actor)
        return record

    async def _completion(self, resource_id: int) -> ChungTuRead:
        if resource_id > 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.get_by_id(resource_id)
        if record is None:
            raise NotFoundException()
        return record

    def _detail(
        self, record: ChungTuRead | None, request_id: str,
    ) -> tuple[ChungTuDetailResponse, str | None]:
        return (
            ChungTuDetailResponse(data=record, meta=ResponseMeta(request_id=request_id)),
            generate_chung_tu_etag(record) if record else None,
        )

    async def _audit(
        self, action: str, actor: dict, before: ChungTuRead | None, after: ChungTuRead,
    ) -> None:
        await self.audit.append(CreationAudit(
            nhan_vien_id=int(actor["sub"]), loai_doi_tuong="chung_tu_hoan_thanh_san_xuat",
            doi_tuong_id=after.id, thao_tac=action,
            trang_thai_truoc=before.trang_thai if before else None,
            trang_thai_sau=after.trang_thai,
            du_lieu_truoc=before.model_dump(mode="json") if before else None,
            du_lieu_sau=after.model_dump(mode="json"),
        ))

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 2–5; A1 một chứng từ (specs/use_cases/production/UC-30.md)
    async def tao(
        self, payload: ChungTuCreate, actor: dict, request_id: str,
    ) -> tuple[ChungTuDetailResponse, str | None]:
        _require_employee(actor)
        async with self.transaction:
            request = await self._request(payload.yeu_cau_san_xuat_id, actor, lock=True)
            existing = await self.repository.get_by_request(request.id)
            if existing:
                raise InvalidWorkflowState(message=f"Yêu cầu đã có chứng từ hoàn thành #{existing.id}")
            if (
                request.trang_thai != "dang_thuc_hien" or request.started_at is None
                or (request.so_luong_can_san_xuat or 0) <= 0
            ):
                raise InvalidWorkflowState()
            created = await self.repository.add(
                request.id, request.so_luong_can_san_xuat, int(actor["sub"]),
            )
            await self._audit("tao", actor, None, created)
        return self._detail(created, request_id)

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 6; D3 xem theo quyền (specs/use_cases/production/UC-30.md)
    async def chi_tiet(
        self, resource_id: int, actor: dict, request_id: str,
    ) -> tuple[ChungTuDetailResponse, str | None]:
        record = await self._completion(resource_id)
        await self._request(record.yeu_cau_san_xuat_id, actor)
        return self._detail(record, request_id)

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 1; A1 mở chứng từ của yêu cầu (specs/use_cases/production/UC-30.md)
    async def cua_yeu_cau(
        self, resource_id: int, actor: dict, request_id: str,
    ) -> tuple[ChungTuDetailResponse, str | None]:
        request = await self._request(resource_id, actor)
        record = await self.repository.get_by_request(request.id)
        return self._detail(record, request_id)

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 8–9; A3 gửi lại trực tiếp (specs/use_cases/production/UC-30.md)
    async def gui(
        self, resource_id: int, actor: dict, if_match: str | None, request_id: str,
    ) -> tuple[ChungTuDetailResponse, str | None]:
        _require_employee(actor)
        async with self.transaction:
            reference = await self._completion(resource_id)
            request = await self._request(reference.yeu_cau_san_xuat_id, actor, lock=True)
            before = await self.repository.get_for_update(resource_id)
            if before is None:
                raise NotFoundException()
            if not if_match or not if_match.strip():
                raise PreconditionRequiredException()
            if if_match.strip() != generate_chung_tu_etag(before):
                raise PreconditionFailedException()
            if before.trang_thai not in {"nhap", "tu_choi"} or request.trang_thai != "dang_thuc_hien":
                raise InvalidWorkflowState()
            after = await self.repository.update(resource_id, {
                "trang_thai": "cho_duyet", "finish_time": datetime.now(timezone.utc),
                "nguoi_xu_ly_id": None, "xu_ly_at": None, "ly_do_tu_choi": None,
            })
            await self._audit("gui_lai" if before.trang_thai == "tu_choi" else "gui", actor, before, after)
        return self._detail(after, request_id)
