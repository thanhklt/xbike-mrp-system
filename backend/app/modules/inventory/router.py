from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.security import require_roles
from app.modules.inventory.schemas import StockLevelResponse, StockMovementCreate, StockMovementResponse
from app.shared.enums import StockMovementType
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/inventory", tags=["Inventory & Warehouse"])

SAMPLE_STOCK: List[StockLevelResponse] = [
    StockLevelResponse(
        id=1,
        part_id=2,
        part_number="XB-SUB-WHEEL-F",
        part_name="Front Wheel Assembly 700c",
        warehouse_code="WH-MAIN",
        bin_location="B-04-12",
        quantity_on_hand=45.0,
        quantity_allocated=10.0,
        quantity_reserved=5.0,
        quantity_available=30.0,
        updated_at=datetime.now(timezone.utc),
    ),
    StockLevelResponse(
        id=2,
        part_id=3,
        part_number="XB-RAW-RIM-700C",
        part_name="Double-wall Alloy Rim 700c",
        warehouse_code="WH-MAIN",
        bin_location="A-01-05",
        quantity_on_hand=120.0,
        quantity_allocated=40.0,
        quantity_reserved=0.0,
        quantity_available=80.0,
        updated_at=datetime.now(timezone.utc),
    ),
    StockLevelResponse(
        id=3,
        part_id=4,
        part_number="XB-RAW-CHN-11S",
        part_name="11-Speed Bicycle Chain",
        warehouse_code="WH-MAIN",
        bin_location="C-02-18",
        quantity_on_hand=88.0,
        quantity_allocated=15.0,
        quantity_reserved=0.0,
        quantity_available=73.0,
        updated_at=datetime.now(timezone.utc),
    ),
]

SAMPLE_MOVEMENTS: List[StockMovementResponse] = [
    StockMovementResponse(
        id=1,
        part_id=3,
        part_number="XB-RAW-RIM-700C",
        movement_type=StockMovementType.RECEIPT,
        quantity=50.0,
        reference_order_number="PO-2026-004",
        notes="Received from Apex Alloy supplier",
        created_at=datetime.now(timezone.utc),
    )
]


@router.get("/stock", response_model=PaginatedResponse[StockLevelResponse])
async def list_stock_levels(params: PageParams = Depends(get_pagination_params)):
    """List current inventory stock levels across all warehouse bins."""
    return create_paginated_response(
        items=SAMPLE_STOCK,
        total_items=len(SAMPLE_STOCK),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/movements", response_model=PaginatedResponse[StockMovementResponse])
async def list_movements(params: PageParams = Depends(get_pagination_params)):
    """Audit ledger of all stock ins and outs."""
    return create_paginated_response(
        items=SAMPLE_MOVEMENTS,
        total_items=len(SAMPLE_MOVEMENTS),
        page=params.page,
        page_size=params.page_size,
    )


@router.post("/movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED)
async def record_movement(payload: StockMovementCreate, _=Depends(require_roles(["ADMIN", "WAREHOUSE"]))):
    """Post an inventory adjustment, receipt or scrap transaction."""
    new_movement = StockMovementResponse(
        id=len(SAMPLE_MOVEMENTS) + 1,
        part_id=payload.part_id,
        part_number=f"PART-{payload.part_id}",
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reference_order_number=payload.reference_order_number,
        notes=payload.notes,
        created_at=datetime.now(timezone.utc),
    )
    SAMPLE_MOVEMENTS.append(new_movement)
    return new_movement
