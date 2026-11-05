"""Application-owned contracts; adapters return detached document snapshots."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.modules.bom.ports import ActiveBom
from app.modules.san_xuat.schemas import (
    ChungTuRead,
    HoanThanhCreate,
    HoanThanhQuery,
    HoanThanhRead,
    LenhDuKien,
    LenhQuery,
    LenhRead,
    VatTuLenhLine,
    YeuCauCreate,
    YeuCauListQuery,
    YeuCauRead,
)
from app.shared.records import RecordPage


class PlanningBomReader(Protocol):
    async def lock_graph(self) -> None: ...
    async def active_graph(self) -> dict[int, ActiveBom]: ...


class AssigneeReader(Protocol):
    async def kiem_tra_nguoi_duoc_giao(self, employee_id: int, *, lock: bool) -> None: ...


class ProductionIssues(Protocol):
    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]: ...
    async def co_phieu_da_ghi_so(self, yeu_cau_id: int, lenh_ids: list[int]) -> bool: ...
    async def huy_phieu_chua_ghi_so(
        self, yeu_cau_id: int, lenh_ids: list[int], ly_do: str, actor_id: int
    ) -> None: ...


class YeuCauSanXuatRepository(Protocol):
    async def list_entries(
        self, params: YeuCauListQuery, actor_id: int | None
    ) -> RecordPage[YeuCauRead]: ...
    async def get_by_id(self, request_id: int) -> YeuCauRead | None: ...
    async def get_for_update(self, request_id: int) -> YeuCauRead | None: ...
    async def add(self, payload: YeuCauCreate, actor_id: int) -> YeuCauRead: ...
    async def update(self, request_id: int, changes: dict[str, object]) -> YeuCauRead: ...
    async def delete(self, request_id: int) -> None: ...
    async def has_dependencies(self, request_id: int) -> bool: ...
    async def add_lenh_tree(self, request_id: int, planned: list[LenhDuKien]) -> list[LenhRead]: ...
    async def lenh_cua_yeu_cau(self, request_id: int, *, lock: bool) -> list[LenhRead]: ...
    async def chung_tu_hoan_thanh_cua_lenh(
        self, lenh_ids: list[int], *, lock: bool
    ) -> list[ChungTuRead]: ...
    async def xoa_chung_tu_nhap(self, document_id: int) -> None: ...
    async def tu_choi_chung_tu(self, document_id: int) -> ChungTuRead: ...
    async def huy_lenh(self, lenh_id: int) -> None: ...


@dataclass(frozen=True)
class HoanThanhOrder:
    id: int
    request_id: int
    mat_hang_id: int
    quantity: int
    state: str
    assignee_id: int | None
    started_at: datetime | None


@dataclass(frozen=True)
class HoanThanhContext:
    document: HoanThanhRead
    order: HoanThanhOrder


@dataclass(frozen=True)
class HoanThanhPosting:
    id: int
    mat_hang_id: int
    quantity: int
    type: str
    source_id: int


@dataclass(frozen=True)
class HoanThanhOutput:
    id: int
    is_active: bool
    type: str
    balance: int
    ledger_total: int


class HoanThanhRepository(Protocol):
    async def list_entries(
        self, params: HoanThanhQuery, actor_id: int | None
    ) -> RecordPage[HoanThanhRead]: ...
    async def get_by_id(self, document_id: int) -> HoanThanhContext | None: ...
    async def lock_for_create(self, order_id: int) -> HoanThanhOrder | None: ...
    async def lock_context(self, document_id: int) -> HoanThanhContext | None: ...
    async def add(self, payload: HoanThanhCreate, actor_id: int) -> HoanThanhRead: ...
    async def update(self, document_id: int, changes: dict[str, object]) -> HoanThanhRead: ...
    async def delete(self, document_id: int) -> None: ...
    async def postings(self, document_id: int) -> list[HoanThanhPosting]: ...
    async def approved_quantity(self, order_id: int) -> int: ...
    async def material_quantities(self, order_id: int) -> tuple[dict[int, int], dict[int, int]]: ...
    async def read_output(self, item_id: int) -> HoanThanhOutput | None: ...
    async def lock_output(self, item_id: int) -> HoanThanhOutput | None: ...
    async def post_output(
        self, document: HoanThanhRead, actor_id: int, posted_at: datetime
    ) -> int: ...
    async def complete_order(
        self, order_id: int, completed_at: datetime
    ) -> tuple[LenhRead, LenhRead]: ...


@dataclass(frozen=True)
class LenhContext:
    document: LenhRead
    request_state: str
    materials: list[VatTuLenhLine]


class LenhSanXuatRepository(Protocol):
    async def list_orders(
        self, params: LenhQuery, employee_id: int | None
    ) -> RecordPage[LenhRead]: ...
    async def get_context(self, order_id: int, *, lock: bool) -> LenhContext | None: ...
    async def update_order(self, order_id: int, changes: dict[str, object]) -> None: ...
    async def start_request(self, request_id: int) -> tuple[YeuCauRead, YeuCauRead] | None: ...
    async def has_posted_dependency(self, order_id: int) -> bool: ...
    async def has_active_children(self, order_id: int) -> bool: ...
