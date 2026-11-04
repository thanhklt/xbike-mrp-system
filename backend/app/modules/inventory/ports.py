"""Inventory queries, receipt posting and warehouse adjustment contracts."""

from datetime import datetime
from typing import NamedTuple, Protocol

from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class InventoryRepository(Protocol):
    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]: ...

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]: ...


class StockReceiptLine(NamedTuple):
    chi_tiet_phieu_nhap_id: int
    mat_hang_id: int
    so_luong: int


class InventoryWriter(Protocol):
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


class InventoryIssueWriter(Protocol):
    async def issue_stock(
        self, lines: list[StockIssueLine], kind: str, actor_id: int, posted_at: datetime
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
