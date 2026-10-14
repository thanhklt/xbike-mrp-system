"""Persisted finished goods issuing endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.finished_goods_issuing.models import DispatchItem, FinishedGoodsDispatch
from app.modules.finished_goods_issuing.schemas import (
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.shared.database_queries import create_record, get_record, list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/finished-goods-issuing",
    tags=["Finished Goods Issuing"],
    dependencies=[Depends(get_current_user_payload)],
)


@router.get("", response_model=PaginatedResponse[FinishedGoodsDispatchResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_records(
        db,
        FinishedGoodsDispatch,
        FinishedGoodsDispatchResponse,
        params,
        FinishedGoodsDispatch.loai_phieu == "xuat_thanh_pham",
    )


@router.get("/{dispatch_id}", response_model=FinishedGoodsDispatchResponse)
async def get_entry(dispatch_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    return await get_record(
        db,
        FinishedGoodsDispatch,
        dispatch_id,
        FinishedGoodsDispatch.loai_phieu == "xuat_thanh_pham",
    )


@router.post("", response_model=FinishedGoodsDispatchResponse, status_code=201)
async def create_entry(
    payload: FinishedGoodsDispatchCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    if payload.loai_phieu != "xuat_thanh_pham":
        raise HTTPException(status_code=422, detail="Incorrect issue type for this endpoint")
    return await create_record(
        db,
        FinishedGoodsDispatch,
        payload,
        actor,
        "phieu_xuat",
        child=(DispatchItem, "phieu_xuat_id"),
    )
