"""State transitions, assignment guards, and atomic audit for orders."""

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    NotFoundException,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.lenh_san_xuat.ports import LenhSanXuatRepository
from app.modules.lenh_san_xuat.schemas import (
    DetailResponse,
    LenhListQuery,
    LenhListResponse,
    LenhRead,
    ListMeta,
    ResponseMeta,
    VatTuLenhRead,
)


class LenhSanXuatService:
    def __init__(
        self, repository: LenhSanXuatRepository, audit: AuditWriter, transaction: Transaction
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def list_orders(self, query: LenhListQuery, request_id: str) -> LenhListResponse:
        page = await self.repository.list_orders(query)
        return LenhListResponse(
            data=page.items,
            meta=ListMeta(
                request_id=request_id,
                page=query.page,
                page_size=query.page_size,
                total=page.total,
                total_pages=(page.total + query.page_size - 1) // query.page_size,
            ),
        )

    async def _require_order(self, order_id: int) -> LenhRead:
        order = await self.repository.get_order(order_id) if order_id <= 2147483647 else None
        if order is None:
            raise NotFoundException(message="Lệnh sản xuất không tồn tại")
        return order

    async def get_order(self, order_id: int, request_id: str) -> DetailResponse[LenhRead]:
        return DetailResponse(
            data=await self._require_order(order_id), meta=ResponseMeta(request_id=request_id)
        )

    async def get_materials(self, order_id: int, request_id: str) -> DetailResponse[VatTuLenhRead]:
        order = await self._require_order(order_id)
        return DetailResponse(
            data=await self.repository.materials(order), meta=ResponseMeta(request_id=request_id)
        )

    async def _lock(self, order_id: int) -> LenhRead:
        order = await self.repository.lock_order(order_id) if order_id <= 2147483647 else None
        if order is None:
            raise NotFoundException(message="Lệnh sản xuất không tồn tại")
        return order

    async def _employee(self, employee_id: int | None) -> None:
        if employee_id is None or not await self.repository.employee_active(employee_id):
            raise InvalidInputException(message="Người thực hiện phải tồn tại và đang hoạt động")

    async def _finish(
        self, before: LenhRead, actor: dict, action: str, reason: str | None = None
    ) -> LenhRead:
        after = await self._require_order(before.id)
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="lenh_san_xuat",
                doi_tuong_id=before.id,
                thao_tac=action,
                du_lieu_truoc=before.model_dump(mode="json"),
                du_lieu_sau=after.model_dump(mode="json"),
                ly_do=reason,
            )
        )
        return after

    async def assign(
        self, order_id: int, employee_id: int, actor: dict, request_id: str
    ) -> DetailResponse[LenhRead]:
        async with self.transaction:
            order = await self._lock(order_id)
            if order.trang_thai != "nhap":
                raise ConflictException(message="Chỉ được phân công khi lệnh ở trạng thái nhap")
            await self._employee(employee_id)
            await self.repository.assign(order_id, employee_id)
            after = await self._finish(order, actor, "sua")
        return DetailResponse(data=after, meta=ResponseMeta(request_id=request_id))

    async def send(self, order_id: int, actor: dict, request_id: str) -> DetailResponse[LenhRead]:
        async with self.transaction:
            await self.repository.lock_bom_graph()
            order = await self._lock(order_id)
            if order.trang_thai != "nhap":
                raise ConflictException(message="Chỉ được gửi lệnh nhap")
            await self._employee(order.nhan_vien_id)
            if not await self.repository.request_active(order.yeu_cau_san_xuat_id):
                raise ConflictException(message="Yêu cầu sản xuất không còn hoạt động")
            if not await self.repository.formula_matches(order):
                raise ConflictException(message="BOM hoặc nhu cầu trực tiếp không khớp kế hoạch")
            await self.repository.transition(order_id, "da_gui")
            after = await self._finish(order, actor, "gui")
        return DetailResponse(data=after, meta=ResponseMeta(request_id=request_id))

    async def start(self, order_id: int, actor: dict, request_id: str) -> DetailResponse[LenhRead]:
        async with self.transaction:
            order = await self._lock(order_id)
            if "nhan_vien" not in actor.get("roles", []) or int(actor["sub"]) != order.nhan_vien_id:
                raise ForbiddenException(message="Chỉ nhân viên được giao được bắt đầu lệnh")
            if order.trang_thai != "da_gui":
                raise ConflictException(message="Chỉ được bắt đầu lệnh da_gui")
            if not (await self.repository.materials(order)).du_dieu_kien_bat_dau:
                raise ConflictException(message="Chưa cấp đủ vật tư")
            await self.repository.transition(order_id, "dang_thuc_hien")
            after = await self._finish(order, actor, "bat_dau")
        return DetailResponse(data=after, meta=ResponseMeta(request_id=request_id))

    async def cancel(
        self, order_id: int, reason: str, actor: dict, request_id: str
    ) -> DetailResponse[LenhRead]:
        async with self.transaction:
            order = await self._lock(order_id)
            if order.trang_thai in {"hoan_thanh", "da_huy"}:
                raise ConflictException(message="Lệnh đã kết thúc")
            if await self.repository.has_postings(order_id):
                raise ConflictException(message="Lệnh đã có chứng từ ghi sổ")
            if await self.repository.has_active_children(order_id):
                raise ConflictException(message="Phải hủy lệnh con đang hoạt động trước")
            await self.repository.transition(order_id, "da_huy")
            after = await self._finish(order, actor, "huy", reason)
        return DetailResponse(data=after, meta=ResponseMeta(request_id=request_id))
