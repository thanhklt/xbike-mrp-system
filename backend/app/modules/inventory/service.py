"""Inventory read use cases and explicit unsupported workflow."""

from hashlib import sha256

from app.core.errors import NotFoundException, WorkflowNotImplemented
from app.modules.inventory.ports import InventoryRepository
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class InventoryService:
    def __init__(self, repository: InventoryRepository):
        self.repository = repository

    async def list_stock(
        self, params: PageParams, mat_hang_id: int | None = None
    ) -> PaginatedResponse[StockLevelResponse]:
        result = await self.repository.list_stock(params, mat_hang_id)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_stock_by_mat_hang(self, mat_hang_id: int) -> tuple[StockLevelResponse, str]:
        record = await self.repository.get_stock_by_mat_hang(mat_hang_id)
        if record is None:
            raise NotFoundException(message=f"ton_kho for mat_hang {mat_hang_id} not found")
        etag = f'"{sha256(record.model_dump_json().encode("utf-8")).hexdigest()}"'
        return record, etag

    async def list_movements(
        self,
        params: PageParams,
        mat_hang_id: int | None = None,
        loai_giao_dich: str | None = None,
    ) -> PaginatedResponse[StockMovementResponse]:
        result = await self.repository.list_movements(params, mat_hang_id, loai_giao_dich)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)

    async def get_movement_by_id(self, movement_id: int) -> tuple[StockMovementResponse, str]:
        record = await self.repository.get_movement_by_id(movement_id)
        if record is None:
            raise NotFoundException(message=f"giao_dich_kho {movement_id} not found")
        etag = f'"{sha256(record.model_dump_json().encode("utf-8")).hexdigest()}"'
        return record, etag

    async def record_movement(self) -> None:
        raise WorkflowNotImplemented()
