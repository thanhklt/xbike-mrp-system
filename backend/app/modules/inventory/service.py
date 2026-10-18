"""Inventory read use cases and explicit unsupported workflow."""

from app.core.errors import WorkflowNotImplemented
from app.modules.inventory.ports import InventoryRepository
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class InventoryService:
    def __init__(self, repository: InventoryRepository):
        self.repository = repository

    async def list_stock(self, params: PageParams) -> PaginatedResponse[StockLevelResponse]:
        result = await self.repository.list_stock(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def list_movements(self, params: PageParams) -> PaginatedResponse[StockMovementResponse]:
        result = await self.repository.list_movements(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def record_movement(self) -> None:
        raise WorkflowNotImplemented()
