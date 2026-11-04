"""Production request policy, deterministic planning and atomic transitions."""

import hashlib
import hmac
import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config.settings import settings
from app.core.errors import (
    BomCycleException,
    ChangedProductionPlan,
    ConflictException,
    ForbiddenException,
    InvalidAssignee,
    InvalidInputException,
    InvalidWorkflowState,
    MissingBomException,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
    ReferencedResource,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.mat_hang.ports import MatHangRead, MatHangStockReader
from app.modules.mat_hang.service import InactiveMatHang
from app.modules.san_xuat.ports import (
    ActiveBom,
    AssigneeReader,
    HoanThanhContext,
    HoanThanhOrder,
    HoanThanhOutput,
    HoanThanhPosting,
    HoanThanhRepository,
    PlanningBomReader,
    ProductionIssues,
    YeuCauSanXuatRepository,
)
from app.modules.san_xuat.schemas import (
    GuiYeuCauRead,
    GuiYeuCauResponse,
    HoanThanhActionRead,
    HoanThanhActionResponse,
    HoanThanhCreate,
    HoanThanhListResponse,
    HoanThanhPatch,
    HoanThanhQuery,
    HoanThanhRead,
    HoanThanhResponse,
    KeHoachPreview,
    KeHoachPreviewResponse,
    KeHoachRead,
    KeHoachResponse,
    LenhDuKien,
    LenhRead,
    ListResponseMeta,
    NhuCauDuKien,
    ResponseMeta,
    VatTuDuKien,
    YeuCauCreate,
    YeuCauDetailResponse,
    YeuCauListQuery,
    YeuCauListResponse,
    YeuCauPatch,
    YeuCauRead,
)

PLAN_AUDIENCE = "ke_hoach_san_xuat"


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def generate_yeu_cau_etag(record: YeuCauRead) -> str:
    return f'"{_canonical_hash(record.model_dump(mode="json"))}"'


def _verify_if_match(if_match: str | None, record: YeuCauRead) -> None:
    if not if_match or not if_match.strip():
        raise PreconditionRequiredException()
    if if_match.strip() != generate_yeu_cau_etag(record):
        raise PreconditionFailedException()


@dataclass(frozen=True)
class PlanCalculation:
    ton_thanh_pham: int
    so_luong_can_san_xuat: int
    lenh_du_kien: list[LenhDuKien]
    vat_tu: list[VatTuDuKien]
    thieu_bom: bool
    ton_da_doc: dict[int, int]

    @property
    def thieu_vat_tu(self) -> bool:
        return any(line.so_luong_thieu > 0 for line in self.vat_tu)

    @property
    def ket_qua_hash(self) -> str:
        return _canonical_hash(
            {
                "ton_thanh_pham": self.ton_thanh_pham,
                "so_luong_can_san_xuat": self.so_luong_can_san_xuat,
                "lenh": [order.model_dump(mode="json") for order in self.lenh_du_kien],
                "vat_tu": [line.model_dump(mode="json") for line in self.vat_tu],
                "thieu_bom": self.thieu_bom,
                "ton": self.ton_da_doc,
            }
        )


def calculate_plan(
    request: YeuCauRead, graph: dict[int, ActiveBom], items: dict[int, MatHangRead]
) -> PlanCalculation:
    """Consume a shared stock snapshot once across BFS branches; never reserve stock."""
    stock = {item_id: item.so_luong_ton for item_id, item in items.items()}
    finished_stock = stock[request.mat_hang_id]
    remaining = stock.copy()
    remaining[request.mat_hang_id] -= min(finished_stock, request.so_luong)
    production = max(request.so_luong - finished_stock, 0)
    orders: list[LenhDuKien] = []
    warehouse_needs: dict[int, int] = {}
    used_stock = {request.mat_hang_id: finished_stock}
    missing_bom = False
    pending: deque[tuple[int, int, str | None, frozenset[int]]] = deque()
    if production:
        pending.append((request.mat_hang_id, production, None, frozenset()))
    while pending:
        item_id, quantity, parent_code, ancestors = pending.popleft()
        # Shared DAG nodes may produce many orders; only an ancestor repeat is a cycle.
        if item_id in ancestors:
            raise BomCycleException()
        bom = graph.get(item_id)
        order = LenhDuKien(
            ma_tam=f"L{len(orders) + 1}",
            ma_cha_tam=parent_code,
            mat_hang_id=item_id,
            bom_id=bom.bom_id if bom else None,
            so_luong=quantity,
        )
        orders.append(order)
        if bom is None:
            missing_bom = True
            continue
        for component_id, per_unit in bom.components:
            need = per_unit * quantity
            if need > 2**31 - 1:
                raise InvalidInputException(message="Nhu cầu trực tiếp vượt giới hạn INT32")
            order.nhu_cau_truc_tiep.append(
                NhuCauDuKien(mat_hang_id=component_id, so_luong_can=need)
            )
            component = items[component_id]
            used_stock[component_id] = stock[component_id]
            if component.loai_mat_hang == "ban_thanh_pham":
                supplied = min(remaining[component_id], need)
                remaining[component_id] -= supplied
                if supplied:
                    warehouse_needs[component_id] = warehouse_needs.get(component_id, 0) + supplied
                if need > supplied:
                    pending.append(
                        (component_id, need - supplied, order.ma_tam, ancestors | {item_id})
                    )
            elif component.loai_mat_hang in {"nguyen_vat_lieu", "linh_kien"}:
                warehouse_needs[component_id] = warehouse_needs.get(component_id, 0) + need
            else:
                raise InvalidInputException(message="Thành phần BOM không hợp lệ")
    materials = [
        VatTuDuKien(
            mat_hang_id=item_id,
            ma_mat_hang=items[item_id].ma_mat_hang,
            ten_mat_hang=items[item_id].ten_mat_hang,
            don_vi_tinh=items[item_id].don_vi_tinh,
            so_luong_can_tu_kho=need,
            so_luong_hien_co=stock[item_id],
            so_luong_thieu=max(need - stock[item_id], 0),
        )
        for item_id, need in sorted(warehouse_needs.items())
    ]
    return PlanCalculation(finished_stock, production, orders, materials, missing_bom, used_stock)


def sign_plan_token(
    request: YeuCauRead,
    calculation: PlanCalculation,
    secret_key: str,
    algorithm: str,
    *,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    return jwt.encode(
        {
            "aud": PLAN_AUDIENCE,
            "iat": issued_at,
            "exp": issued_at + timedelta(minutes=10),
            "yeu_cau_san_xuat_id": request.id,
            "nhan_vien_duoc_giao_id": request.nhan_vien_duoc_giao_id,
            "so_luong": request.so_luong,
            "ket_qua_hash": calculation.ket_qua_hash,
        },
        secret_key,
        algorithm=algorithm,
    )


def verify_plan_token(
    token: str,
    request: YeuCauRead,
    calculation: PlanCalculation,
    secret_key: str,
    algorithm: str,
) -> None:
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
            audience=PLAN_AUDIENCE,
            options={"require_exp": True, "require_aud": True},
        )
    except JWTError as exc:
        raise ChangedProductionPlan() from exc
    expected = {
        "yeu_cau_san_xuat_id": request.id,
        "nhan_vien_duoc_giao_id": request.nhan_vien_duoc_giao_id,
        "so_luong": request.so_luong,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ChangedProductionPlan()
    digest = payload.get("ket_qua_hash")
    if (
        not isinstance(digest, str)
        or not digest.isascii()
        or not hmac.compare_digest(digest, calculation.ket_qua_hash)
    ):
        raise ChangedProductionPlan()


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
        boms: PlanningBomReader,
        issues: ProductionIssues,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.items = items
        self.employees = employees
        self.boms = boms
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
        if record is None:
            raise NotFoundException()
        _require_scope(record, actor)
        return (await self._with_progress([record]))[0]

    async def _audit(
        self, kind: str, action: str, actor: dict, before, after, *, reason: str | None = None
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
            )
        )

    def _detail(self, record: YeuCauRead, request_id: str) -> tuple[YeuCauDetailResponse, str]:
        return (
            YeuCauDetailResponse(data=record, meta=ResponseMeta(request_id=request_id)),
            generate_yeu_cau_etag(record),
        )

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

    async def get_entry(
        self, resource_id: int, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        return self._detail(await self._require_request(resource_id, actor), request_id)

    async def _validate_product(self, item_id: int) -> None:
        records = await self.items.read_items([item_id], lock=True)
        if records[0].loai_mat_hang != "thanh_pham":
            raise InvalidInputException(message="mat_hang_id phải là thành phẩm")

    async def create_entry(
        self, payload: YeuCauCreate, actor: dict, request_id: str
    ) -> tuple[YeuCauDetailResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            await self._validate_product(payload.mat_hang_id)
            if payload.nhan_vien_duoc_giao_id is not None:
                await self.employees.kiem_tra_nguoi_duoc_giao(
                    payload.nhan_vien_duoc_giao_id, lock=True
                )
            created = (
                await self._with_progress([await self.repository.add(payload, int(actor["sub"]))])
            )[0]
            await self._audit("yeu_cau_san_xuat", "tao", actor, None, created)
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

    async def _assignee_valid(self, record: YeuCauRead, *, lock: bool) -> bool:
        if record.nhan_vien_duoc_giao_id is None:
            return False
        try:
            await self.employees.kiem_tra_nguoi_duoc_giao(record.nhan_vien_duoc_giao_id, lock=lock)
        except (NotFoundException, InvalidAssignee):
            return False
        return True

    async def _calculate(self, record: YeuCauRead, *, lock: bool) -> PlanCalculation:
        if lock:
            await self.boms.lock_graph()
        graph = await self.boms.active_graph()
        reachable = {record.mat_hang_id}
        pending = [record.mat_hang_id]
        while pending:
            bom = graph.get(pending.pop())
            if bom:
                for component, _ in bom.components:
                    if component not in reachable:
                        reachable.add(component)
                        pending.append(component)
        items = await self.items.read_items(sorted(reachable), lock=lock)
        return calculate_plan(record, graph, {item.id: item for item in items})

    async def tinh_ke_hoach(
        self, resource_id: int, actor: dict, request_id: str
    ) -> KeHoachPreviewResponse:
        record = await self._require_request(resource_id, actor)
        _require_draft(record)
        result = await self._calculate(record, lock=False)
        valid_assignee = await self._assignee_valid(record, lock=False)
        now = datetime.now(timezone.utc)
        return KeHoachPreviewResponse(
            data=KeHoachPreview(
                yeu_cau_san_xuat_id=record.id,
                tinh_luc=now,
                ke_hoach_token=sign_plan_token(
                    record, result, settings.secret_key, settings.algorithm, now=now
                ),
                so_luong_yeu_cau=record.so_luong,
                ton_thanh_pham=result.ton_thanh_pham,
                so_luong_can_san_xuat=result.so_luong_can_san_xuat,
                du_dieu_kien_gui=not result.thieu_bom and valid_assignee,
                thieu_vat_tu=result.thieu_vat_tu,
                lenh_du_kien=result.lenh_du_kien,
                vat_tu=result.vat_tu,
            ),
            meta=ResponseMeta(request_id=request_id),
        )

    async def gui(
        self, resource_id: int, token: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[GuiYeuCauResponse, str]:
        _require_manager(actor)
        async with self.transaction:
            before = await self._require_request(resource_id, actor, lock=True)
            _verify_if_match(if_match, before)
            _require_draft(before)
            if not await self._assignee_valid(before, lock=True):
                raise InvalidAssignee()
            result = await self._calculate(before, lock=True)
            verify_plan_token(token, before, result, settings.secret_key, settings.algorithm)
            if result.thieu_bom:
                raise MissingBomException(message="Thiếu BOM hiện hành cho kế hoạch")
            orders = await self.repository.add_lenh_tree(resource_id, result.lenh_du_kien)
            after = (
                await self._with_progress(
                    [
                        await self.repository.update(
                            resource_id,
                            {
                                "trang_thai": "cho_bo_sung_vat_tu"
                                if result.thieu_vat_tu
                                else "da_gui",
                            },
                        )
                    ]
                )
            )[0]
            await self._audit("yeu_cau_san_xuat", "gui", actor, before, after)
            for order in orders:
                await self._audit("lenh_san_xuat", "tao", actor, None, order)
            response = GuiYeuCauResponse(
                data=GuiYeuCauRead(
                    yeu_cau=after,
                    ke_hoach=KeHoachRead(yeu_cau_san_xuat_id=resource_id, lenh=orders),
                ),
                meta=ResponseMeta(request_id=request_id),
            )
        return response, generate_yeu_cau_etag(after)

    async def ke_hoach(self, resource_id: int, actor: dict, request_id: str) -> KeHoachResponse:
        record = await self._require_request(resource_id, actor)
        if record.trang_thai == "nhap":
            raise InvalidWorkflowState()
        return KeHoachResponse(
            data=KeHoachRead(
                yeu_cau_san_xuat_id=resource_id,
                lenh=await self.repository.lenh_cua_yeu_cau(resource_id, lock=False),
            ),
            meta=ResponseMeta(request_id=request_id),
        )

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


def generate_hoan_thanh_etag(record: HoanThanhRead) -> str:
    return f'"{_canonical_hash(record.model_dump(mode="json"))}"'


def verify_hoan_thanh_if_match(if_match: str | None, record: HoanThanhRead) -> None:
    if not if_match or not if_match.strip():
        raise PreconditionRequiredException()
    if if_match.strip() != generate_hoan_thanh_etag(record):
        raise PreconditionFailedException()


def check_hoan_thanh_time(
    finish_time: datetime | None, started_at: datetime | None, *, submitting: bool
) -> None:
    if finish_time is None or started_at is None:
        raise InvalidWorkflowState(message="Thiếu thời gian hoàn thành hoặc bắt đầu lệnh")
    if finish_time < started_at:
        raise InvalidInputException(message="finish_time không được trước started_at")
    if submitting and finish_time > datetime.now(timezone.utc):
        raise InvalidInputException(message="finish_time không được ở tương lai khi gửi/duyệt")


class HoanThanhExceeded(ConflictException):
    code = "vuot_so_luong_hoan_thanh"
    default_message = "Tổng lượng hoàn thành vượt số lượng lệnh"


class HoanThanhMissingMaterials(ConflictException):
    code = "chua_du_vat_tu_da_cap"
    default_message = "Lệnh chưa được cấp đủ vật tư"


def check_hoan_thanh_quantities(
    order_quantity: int,
    approved: int,
    submitted: int,
    demand: dict[int, int],
    supplied: dict[int, int],
) -> int:
    total = approved + submitted
    if total > order_quantity:
        raise HoanThanhExceeded()
    if not demand or any(supplied.get(item_id, 0) < need for item_id, need in demand.items()):
        raise HoanThanhMissingMaterials()
    return total


class ChungTuHoanThanhService:
    def __init__(
        self, repository: HoanThanhRepository, audit: AuditWriter, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    @staticmethod
    def _role(actor: dict, allowed: set[str]) -> None:
        if not allowed.intersection(actor.get("roles", [])):
            raise ForbiddenException()

    @staticmethod
    def _scope(context: HoanThanhContext, actor: dict) -> None:
        if "quan_ly" in actor.get("roles", []):
            return
        actor_id = int(actor["sub"])
        if context.document.nhan_vien_id != actor_id or context.order.assignee_id != actor_id:
            raise ForbiddenException()

    async def _locked(self, document_id: int, actor: dict) -> HoanThanhContext:
        if not 0 < document_id <= 2**31 - 1:
            raise NotFoundException()
        context = await self.repository.lock_context(document_id)
        if context is None:
            raise NotFoundException()
        self._scope(context, actor)
        return context

    async def _unposted(self, record: HoanThanhRead, state: str) -> None:
        if record.trang_thai != state:
            raise InvalidWorkflowState()
        if await self.repository.postings(record.id):
            raise ConflictException(message="Chứng từ đã có giao dịch kho")

    @staticmethod
    def _running(order: HoanThanhOrder) -> None:
        if order.state != "dang_thuc_hien":
            raise InvalidWorkflowState(message="Lệnh phải đang thực hiện")

    @staticmethod
    def _output(item: HoanThanhOutput | None) -> HoanThanhOutput:
        if item is None:
            raise NotFoundException(message="Mặt hàng đầu ra không tồn tại")
        if not item.is_active:
            raise InactiveMatHang()
        if item.type not in {"ban_thanh_pham", "thanh_pham"}:
            raise ConflictException(message="Đầu ra phải là bán thành phẩm hoặc thành phẩm")
        return item

    @staticmethod
    def _quantity(record_quantity: int, order: HoanThanhOrder) -> None:
        if record_quantity > order.quantity:
            raise HoanThanhExceeded()

    @staticmethod
    def _detail(record: HoanThanhRead, request_id: str) -> tuple[HoanThanhResponse, str]:
        return (
            HoanThanhResponse(data=record, meta=ResponseMeta(request_id=request_id)),
            generate_hoan_thanh_etag(record),
        )

    @staticmethod
    def _action(
        record: HoanThanhRead, ids: list[int], replay: bool, request_id: str
    ) -> tuple[HoanThanhActionResponse, str]:
        action = HoanThanhActionRead(
            **record.model_dump(), giao_dich_kho_ids=ids, da_ghi_so_truoc_do=replay
        )
        return (
            HoanThanhActionResponse(data=action, meta=ResponseMeta(request_id=request_id)),
            generate_hoan_thanh_etag(record),
        )

    async def _audit(
        self,
        operation: str,
        actor: dict,
        before: HoanThanhRead | None,
        after: HoanThanhRead | None,
        *,
        reason: str | None = None,
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="chung_tu_hoan_thanh_san_xuat",
                doi_tuong_id=(after or before).id,
                thao_tac=operation,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else None,
                ly_do=reason,
            )
        )

    async def list_entries(
        self, params: HoanThanhQuery, actor: dict, request_id: str
    ) -> HoanThanhListResponse:
        self._role(actor, {"quan_ly", "nhan_vien"})
        actor_id = None if "quan_ly" in actor["roles"] else int(actor["sub"])
        page = await self.repository.list_entries(params, actor_id)
        return HoanThanhListResponse(
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
        self, document_id: int, actor: dict, request_id: str
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"quan_ly", "nhan_vien"})
        if not 0 < document_id <= 2**31 - 1:
            raise NotFoundException()
        context = await self.repository.get_by_id(document_id)
        if context is None:
            raise NotFoundException()
        self._scope(context, actor)
        return self._detail(context.document, request_id)

    async def create_entry(
        self, payload: HoanThanhCreate, actor: dict, request_id: str
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"nhan_vien"})
        async with self.transaction:
            order = await self.repository.lock_for_create(payload.lenh_san_xuat_id)
            if order is None:
                raise NotFoundException()
            if order.assignee_id != int(actor["sub"]):
                raise ForbiddenException()
            self._running(order)
            self._output(await self.repository.read_output(order.mat_hang_id))
            check_hoan_thanh_time(payload.finish_time, order.started_at, submitting=False)
            self._quantity(payload.so_luong_hoan_thanh, order)
            after = await self.repository.add(payload, int(actor["sub"]))
            await self._audit("tao", actor, None, after)
        return self._detail(after, request_id)

    async def patch_entry(
        self,
        document_id: int,
        payload: HoanThanhPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"nhan_vien"})
        async with self.transaction:
            context = await self._locked(document_id, actor)
            before = context.document
            verify_hoan_thanh_if_match(if_match, before)
            await self._unposted(before, "nhap")
            changes = {
                name: value
                for name, value in payload.model_dump(exclude_unset=True).items()
                if getattr(before, name) != value
            }
            if not changes:
                return self._detail(before, request_id)
            after = before.model_copy(update=changes)
            self._quantity(after.so_luong_hoan_thanh, context.order)
            check_hoan_thanh_time(after.finish_time, context.order.started_at, submitting=False)
            self._output(await self.repository.read_output(after.mat_hang_id))
            after = await self.repository.update(document_id, changes)
            await self._audit("sua", actor, before, after)
        return self._detail(after, request_id)

    async def delete_entry(self, document_id: int, actor: dict, if_match: str | None) -> None:
        self._role(actor, {"nhan_vien"})
        async with self.transaction:
            context = await self._locked(document_id, actor)
            before = context.document
            verify_hoan_thanh_if_match(if_match, before)
            await self._unposted(before, "nhap")
            await self.repository.delete(document_id)
            await self._audit("xoa_nhap", actor, before, None)

    async def gui(
        self, document_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"nhan_vien"})
        async with self.transaction:
            context = await self._locked(document_id, actor)
            before = context.document
            verify_hoan_thanh_if_match(if_match, before)
            await self._unposted(before, "nhap")
            self._running(context.order)
            self._output(await self.repository.read_output(before.mat_hang_id))
            check_hoan_thanh_time(before.finish_time, context.order.started_at, submitting=True)
            self._quantity(before.so_luong_hoan_thanh, context.order)
            after = await self.repository.update(document_id, {"trang_thai": "cho_duyet"})
            await self._audit("gui", actor, before, after)
        return self._detail(after, request_id)

    async def tu_choi(
        self, document_id: int, reason: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"quan_ly"})
        return await self._change_state(
            document_id,
            reason,
            actor,
            if_match,
            request_id,
            operation="tu_choi",
            source="cho_duyet",
            target="tu_choi",
        )

    async def ve_nhap(
        self, document_id: int, reason: str, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[HoanThanhResponse, str]:
        self._role(actor, {"nhan_vien"})
        return await self._change_state(
            document_id,
            reason,
            actor,
            if_match,
            request_id,
            operation="ve_nhap",
            source="tu_choi",
            target="nhap",
        )

    async def _change_state(
        self,
        document_id: int,
        reason: str,
        actor: dict,
        if_match: str | None,
        request_id: str,
        *,
        operation: str,
        source: str,
        target: str,
    ) -> tuple[HoanThanhResponse, str]:
        if not reason or not reason.strip():
            raise InvalidInputException(message="Lý do là bắt buộc")
        async with self.transaction:
            context = await self._locked(document_id, actor)
            before = context.document
            verify_hoan_thanh_if_match(if_match, before)
            await self._unposted(before, source)
            after = await self.repository.update(document_id, {"trang_thai": target})
            await self._audit(operation, actor, before, after, reason=reason.strip())
        return self._detail(after, request_id)

    @staticmethod
    def _replay(record: HoanThanhRead, postings: list[HoanThanhPosting]) -> list[int]:
        if len(postings) != 1:
            raise ConflictException(message="Chứng từ đã duyệt thiếu hoặc sai giao dịch kho")
        posting = postings[0]
        if (
            posting.source_id != record.id
            or posting.mat_hang_id != record.mat_hang_id
            or posting.quantity != record.so_luong_hoan_thanh
            or posting.quantity <= 0
            or posting.type != "nhap_san_pham_san_xuat"
        ):
            raise ConflictException(message="Giao dịch kho không khớp chứng từ đã duyệt")
        return [posting.id]

    async def duyet(
        self, document_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[HoanThanhActionResponse, str]:
        self._role(actor, {"quan_ly"})
        async with self.transaction:
            context = await self._locked(document_id, actor)
            before, order = context.document, context.order
            if not if_match or not if_match.strip():
                raise PreconditionRequiredException()
            postings = await self.repository.postings(document_id)
            if before.trang_thai == "da_duyet":
                return self._action(before, self._replay(before, postings), True, request_id)
            verify_hoan_thanh_if_match(if_match, before)
            if before.trang_thai != "cho_duyet":
                raise InvalidWorkflowState()
            if postings:
                raise ConflictException(message="Chứng từ chưa duyệt đã có giao dịch kho")
            self._running(order)
            check_hoan_thanh_time(before.finish_time, order.started_at, submitting=True)
            output = self._output(await self.repository.lock_output(before.mat_hang_id))
            if output.balance != output.ledger_total:
                raise ConflictException(message="Số dư tồn không khớp sổ kho")
            if output.balance + before.so_luong_hoan_thanh > 2**31 - 1:
                raise ConflictException(message="Số dư tồn vượt giới hạn INT32")
            approved = await self.repository.approved_quantity(order.id)
            demand, supplied = await self.repository.material_quantities(order.id)
            total = check_hoan_thanh_quantities(
                order.quantity, approved, before.so_luong_hoan_thanh, demand, supplied
            )
            posted_at = datetime.now(timezone.utc)
            after = await self.repository.update(document_id, {"trang_thai": "da_duyet"})
            movement_id = await self.repository.post_output(after, int(actor["sub"]), posted_at)
            if total == order.quantity:
                old_order, new_order = await self.repository.complete_order(order.id, posted_at)
                await self.audit.append(
                    CreationAudit(
                        nhan_vien_id=int(actor["sub"]),
                        loai_doi_tuong="lenh_san_xuat",
                        doi_tuong_id=order.id,
                        thao_tac="hoan_tat",
                        du_lieu_truoc=old_order.model_dump(mode="json"),
                        du_lieu_sau=new_order.model_dump(mode="json"),
                    )
                )
            await self._audit("duyet", actor, before, after)
        return self._action(after, [movement_id], False, request_id)
