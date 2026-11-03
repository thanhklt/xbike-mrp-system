"""The seven production-order endpoints from contract v2."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_lenh_san_xuat_service, require_roles
from app.modules.lenh_san_xuat.schemas import (
    DetailResponse,
    EmptyInput,
    LenhErrorResponse,
    LenhListQuery,
    LenhListResponse,
    LenhRead,
    LyDoInput,
    NguoiThucHienInput,
    VatTuLenhRead,
)
from app.modules.lenh_san_xuat.service import LenhSanXuatService

router = APIRouter(
    prefix="/lenh_san_xuat",
    tags=["Lệnh sản xuất"],
    responses={code: {"model": LenhErrorResponse} for code in (401, 403, 404, 409, 422, 500)},
)
read_actor = require_roles(["quan_ly", "nhan_vien"])
manager = require_roles(["quan_ly"])
worker = require_roles(["nhan_vien"])
OrderId = Annotated[int, Path(gt=0)]
Service = Annotated[LenhSanXuatService, Depends(get_lenh_san_xuat_service)]
RequestId = Annotated[str, Depends(get_request_id)]


@router.get("", response_model=LenhListResponse, dependencies=[Depends(read_actor)])
async def list_orders(
    params: Annotated[LenhListQuery, Query()], service: Service, request_id: RequestId
):
    return await service.list_orders(params, request_id)


@router.get(
    "/{id}",
    response_model=DetailResponse[LenhRead],
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def get_order(id: OrderId, service: Service, request_id: RequestId):
    return await service.get_order(id, request_id)


@router.get(
    "/{id}/vat_tu",
    response_model=DetailResponse[VatTuLenhRead],
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def get_materials(id: OrderId, service: Service, request_id: RequestId):
    return await service.get_materials(id, request_id)


@router.patch(
    "/{id}", response_model=DetailResponse[LenhRead], dependencies=[Depends(reject_query)]
)
async def assign(
    id: OrderId,
    payload: NguoiThucHienInput,
    actor: Annotated[dict, Depends(manager)],
    service: Service,
    request_id: RequestId,
):
    return await service.assign(id, payload.nhan_vien_id, actor, request_id)


@router.post(
    "/{id}/gui", response_model=DetailResponse[LenhRead], dependencies=[Depends(reject_query)]
)
async def send(
    id: OrderId,
    payload: EmptyInput,
    actor: Annotated[dict, Depends(manager)],
    service: Service,
    request_id: RequestId,
):
    return await service.send(id, actor, request_id)


@router.post(
    "/{id}/bat_dau", response_model=DetailResponse[LenhRead], dependencies=[Depends(reject_query)]
)
async def start(
    id: OrderId,
    payload: EmptyInput,
    actor: Annotated[dict, Depends(worker)],
    service: Service,
    request_id: RequestId,
):
    return await service.start(id, actor, request_id)


@router.post(
    "/{id}/huy", response_model=DetailResponse[LenhRead], dependencies=[Depends(reject_query)]
)
async def cancel(
    id: OrderId,
    payload: LyDoInput,
    actor: Annotated[dict, Depends(manager)],
    service: Service,
    request_id: RequestId,
):
    return await service.cancel(id, payload.ly_do, actor, request_id)
