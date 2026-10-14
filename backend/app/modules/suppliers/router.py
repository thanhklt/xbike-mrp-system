"""Persisted suppliers endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.suppliers.models import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/suppliers", tags=["Suppliers"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, Supplier, SupplierResponse, params)


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_entry(supplier_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(db, Supplier, supplier_id)


@router.post("", response_model=SupplierResponse, status_code=201)
async def create_entry(
    payload: SupplierCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await create_record(db, Supplier, payload, actor, "nha_cung_cap")
