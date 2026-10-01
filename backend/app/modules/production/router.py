from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.production.schemas import WorkOrderCreate, WorkOrderResponse, WorkOrderUpdateStatus
from app.shared.enums import WorkOrderStatus
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/production", tags=["Production & Work Orders"])

SAMPLE_WORK_ORDERS: List[WorkOrderResponse] = [
    WorkOrderResponse(
        id=1,
        work_order_number="WO-2026-0012",
        product_part_id=1,
        product_part_number="XB-BIKE-URBAN-01",
        product_name="xBike Urban Commuter E-Bike",
        bom_id=1,
        quantity_planned=25.0,
        quantity_completed=10.0,
        quantity_scrapped=0.0,
        status=WorkOrderStatus.IN_PROGRESS,
        scheduled_start=datetime.now(timezone.utc),
        scheduled_finish=datetime.now(timezone.utc),
        notes="Line A Assembly - Batch 1 for Spring Release",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
]


@router.get("/work-orders", response_model=PaginatedResponse[WorkOrderResponse])
async def list_work_orders(params: PageParams = Depends(get_pagination_params)):
    """List production work orders with progress status."""
    return create_paginated_response(
        items=SAMPLE_WORK_ORDERS,
        total_items=len(SAMPLE_WORK_ORDERS),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/work-orders/{wo_id}", response_model=WorkOrderResponse)
async def get_work_order(wo_id: int):
    """Retrieve single work order details."""
    for wo in SAMPLE_WORK_ORDERS:
        if wo.id == wo_id:
            return wo
    raise NotFoundException(message=f"Work Order {wo_id} not found")


@router.post("/work-orders", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate,
    _=Depends(require_roles(["ADMIN", "MANAGER", "PRODUCTION"])),
):
    """Create a new manufacturing work order."""
    for wo in SAMPLE_WORK_ORDERS:
        if wo.work_order_number == payload.work_order_number:
            raise ConflictException(message=f"Work Order {payload.work_order_number} already exists")

    new_wo = WorkOrderResponse(
        id=len(SAMPLE_WORK_ORDERS) + 1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    SAMPLE_WORK_ORDERS.append(new_wo)
    return new_wo


@router.patch("/work-orders/{wo_id}/status", response_model=WorkOrderResponse)
async def update_work_order_status(
    wo_id: int,
    payload: WorkOrderUpdateStatus,
    _=Depends(require_roles(["ADMIN", "PRODUCTION"])),
):
    """Update work order progress or mark completed."""
    for wo in SAMPLE_WORK_ORDERS:
        if wo.id == wo_id:
            wo.status = payload.status
            if payload.quantity_completed is not None:
                wo.quantity_completed = payload.quantity_completed
            if payload.quantity_scrapped is not None:
                wo.quantity_scrapped = payload.quantity_scrapped
            wo.updated_at = datetime.now(timezone.utc)
            return wo
    raise NotFoundException(message=f"Work Order {wo_id} not found")
