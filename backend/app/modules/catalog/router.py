from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.catalog.schemas import PartCreate, PartResponse, PartUpdate
from app.shared.enums import ItemType, PartCategory, UnitOfMeasure
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/catalog", tags=["Catalog & Materials"])

# Sample bicycle components for initial seed/demo
SAMPLE_PARTS: List[PartResponse] = [
    PartResponse(
        id=1,
        part_number="XB-BIKE-URBAN-01",
        name="xBike Urban Commuter E-Bike",
        description="Premium aluminum electric commuter bicycle with internal hub",
        item_type=ItemType.FINISHED_GOOD,
        category=PartCategory.FRAME,
        unit=UnitOfMeasure.PCS,
        lead_time_days=14,
        safety_stock=5.0,
        standard_cost=1250.00,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    PartResponse(
        id=2,
        part_number="XB-SUB-WHEEL-F",
        name="Front Wheel Assembly 700c",
        description="Front rim, hub, 36 spokes, and hydraulic disc rotor",
        item_type=ItemType.SUB_ASSEMBLY,
        category=PartCategory.WHEEL,
        unit=UnitOfMeasure.SET,
        lead_time_days=5,
        safety_stock=20.0,
        standard_cost=65.00,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    PartResponse(
        id=3,
        part_number="XB-RAW-RIM-700C",
        name="Double-wall Alloy Rim 700c 36H",
        description="Black anodized 6061 rim",
        item_type=ItemType.RAW_MATERIAL,
        category=PartCategory.WHEEL,
        unit=UnitOfMeasure.PCS,
        lead_time_days=10,
        safety_stock=50.0,
        standard_cost=18.50,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    PartResponse(
        id=4,
        part_number="XB-RAW-CHN-11S",
        name="11-Speed Bicycle Chain with Quick Link",
        description="Nickel plated corrosion resistant chain",
        item_type=ItemType.RAW_MATERIAL,
        category=PartCategory.DRIVETRAIN,
        unit=UnitOfMeasure.PCS,
        lead_time_days=7,
        safety_stock=40.0,
        standard_cost=14.00,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
]


@router.get("/parts", response_model=PaginatedResponse[PartResponse])
async def list_parts(params: PageParams = Depends(get_pagination_params)):
    """List catalog parts and materials with search filter."""
    filtered = SAMPLE_PARTS
    if params.search:
        term = params.search.lower()
        filtered = [p for p in filtered if term in p.name.lower() or term in p.part_number.lower()]

    return create_paginated_response(
        items=filtered,
        total_items=len(filtered),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/parts/{part_id}", response_model=PartResponse)
async def get_part(part_id: int):
    """Retrieve single part details by ID."""
    for part in SAMPLE_PARTS:
        if part.id == part_id:
            return part
    raise NotFoundException(message=f"Part with ID {part_id} not found")


@router.post("/parts", response_model=PartResponse, status_code=status.HTTP_201_CREATED)
async def create_part(payload: PartCreate, _=Depends(require_roles(["ADMIN", "MANAGER"]))):
    """Create a new catalog item (raw material, assembly or finished bike)."""
    for part in SAMPLE_PARTS:
        if part.part_number == payload.part_number:
            raise ConflictException(message=f"Part number {payload.part_number} already exists")

    new_part = PartResponse(
        id=len(SAMPLE_PARTS) + 1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    SAMPLE_PARTS.append(new_part)
    return new_part
