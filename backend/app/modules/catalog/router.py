"""Persisted catalog endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_catalog_service,
    get_current_user_payload,
    get_pagination_params,
    require_roles,
)
from app.modules.catalog.schemas import PartCreate, PartResponse
from app.modules.catalog.service import CatalogService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/catalog", tags=["Catalog"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/parts", response_model=PaginatedResponse[PartResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[CatalogService, Depends(get_catalog_service)],
):
    return await service.list_entries(params)


@router.get("/parts/{part_id}", response_model=PartResponse)
async def get_entry(part_id: int, service: Annotated[CatalogService, Depends(get_catalog_service)]):
    return await service.get_entry(part_id)


@router.post("/parts", response_model=PartResponse, status_code=201)
async def create_entry(
    payload: PartCreate,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.create_entry(payload, actor)
