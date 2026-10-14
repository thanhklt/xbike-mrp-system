"""Persisted catalog endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.catalog.models import Part
from app.modules.catalog.schemas import PartCreate, PartResponse
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/catalog", tags=["Catalog"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("/parts", response_model=PaginatedResponse[PartResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, Part, PartResponse, params)


@router.get("/parts/{part_id}", response_model=PartResponse)
async def get_entry(part_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(db, Part, part_id)


@router.post("/parts", response_model=PartResponse, status_code=201)
async def create_entry(
    payload: PartCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await create_record(db, Part, payload, actor, "mat_hang")
