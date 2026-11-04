"""Application-owned order persistence and employee-validation contracts."""

from dataclasses import dataclass
from typing import Protocol

from app.modules.lenh_san_xuat.schemas import LenhQuery, LenhRead, VatTuLenhLine
from app.modules.san_xuat.schemas import YeuCauRead
from app.shared.records import RecordPage


@dataclass(frozen=True)
class LenhContext:
    document: LenhRead
    request_state: str
    materials: list[VatTuLenhLine]


class AssigneeReader(Protocol):
    async def kiem_tra_nguoi_duoc_giao(self, employee_id: int, *, lock: bool) -> None: ...


class LenhSanXuatRepository(Protocol):
    async def list_orders(
        self, params: LenhQuery, employee_id: int | None
    ) -> RecordPage[LenhRead]: ...
    async def get_context(self, order_id: int, *, lock: bool) -> LenhContext | None: ...
    async def update_order(self, order_id: int, changes: dict[str, object]) -> None: ...
    async def start_request(self, request_id: int) -> tuple[YeuCauRead, YeuCauRead] | None: ...
    async def has_posted_dependency(self, order_id: int) -> bool: ...
    async def has_active_children(self, order_id: int) -> bool: ...
