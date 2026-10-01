from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.bom.schemas import BOMHeaderCreate, BOMHeaderResponse, BOMItemResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/bom", tags=["Bill of Materials (BOM)"])

SAMPLE_BOMS: List[BOMHeaderResponse] = [
    BOMHeaderResponse(
        id=1,
        product_part_id=1,
        product_name="xBike Urban Commuter E-Bike",
        product_part_number="XB-BIKE-URBAN-01",
        bom_code="BOM-XB-URBAN-01",
        version="1.0",
        description="Standard Bill of Materials for Urban Commuter Model 2026",
        is_active=True,
        items=[
            BOMItemResponse(
                id=101,
                component_part_id=2,
                component_part_number="XB-SUB-WHEEL-F",
                component_name="Front Wheel Assembly 700c",
                unit="SET",
                quantity_required=1.0,
                scrap_factor_percent=0.0,
                notes="Inspect truing before line installation",
            ),
            BOMItemResponse(
                id=102,
                component_part_id=4,
                component_part_number="XB-RAW-CHN-11S",
                component_name="11-Speed Bicycle Chain",
                unit="PCS",
                quantity_required=1.0,
                scrap_factor_percent=2.0,
                notes="Cut to 114 links",
            ),
        ],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
]


@router.get("", response_model=PaginatedResponse[BOMHeaderResponse])
async def list_boms(params: PageParams = Depends(get_pagination_params)):
    """List BOM headers with pagination."""
    return create_paginated_response(
        items=SAMPLE_BOMS,
        total_items=len(SAMPLE_BOMS),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{bom_id}", response_model=BOMHeaderResponse)
async def get_bom(bom_id: int):
    """Retrieve full BOM structure including hierarchical components."""
    for bom in SAMPLE_BOMS:
        if bom.id == bom_id:
            return bom
    raise NotFoundException(message=f"BOM with ID {bom_id} not found")


@router.post("", response_model=BOMHeaderResponse, status_code=status.HTTP_201_CREATED)
async def create_bom(payload: BOMHeaderCreate, _=Depends(require_roles(["ADMIN", "MANAGER"]))):
    """Create a new Bill of Materials recipe."""
    for b in SAMPLE_BOMS:
        if b.bom_code == payload.bom_code:
            raise ConflictException(message=f"BOM code {payload.bom_code} already exists")

    items_res = [
        BOMItemResponse(
            id=100 + i,
            component_part_id=it.component_part_id,
            quantity_required=it.quantity_required,
            scrap_factor_percent=it.scrap_factor_percent,
            notes=it.notes,
        )
        for i, it in enumerate(payload.items)
    ]

    new_bom = BOMHeaderResponse(
        id=len(SAMPLE_BOMS) + 1,
        product_part_id=payload.product_part_id,
        bom_code=payload.bom_code,
        version=payload.version,
        description=payload.description,
        is_active=payload.is_active,
        items=items_res,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    SAMPLE_BOMS.append(new_bom)
    return new_bom
