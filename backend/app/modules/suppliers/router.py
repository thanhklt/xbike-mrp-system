from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse, SupplierUpdate
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

SAMPLE_SUPPLIERS: List[SupplierResponse] = [
    SupplierResponse(
        id=1,
        code="SUP-SHIMANO-VN",
        name="Shimano Global Bike Components",
        contact_name="Kenji Sato",
        contact_email="kenji.s@shimano-components.com",
        contact_phone="+84-901-234-567",
        address="VSIP Industrial Park, Binh Duong, Vietnam",
        payment_terms_days=30,
        lead_time_days=14,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
    SupplierResponse(
        id=2,
        code="SUP-ALUFRAME-CORP",
        name="Apex Precision Alloy Frames",
        contact_name="Le Van An",
        contact_email="an.le@apex-frames.vn",
        contact_phone="+84-918-765-432",
        address="Long Thanh High Tech Park, Dong Nai, Vietnam",
        payment_terms_days=45,
        lead_time_days=21,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    ),
]


@router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_suppliers(params: PageParams = Depends(get_pagination_params)):
    """List approved vendor list / suppliers with pagination."""
    return create_paginated_response(
        items=SAMPLE_SUPPLIERS,
        total_items=len(SAMPLE_SUPPLIERS),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(supplier_id: int):
    """Retrieve supplier details."""
    for s in SAMPLE_SUPPLIERS:
        if s.id == supplier_id:
            return s
    raise NotFoundException(message=f"Supplier {supplier_id} not found")


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(payload: SupplierCreate, _=Depends(require_roles(["ADMIN", "MANAGER"]))):
    """Register a new vendor/supplier."""
    for s in SAMPLE_SUPPLIERS:
        if s.code == payload.code:
            raise ConflictException(message=f"Supplier code {payload.code} already exists")

    new_supp = SupplierResponse(
        id=len(SAMPLE_SUPPLIERS) + 1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        **payload.model_dump(),
    )
    SAMPLE_SUPPLIERS.append(new_supp)
    return new_supp
