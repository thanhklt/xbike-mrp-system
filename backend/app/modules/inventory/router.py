"""Read the persisted database; no in-memory fixtures."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_inventory_service,
    get_pagination_params,
    require_roles,
)
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.modules.inventory.service import InventoryService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/inventory", tags=["Inventory"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/stock", response_model=PaginatedResponse[StockLevelResponse])
async def list_0(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
):
    return await service.list_stock(params)


@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
async def list_1(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
):
    return await service.list_movements(params)


@router.post("/movements")
async def record_movement(
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    await service.record_movement()
