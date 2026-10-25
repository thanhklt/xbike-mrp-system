"""Read-only inventory persistence contract."""

from typing import Protocol

from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class InventoryRepository(Protocol):
    async def list_stock(
        self, params: PageParams, mat_hang_id: int | None = None
    ) -> RecordPage[StockLevelResponse]: ...

    async def get_stock_by_mat_hang(self, mat_hang_id: int) -> StockLevelResponse | None: ...

    async def list_movements(
        self,
        params: PageParams,
        mat_hang_id: int | None = None,
        loai_giao_dich: str | None = None,
    ) -> RecordPage[StockMovementResponse]: ...

    async def get_movement_by_id(self, movement_id: int) -> StockMovementResponse | None: ...
