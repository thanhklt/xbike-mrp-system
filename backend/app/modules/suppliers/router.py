"""Persisted suppliers endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_pagination_params,
    get_suppliers_service,
    require_roles,
)
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse
from app.modules.suppliers.service import SupplierService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/suppliers", tags=["Suppliers"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
):
    return await service.list_entries(params)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_entry(
    supplier_id: int, service: Annotated[SupplierService, Depends(get_suppliers_service)]
):
    return await service.get_entry(supplier_id)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_entry(
    payload: SupplierCreate,
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.create_entry(payload, actor)
