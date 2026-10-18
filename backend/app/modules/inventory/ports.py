"""Read-only inventory persistence contract."""

from typing import Protocol

from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class InventoryRepository(Protocol):
    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]: ...

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]: ...
