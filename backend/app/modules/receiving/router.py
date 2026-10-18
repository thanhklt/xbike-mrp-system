"""Persisted receiving endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_pagination_params,
    get_receiving_service,
    require_roles,
)
from app.modules.receiving.schemas import GoodsReceiptNoteCreate, GoodsReceiptNoteResponse
from app.modules.receiving.service import ReceivingService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/receiving", tags=["Receiving"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[GoodsReceiptNoteResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
):
    return await service.list_entries(params)


@router.get("/{grn_id}", response_model=GoodsReceiptNoteResponse)
async def get_entry(
    grn_id: int, service: Annotated[ReceivingService, Depends(get_receiving_service)]
):
    return await service.get_entry(grn_id)


@router.post("", response_model=GoodsReceiptNoteResponse, status_code=201)
async def create_entry(
    payload: GoodsReceiptNoteCreate,
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    return await service.create_entry(payload, actor)
