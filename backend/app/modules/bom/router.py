"""Persisted bom endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.bom.models import BOMHeader, BOMItem
from app.modules.bom.schemas import BOMHeaderCreate, BOMHeaderResponse
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(prefix="/bom", tags=["Bom"], dependencies=[Depends(get_current_user_payload)])


@router.get("", response_model=PaginatedResponse[BOMHeaderResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, BOMHeader, BOMHeaderResponse, params)


@router.get("/{bom_id}", response_model=BOMHeaderResponse)
async def get_entry(bom_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(db, BOMHeader, bom_id)


@router.post("", response_model=BOMHeaderResponse, status_code=201)
async def create_entry(
    payload: BOMHeaderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await create_record(
        db, BOMHeader, payload, actor, "cong_thuc", child=(BOMItem, "bom_id")
    )
