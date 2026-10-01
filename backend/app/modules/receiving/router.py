from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.receiving.schemas import GoodsReceiptNoteCreate, GoodsReceiptNoteResponse, ReceiptItemResponse
from app.shared.enums import GoodsReceiptStatus
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/receiving", tags=["Receiving & Inspection"])

SAMPLE_GRNS: List[GoodsReceiptNoteResponse] = [
    GoodsReceiptNoteResponse(
        id=1,
        grn_number="GRN-2026-0089",
        purchase_order_number="PO-2026-004",
        supplier_id=1,
        supplier_name="Shimano Global Bike Components",
        status=GoodsReceiptStatus.ACCEPTED,
        received_by_user_id=1,
        notes="All 50 chains inspected; tolerance passed.",
        received_at=datetime.now(timezone.utc),
        items=[
            ReceiptItemResponse(
                id=1,
                part_id=4,
                part_number="XB-RAW-CHN-11S",
                part_name="11-Speed Bicycle Chain",
                quantity_shipped=50.0,
                quantity_accepted=50.0,
                quantity_rejected=0.0,
                lot_number="LOT-SHM-2026-Q1",
            )
        ],
    )
]


@router.get("", response_model=PaginatedResponse[GoodsReceiptNoteResponse])
async def list_receipts(params: PageParams = Depends(get_pagination_params)):
    """List inbound goods receipt notes."""
    return create_paginated_response(
        items=SAMPLE_GRNS,
        total_items=len(SAMPLE_GRNS),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{grn_id}", response_model=GoodsReceiptNoteResponse)
async def get_receipt(grn_id: int):
    """Retrieve goods receipt details."""
    for grn in SAMPLE_GRNS:
        if grn.id == grn_id:
            return grn
    raise NotFoundException(message=f"GRN with ID {grn_id} not found")


@router.post("", response_model=GoodsReceiptNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_receipt(payload: GoodsReceiptNoteCreate, _=Depends(require_roles(["ADMIN", "WAREHOUSE", "QUALITY"]))):
    """Log an inbound delivery for QA inspection."""
    for g in SAMPLE_GRNS:
        if g.grn_number == payload.grn_number:
            raise ConflictException(message=f"GRN {payload.grn_number} already registered")

    items_res = [
        ReceiptItemResponse(
            id=len(SAMPLE_GRNS) * 10 + i,
            part_id=it.part_id,
            part_number=f"PART-{it.part_id}",
            quantity_shipped=it.quantity_shipped,
            quantity_accepted=it.quantity_accepted,
            quantity_rejected=it.quantity_rejected,
            lot_number=it.lot_number,
        )
        for i, it in enumerate(payload.items)
    ]

    new_grn = GoodsReceiptNoteResponse(
        id=len(SAMPLE_GRNS) + 1,
        grn_number=payload.grn_number,
        purchase_order_number=payload.purchase_order_number,
        supplier_id=payload.supplier_id,
        supplier_name="Vendor Partner",
        status=payload.status,
        notes=payload.notes,
        received_by_user_id=1,
        received_at=datetime.now(timezone.utc),
        items=items_res,
    )
    SAMPLE_GRNS.append(new_grn)
    return new_grn
