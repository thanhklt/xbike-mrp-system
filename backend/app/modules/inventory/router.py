"""Read-only inventory and warehouse ledger endpoints matching contract: /ton_kho and /giao_dich_kho."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.dependencies import (
    get_current_user_payload,
    get_inventory_service,
    get_pagination_params,
)
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.modules.inventory.service import InventoryService
from app.shared.pagination import PageParams, PaginatedResponse

ton_kho_router = APIRouter(
    prefix="/ton_kho", tags=["ton_kho"], dependencies=[Depends(get_current_user_payload)]
)

giao_dich_kho_router = APIRouter(
    prefix="/giao_dich_kho",
    tags=["giao_dich_kho"],
    dependencies=[Depends(get_current_user_payload)],
)


@ton_kho_router.get("", response_model=PaginatedResponse[StockLevelResponse])
async def list_stock(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    mat_hang_id: Annotated[int | None, Query(gt=0, description="Filter by mat_hang_id")] = None,
):
    """API-029: Lấy danh sách tồn kho phân trang, hỗ trợ lọc theo mat_hang_id."""
    return await service.list_stock(params, mat_hang_id)


@ton_kho_router.get(
    "/{mat_hang_id}",
    response_model=StockLevelResponse,
    responses={
        200: {
            "headers": {
                "ETag": {"schema": {"type": "string"}, "description": "Strong resource ETag"}
            }
        }
    },
)
async def get_stock_by_mat_hang(
    mat_hang_id: Annotated[int, Path(gt=0, description="ID mặt hàng")],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    response: Response,
):
    """API-030: Lấy chi tiết tồn kho theo mat_hang_id kèm ETag."""
    record, etag = await service.get_stock_by_mat_hang(mat_hang_id)
    response.headers["ETag"] = etag
    return record


@giao_dich_kho_router.get("", response_model=PaginatedResponse[StockMovementResponse])
async def list_movements(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    mat_hang_id: Annotated[int | None, Query(gt=0, description="Filter by mat_hang_id")] = None,
    loai_giao_dich: Annotated[str | None, Query(description="Filter by loai_giao_dich")] = None,
):
    """API-031: Lấy sổ giao dịch kho phân biệt so_luong_bien_dong và so_luong_hieu_luc."""
    return await service.list_movements(params, mat_hang_id, loai_giao_dich)


@giao_dich_kho_router.get(
    "/{id}",
    response_model=StockMovementResponse,
    responses={
        200: {
            "headers": {
                "ETag": {"schema": {"type": "string"}, "description": "Strong resource ETag"}
            }
        }
    },
)
async def get_movement(
    id: Annotated[int, Path(gt=0, description="ID giao dịch kho")],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    response: Response,
):
    """API-032: Lấy chi tiết giao dịch kho kèm ETag."""
    record, etag = await service.get_movement_by_id(id)
    response.headers["ETag"] = etag
    return record


# Compatibility alias
router = ton_kho_router
