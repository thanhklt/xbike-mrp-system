"""Persisted bom endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_bom_service,
    get_current_user_payload,
    get_pagination_params,
    require_roles,
)
from app.modules.bom.schemas import BOMHeaderCreate, BOMHeaderResponse
from app.modules.bom.service import BomService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(prefix="/bom", tags=["Bom"], dependencies=[Depends(get_current_user_payload)])


@router.get("", response_model=PaginatedResponse[BOMHeaderResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[BomService, Depends(get_bom_service)],
):
    return await service.list_entries(params)


@router.get("/{bom_id}", response_model=BOMHeaderResponse)
async def get_entry(bom_id: int, service: Annotated[BomService, Depends(get_bom_service)]):
    return await service.get_entry(bom_id)


@router.post("", response_model=BOMHeaderResponse, status_code=201)
async def create_entry(
    payload: BOMHeaderCreate,
    service: Annotated[BomService, Depends(get_bom_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.create_entry(payload, actor)
