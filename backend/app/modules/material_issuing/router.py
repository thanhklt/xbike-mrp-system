"""Persisted material issuing endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_material_issuing_service,
    get_pagination_params,
    require_roles,
)
from app.modules.material_issuing.schemas import (
    MaterialIssueRequestCreate,
    MaterialIssueRequestResponse,
)
from app.modules.material_issuing.service import MaterialIssuingService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/material-issuing",
    tags=["Material Issuing"],
    dependencies=[Depends(get_current_user_payload)],
)


@router.get("", response_model=PaginatedResponse[MaterialIssueRequestResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[MaterialIssuingService, Depends(get_material_issuing_service)],
):
    return await service.list_entries(params)


@router.get("/{issue_id}", response_model=MaterialIssueRequestResponse)
async def get_entry(
    issue_id: int, service: Annotated[MaterialIssuingService, Depends(get_material_issuing_service)]
):
    return await service.get_entry(issue_id)


@router.post("", response_model=MaterialIssueRequestResponse, status_code=201)
async def create_entry(
    payload: MaterialIssueRequestCreate,
    service: Annotated[MaterialIssuingService, Depends(get_material_issuing_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    return await service.create_entry(payload, actor)
