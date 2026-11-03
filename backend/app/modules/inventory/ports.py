"""Inventory query and receipt posting contracts."""

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
    async def receive_receipt(
        self, lines: list[StockReceiptLine], actor_id: int, posted_at: datetime
    ) -> list[int]: ...
