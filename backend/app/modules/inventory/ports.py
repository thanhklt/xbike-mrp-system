"""Inventory queries, receipt posting and warehouse adjustment contracts."""

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Protocol

from app.modules.inventory.schemas import StockLevelResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class InventoryRepository(Protocol):
    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]: ...


class StockReceiptLine(NamedTuple):
    chi_tiet_phieu_nhap_id: int
    mat_hang_id: int
    so_luong: int


class InventoryWriter(Protocol):
    async def lock_receipt_stock(self, item_ids: list[int]) -> list["ReceiptStock"]: ...
    async def lock_balances(self, item_ids: list[int]) -> dict[int, int]: ...

    async def adjust_stock(
        self, lines: list["StockAdjustmentLine"], actor_id: int, posted_at: datetime
    ) -> list[int]: ...

    async def receive_receipt(
        self, lines: list[StockReceiptLine], actor_id: int, posted_at: datetime
    ) -> list[int]: ...


class StockIssueLine(NamedTuple):
    chi_tiet_phieu_xuat_id: int
    mat_hang_id: int
    so_luong: int


@dataclass(frozen=True)
class ReceiptStock:
    id: int
    loai_mat_hang: str
    is_active: bool
    so_luong_ton: int
    so_luong_dang_giu: int
    ledger_balance: int


@dataclass(frozen=True)
class IssueReservation:
    id: int
    request_id: int
    item_id: int
    kind: str
    quantity: int
    completion_id: int | None


@dataclass(frozen=True)
class IssueStockContext:
    item_id: int
    kind: str
    price: int
    stock: int
    held: int
    ledger_balance: int
    reservations: tuple[IssueReservation, ...]


class InventoryIssueWriter(Protocol):
    async def lock_issue_stock(
        self, request_id: int, item_ids: list[int]
    ) -> list[IssueStockContext]: ...

    async def issue_stock(
        self,
        lines: list[StockIssueLine],
        kind: str,
        actor_id: int,
        posted_at: datetime,
        *,
        issue_id: int,
        reservations: list[IssueReservation],
    ) -> list[int]: ...


class StockAdjustmentLine(NamedTuple):
    chi_tiet_phieu_dieu_chinh_id: int
    mat_hang_id: int
    so_luong_bien_dong: int


class StockShortage(Exception):
    def __init__(self, *, lines: list[dict], balances: dict[int, int]):
        super().__init__("Không đủ tồn để điều chỉnh")
        self.lines = lines
        self.balances = balances


class InventoryProductionWriter(Protocol):
    # UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 5 cộng tồn và ghi sổ (specs/use_cases/production/UC-31.md)
    async def receive_production(
        self, item_id: int, quantity: int, completion_id: int, actor_id: int,
        posted_at: datetime, *, hold: bool,
    ) -> tuple[int, int]: ...
