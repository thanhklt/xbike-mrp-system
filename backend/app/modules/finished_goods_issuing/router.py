from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.finished_goods_issuing.schemas import (
    DispatchItemResponse,
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/finished-goods-issuing", tags=["Finished Goods Dispatch"])

SAMPLE_DISPATCHES: List[FinishedGoodsDispatchResponse] = [
    FinishedGoodsDispatchResponse(
        id=1,
        dispatch_number="DSP-2026-0005",
        destination_dealer="EuroBike Hub Berlin",
        carrier_tracking_number="DHL-EX-992819",
        status="DISPATCHED",
        dispatched_by_user_id=1,
        notes="Container #4 - Final QA checked",
        created_at=datetime.now(timezone.utc),
        dispatched_at=datetime.now(timezone.utc),
        items=[
            DispatchItemResponse(
                id=1,
                product_part_id=1,
                product_part_number="XB-BIKE-URBAN-01",
                product_name="xBike Urban Commuter E-Bike",
                quantity_dispatched=10.0,
                serial_numbers="XB26-00101 thru XB26-00110",
            )
        ],
    )
]


@router.get("", response_model=PaginatedResponse[FinishedGoodsDispatchResponse])
async def list_dispatches(params: PageParams = Depends(get_pagination_params)):
    """List outgoing finished goods dispatches."""
    return create_paginated_response(
        items=SAMPLE_DISPATCHES,
        total_items=len(SAMPLE_DISPATCHES),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{dispatch_id}", response_model=FinishedGoodsDispatchResponse)
async def get_dispatch(dispatch_id: int):
    """Retrieve details of a single dispatch order."""
    for d in SAMPLE_DISPATCHES:
        if d.id == dispatch_id:
            return d
    raise NotFoundException(message=f"Dispatch {dispatch_id} not found")


@router.post("", response_model=FinishedGoodsDispatchResponse, status_code=status.HTTP_201_CREATED)
async def create_dispatch(
    payload: FinishedGoodsDispatchCreate,
    _=Depends(require_roles(["ADMIN", "WAREHOUSE"])),
):
    """Register finished bicycle dispatch to dealership or logistics center."""
    for d in SAMPLE_DISPATCHES:
        if d.dispatch_number == payload.dispatch_number:
            raise ConflictException(message=f"Dispatch number {payload.dispatch_number} already exists")

    items_res = [
        DispatchItemResponse(
            id=len(SAMPLE_DISPATCHES) * 10 + i,
            product_part_id=it.product_part_id,
            product_part_number=f"PROD-{it.product_part_id}",
            product_name="xBike Model",
            quantity_dispatched=it.quantity_dispatched,
            serial_numbers=it.serial_numbers,
        )
        for i, it in enumerate(payload.items)
    ]

    new_dispatch = FinishedGoodsDispatchResponse(
        id=len(SAMPLE_DISPATCHES) + 1,
        dispatch_number=payload.dispatch_number,
        destination_dealer=payload.destination_dealer,
        carrier_tracking_number=payload.carrier_tracking_number,
        status=payload.status,
        dispatched_by_user_id=1,
        notes=payload.notes,
        created_at=datetime.now(timezone.utc),
        items=items_res,
    )
    SAMPLE_DISPATCHES.append(new_dispatch)
    return new_dispatch
