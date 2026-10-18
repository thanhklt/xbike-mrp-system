"""Persisted production endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_pagination_params,
    get_production_service,
    require_roles,
)
from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse
from app.modules.production.service import ProductionService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/production", tags=["Production"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[ProductionService, Depends(get_production_service)],
):
    return await service.list_entries(params)


@router.get("/work-orders/{wo_id}", response_model=WorkOrderResponse)
async def get_entry(
    wo_id: int, service: Annotated[ProductionService, Depends(get_production_service)]
):
    return await service.get_entry(wo_id)


@router.post("/work-orders", response_model=WorkOrderResponse, status_code=201)
async def create_entry(
    payload: WorkOrderCreate,
    service: Annotated[ProductionService, Depends(get_production_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.create_entry(payload, actor)


@router.patch("/work-orders/{wo_id}/status")
async def update_work_order_status(
    wo_id: int,
    service: Annotated[ProductionService, Depends(get_production_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    await service.update_work_order_status(wo_id)
