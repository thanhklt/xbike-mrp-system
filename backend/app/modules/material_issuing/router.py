from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import require_roles
from app.modules.material_issuing.schemas import (
    MaterialIssueItemResponse,
    MaterialIssueRequestCreate,
    MaterialIssueRequestResponse,
)
from app.shared.enums import MaterialIssueStatus
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/material-issuing", tags=["Material Issuing & Picking"])

SAMPLE_ISSUES: List[MaterialIssueRequestResponse] = [
    MaterialIssueRequestResponse(
        id=1,
        request_number="MIR-2026-0034",
        work_order_id=1,
        status=MaterialIssueStatus.ISSUED,
        requested_by_user_id=2,
        issued_by_user_id=1,
        notes="Issued 10 chains & wheels for production batch #01",
        created_at=datetime.now(timezone.utc),
        issued_at=datetime.now(timezone.utc),
        items=[
            MaterialIssueItemResponse(
                id=1,
                part_id=2,
                part_number="XB-SUB-WHEEL-F",
                part_name="Front Wheel Assembly 700c",
                quantity_requested=10.0,
                quantity_issued=10.0,
                source_bin_location="B-04-12",
            )
        ],
    )
]


@router.get("", response_model=PaginatedResponse[MaterialIssueRequestResponse])
async def list_material_issues(params: PageParams = Depends(get_pagination_params)):
    """List shop floor material issue requests."""
    return create_paginated_response(
        items=SAMPLE_ISSUES,
        total_items=len(SAMPLE_ISSUES),
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{issue_id}", response_model=MaterialIssueRequestResponse)
async def get_material_issue(issue_id: int):
    """Get single material issue request."""
    for issue in SAMPLE_ISSUES:
        if issue.id == issue_id:
            return issue
    raise NotFoundException(message=f"Material issue request {issue_id} not found")


@router.post("", response_model=MaterialIssueRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_material_issue(
    payload: MaterialIssueRequestCreate,
    _=Depends(require_roles(["ADMIN", "PRODUCTION", "WAREHOUSE"])),
):
    """Create a pick list / material issue request for a Work Order."""
    for issue in SAMPLE_ISSUES:
        if issue.request_number == payload.request_number:
            raise ConflictException(message=f"Request {payload.request_number} already exists")

    items_res = [
        MaterialIssueItemResponse(
            id=len(SAMPLE_ISSUES) * 10 + i,
            part_id=it.part_id,
            part_number=f"PART-{it.part_id}",
            quantity_requested=it.quantity_requested,
            quantity_issued=it.quantity_issued,
            source_bin_location=it.source_bin_location,
        )
        for i, it in enumerate(payload.items)
    ]

    new_issue = MaterialIssueRequestResponse(
        id=len(SAMPLE_ISSUES) + 1,
        request_number=payload.request_number,
        work_order_id=payload.work_order_id,
        status=payload.status,
        notes=payload.notes,
        requested_by_user_id=1,
        created_at=datetime.now(timezone.utc),
        items=items_res,
    )
    SAMPLE_ISSUES.append(new_issue)
    return new_issue
