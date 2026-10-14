"""Persisted receiving endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.receiving.models import GoodsReceiptNote, ReceiptItem
from app.modules.receiving.schemas import GoodsReceiptNoteCreate, GoodsReceiptNoteResponse
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/receiving", tags=["Receiving"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[GoodsReceiptNoteResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(db, GoodsReceiptNote, GoodsReceiptNoteResponse, params)


@router.get("/{grn_id}", response_model=GoodsReceiptNoteResponse)
async def get_entry(grn_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(db, GoodsReceiptNote, grn_id)


@router.post("", response_model=GoodsReceiptNoteResponse, status_code=201)
async def create_entry(
    payload: GoodsReceiptNoteCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    return await create_record(
        db, GoodsReceiptNote, payload, actor, "phieu_nhap", child=(ReceiptItem, "phieu_nhap_id")
    )
