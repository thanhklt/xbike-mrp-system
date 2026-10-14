"""Persisted production endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.production.models import WorkOrder, WorkOrderItem
from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/production", tags=["Production"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, WorkOrder, WorkOrderResponse, params)


@router.get("/work-orders/{wo_id}", response_model=WorkOrderResponse)
async def get_entry(wo_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(db, WorkOrder, wo_id)


@router.post("/work-orders", response_model=WorkOrderResponse, status_code=201)
async def create_entry(
    payload: WorkOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await create_record(
        db, WorkOrder, payload, actor, "lenh_san_xuat", child=(WorkOrderItem, "lenh_san_xuat_id")
    )


@router.patch("/work-orders/{wo_id}/status")
async def update_work_order_status(
    wo_id: int,
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    from app.shared.database_queries import workflow_not_implemented

    workflow_not_implemented()
