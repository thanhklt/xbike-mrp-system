"""Persisted finished goods issuing endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_current_user_payload,
    get_finished_goods_issuing_service,
    get_pagination_params,
    require_roles,
)
from app.modules.finished_goods_issuing.schemas import (
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.modules.finished_goods_issuing.service import FinishedGoodsIssuingService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/finished-goods-issuing",
    tags=["Finished Goods Issuing"],
    dependencies=[Depends(get_current_user_payload)],
)


@router.get("", response_model=PaginatedResponse[FinishedGoodsDispatchResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[FinishedGoodsIssuingService, Depends(get_finished_goods_issuing_service)],
):
    return await service.list_entries(params)


@router.get("/{dispatch_id}", response_model=FinishedGoodsDispatchResponse)
async def get_entry(
    dispatch_id: int,
    service: Annotated[FinishedGoodsIssuingService, Depends(get_finished_goods_issuing_service)],
):
    return await service.get_entry(dispatch_id)


@router.post("", response_model=FinishedGoodsDispatchResponse, status_code=201)
async def create_entry(
    payload: FinishedGoodsDispatchCreate,
    service: Annotated[FinishedGoodsIssuingService, Depends(get_finished_goods_issuing_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    return await service.create_entry(payload, actor)
