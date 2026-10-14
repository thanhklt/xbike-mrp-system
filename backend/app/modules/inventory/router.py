"""Read the persisted database; no in-memory fixtures."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.database_queries import list_records, workflow_not_implemented
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/inventory", tags=["Inventory"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/stock", response_model=PaginatedResponse[StockLevelResponse])
async def list_0(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, StockLevel, StockLevelResponse, params)


@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
async def list_1(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, StockMovement, StockMovementResponse, params)


@router.post("/movements")
async def record_movement(
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    workflow_not_implemented()
