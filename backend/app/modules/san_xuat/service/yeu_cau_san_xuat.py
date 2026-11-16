"""Production request policy and atomic transitions (UC-23)."""

from datetime import datetime, timezone

from app.core.errors import (
    ForbiddenException,
    InvalidAssignee,
    InvalidInputException,
    InvalidWorkflowState,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
    ReferencedResource,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.mat_hang.ports import MatHangStockReader
from app.modules.mat_hang.service import InactiveMatHang
from app.modules.san_xuat.ports import (
    AssigneeReader,
    ProductionIssues,
    YeuCauSanXuatRepository,
)
from app.modules.san_xuat.schemas import (
    LenhRead,
    ListResponseMeta,
    ResponseMeta,
    YeuCauCreate,
    YeuCauDetailResponse,
    YeuCauListQuery,
    YeuCauListResponse,
    YeuCauPatch,
    YeuCauRead,
)
from app.modules.san_xuat.service.common import canonical_hash


def generate_yeu_cau_etag(record: YeuCauRead) -> str:
    return f'"{canonical_hash(record.model_dump(mode="json"))}"'


def _verify_if_match(if_match: str | None, record: YeuCauRead) -> None:
    if not if_match or not if_match.strip():
        raise PreconditionRequiredException()
    if if_match.strip() != generate_yeu_cau_etag(record):
        raise PreconditionFailedException()


def _require_manager(actor: dict) -> None:
    if "quan_ly" not in actor.get("roles", []):
        raise ForbiddenException()


def _require_scope(record: YeuCauRead, actor: dict) -> None:
    if "quan_ly" in actor.get("roles", []):
        return
    if "nhan_vien" not in actor.get("roles", []) or record.nhan_vien_duoc_giao_id != int(
        actor["sub"]
    ):
        raise ForbiddenException()


def _require_draft(record: YeuCauRead) -> None:
    if record.trang_thai != "nhap":
        raise InvalidWorkflowState()


def _cancel_ordering(orders: list[LenhRead]) -> list[LenhRead]:
    parents = {order.id: order.lenh_san_xuat_cha_id for order in orders}
    depths = {}
    for order in orders:
        path = {order.id}
        parent = parents[order.id]
        while parent is not None:
            if parent in path or parent not in parents:
                raise InvalidWorkflowState(message="Cây lệnh không hợp lệ")
            path.add(parent)
            parent = parents[parent]
        depths[order.id] = len(path)
    return sorted(orders, key=lambda order: (-depths[order.id], order.id))


class YeuCauSanXuatService:
    def __init__(
        self,
        repository: YeuCauSanXuatRepository,
        audit: AuditWriter,
        transaction: Transaction,
        items: MatHangStockReader,
        employees: AssigneeReader,
        issues: ProductionIssues,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.items = items
        self.employees = employees
        self.issues = issues

    async def _with_progress(self, records: list[YeuCauRead]) -> list[YeuCauRead]:
        if not records:
            return []
        totals = await self.issues.tong_da_xuat_thanh_pham([record.id for record in records])
        return [
            record.model_copy(
                update={
                    "so_luong_da_xuat": totals.get(record.id, 0),
                    "so_luong_con_phai_xuat": max(record.so_luong - totals.get(record.id, 0), 0),
                }
            )
            for record in records
        ]

    async def _require_request(
        self, request_id: int, actor: dict, *, lock: bool = False
    ) -> YeuCauRead:
        if request_id > 2**31 - 1:
            raise NotFoundException()
        record = (
            await self.repository.get_for_update(request_id)
            if lock
            else await self.repository.get_by_id(request_id)
        )
        if record is None or ("quan_ly" not in actor.get("roles", []) and record.trang_thai == "nhap"):
            raise NotFoundException()
        _require_scope(record, actor)
        return (await self._with_progress([record]))[0]

    async def _audit(
        self,
        kind: str,
        action: str,
        actor: dict,
        before,
        after,
        *,
        reason: str | None = None,
        trang_thai_truoc: str | None = None,
        trang_thai_sau: str | None = None,
    ) -> None:
        record = after if after is not None else before
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong=kind,
                doi_tuong_id=record.id,
                thao_tac=action,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else {},
                ly_do=reason,
                trang_thai_truoc=trang_thai_truoc,
                trang_thai_sau=trang_thai_sau,
            )
        )

    def _detail(self, record: YeuCauRead, request_id: str) -> tuple[YeuCauDetailResponse, str]:
        return (
            YeuCauDetailResponse(data=record, meta=ResponseMeta(request_id=request_id)),
            generate_yeu_cau_etag(record),
        )

    # UC-23 Lập và gửi yêu cầu sản xuất — A2; D5 (specs/use_cases/production/UC-23.md)
    async def list_entries(
        self, params: YeuCauListQuery, actor: dict, request_id: str
    ) -> YeuCauListResponse:
        if not {"quan_ly", "nhan_vien"}.intersection(actor.get("roles", [])):
            raise ForbiddenException()
        actor_id = None if "quan_ly" in actor["roles"] else int(actor["sub"])
        result = await self.repository.list_entries(params, actor_id)
        return YeuCauListResponse(
            data=await self._with_progress(result.items),
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    # UC-23 Lập và gửi yêu cầu sản xuất — A2; D5 (specs/use_cases/production/UC-23.md)
    async def get_entry(
        self, resource_id: int, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        return self._detail(await self._require_request(resource_id, actor), request_id)

    async def _validate_product(self, item_id: int) -> None:
        records = await self.items.read_items([item_id], lock=True)
        if not records[0].is_active:
            raise InactiveMatHang()
        if records[0].loai_mat_hang != "thanh_pham":
            raise InvalidInputException(message="mat_hang_id phải là thành phẩm")

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 4–6; A1 (specs/use_cases/production/UC-23.md)
    async def create_entry(
        self, payload: YeuCauCreate, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            await self._validate_product(payload.mat_hang_id)
            await self.employees.kiem_tra_nguoi_duoc_giao(
                payload.nhan_vien_duoc_giao_id, lock=True
            )
            created = (
                await self._with_progress([await self.repository.add(payload, int(actor["sub"]))])
            )[0]
            await self._audit(
                "yeu_cau_san_xuat", "tao", actor, None, created,
                trang_thai_truoc=None,
                trang_thai_sau="nhap",
            )
        return self._detail(created, request_id)

    async def patch_entry(
        self,
        resource_id: int,
        payload: YeuCauPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            changes = payload.model_dump(exclude_unset=True)
            await self._validate_product(changes.get("mat_hang_id", before.mat_hang_id))
            assignee = changes.get("nhan_vien_duoc_giao_id", before.nhan_vien_duoc_giao_id)
            if assignee is not None:
                await self.employees.kiem_tra_nguoi_duoc_giao(assignee, lock=True)
            updated = (
                await self._with_progress([await self.repository.update(resource_id, changes)])
            )[0]
            await self._audit("yeu_cau_san_xuat", "sua", actor, before, updated)
        return self._detail(updated, request_id)

    async def delete_entry(self, resource_id: int, actor: dict, if_match: str | None) -> None:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            if await self.repository.has_dependencies(resource_id):
                raise ReferencedResource()
            await self.repository.delete(resource_id)
            await self._audit("yeu_cau_san_xuat", "xoa_nhap", actor, before, None)

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 7–9; A3 (specs/use_cases/production/UC-23.md)
    async def gui(
        self, resource_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            try:
                await self._validate_product(before.mat_hang_id)
            except InactiveMatHang as exc:
                raise InvalidWorkflowState(
                    message="Thành phẩm đã ngừng hoạt động, không thể gửi yêu cầu"
                ) from exc
            try:
                await self.employees.kiem_tra_nguoi_duoc_giao(
                    before.nhan_vien_duoc_giao_id, lock=True
                )
            except (NotFoundException, InvalidAssignee) as exc:
                raise InvalidAssignee(
                    message="Nhân viên được giao đã bị khóa hoặc không còn hợp lệ"
                ) from exc
            bom_id = await self.repository.bom_dang_dung(before.mat_hang_id)
            after = await self.repository.update(
                resource_id,
                {"trang_thai": "da_gui", "bom_id": bom_id, "gui_at": datetime.now(timezone.utc)},
            )
            after = (await self._with_progress([after]))[0]
            await self._audit(
                "yeu_cau_san_xuat", "gui", actor, before, after,
                trang_thai_truoc="nhap",
                trang_thai_sau="da_gui",
            )
        return self._detail(after, request_id)

    async def _cancel_completions(self, documents, actor: dict, reason: str) -> None:
        for before in documents:
            if before.trang_thai == "nhap":
                await self.repository.xoa_chung_tu_nhap(before.id)
                await self._audit(
                    "chung_tu_hoan_thanh_san_xuat", "xoa_nhap", actor, before, None, reason=reason
                )
            elif before.trang_thai == "cho_duyet":
                after = await self.repository.tu_choi_chung_tu(before.id)
                await self._audit(
                    "chung_tu_hoan_thanh_san_xuat", "tu_choi", actor, before, after, reason=reason
                )

    async def huy(
        self, resource_id: int, reason: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            if before.trang_thai in {"da_huy", "hoan_thanh"}:
                raise InvalidWorkflowState()
            orders = await self.repository.lenh_cua_yeu_cau(resource_id, lock=True)
            order_ids = [order.id for order in orders]
            documents = await self.repository.chung_tu_hoan_thanh_cua_lenh(order_ids, lock=True)
            posted_issue = await self.issues.co_phieu_da_ghi_so(resource_id, order_ids)
            if posted_issue or any(document.trang_thai == "da_duyet" for document in documents):
                raise PostedProductionDependency()
            for order in _cancel_ordering(orders):
                if order.trang_thai != "da_huy":
                    await self.repository.huy_lenh(order.id)
                    canceled = order.model_copy(update={"trang_thai": "da_huy"})
                    await self._audit("lenh_san_xuat", "huy", actor, order, canceled, reason=reason)
            await self._cancel_completions(documents, actor, reason)
            await self.issues.huy_phieu_chua_ghi_so(
                resource_id, order_ids, reason, int(actor["sub"])
            )
            after = (
                await self._with_progress(
                    [await self.repository.update(resource_id, {"trang_thai": "da_huy"})]
                )
            )[0]
            await self._audit("yeu_cau_san_xuat", "huy", actor, before, after, reason=reason)
        return self._detail(after, request_id)
