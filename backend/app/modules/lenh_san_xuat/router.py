"""Seven contract v3 §9 endpoints. Orders originate only from submitted plans."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.core.request_context import (
    get_if_match,
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import get_lenh_san_xuat_service, require_roles
from app.modules.lenh_san_xuat.schemas import (
    LenhEmptyInput,
    LenhErrorResponse,
    LenhListResponse,
    LenhPatch,
    LenhQuery,
    LenhResponse,
    LyDoInput,
    VatTuLenhResponse,
)
from app.modules.lenh_san_xuat.service import LenhSanXuatService

read_actor = require_roles(["quan_ly", "nhan_vien"])
write_actor = require_roles(["quan_ly"])
start_actor = require_roles(["nhan_vien"])
ReadActor = Annotated[dict, Depends(read_actor)]
WriteActor = Annotated[dict, Depends(write_actor)]
StartActor = Annotated[dict, Depends(start_actor)]
Service = Annotated[LenhSanXuatService, Depends(get_lenh_san_xuat_service)]
ResourceId = Annotated[int, Path(gt=0, le=2**31 - 1)]
RequestId = Annotated[str, Depends(get_request_id)]
IfMatch = Annotated[str | None, Depends(get_if_match)]
ETAG: dict[int | str, dict[str, object]] = {
    200: {
        "headers": {
            "ETag": {
                "schema": {"type": "string"},
                "description": "Strong version of the order, source state and material snapshot",
            }
        }
    }
}
router = APIRouter(
    prefix="/lenh_san_xuat",
    tags=["lenh_san_xuat"],
    responses={
        code: {"model": LenhErrorResponse} for code in (401, 403, 404, 409, 412, 422, 428, 500)
    },
)


@router.get(
    "",
    response_model=LenhListResponse,
    dependencies=[Depends(read_actor), Depends(reject_repeated_query)],
)
async def list_entries(
    actor: ReadActor, params: Annotated[LenhQuery, Query()], service: Service, request_id: RequestId
) -> LenhListResponse:
    return await service.list_entries(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=LenhResponse,
    responses=ETAG,
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def get_entry(
    id: ResourceId, actor: ReadActor, service: Service, request_id: RequestId, response: Response
) -> LenhResponse:
    result, etag = await service.get_entry(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.get(
    "/{id}/vat_tu",
    response_model=VatTuLenhResponse,
    responses=ETAG,
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def materials(
    id: ResourceId, actor: ReadActor, service: Service, request_id: RequestId, response: Response
) -> VatTuLenhResponse:
    result, etag = await service.materials(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.patch(
    "/{id}",
    response_model=LenhResponse,
    responses=ETAG,
    dependencies=[Depends(write_actor), Depends(reject_query)],
)
async def patch_entry(
    id: ResourceId,
    payload: LenhPatch,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch,
) -> LenhResponse:
    result, etag = await service.patch_entry(id, payload, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/gui",
    response_model=LenhResponse,
    responses=ETAG,
    dependencies=[Depends(write_actor), Depends(reject_query)],
)
async def send(
    id: ResourceId,
    payload: LenhEmptyInput,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch,
) -> LenhResponse:
    result, etag = await service.send(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/bat_dau",
    response_model=LenhResponse,
    responses=ETAG,
    dependencies=[Depends(start_actor), Depends(reject_query)],
)
async def start(
    id: ResourceId,
    payload: LenhEmptyInput,
    actor: StartActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch,
) -> LenhResponse:
    result, etag = await service.start(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/huy",
    response_model=LenhResponse,
    responses=ETAG,
    dependencies=[Depends(write_actor), Depends(reject_query)],
)
async def cancel(
    id: ResourceId,
    payload: LyDoInput,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch,
) -> LenhResponse:
    result, etag = await service.cancel(id, payload.ly_do, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result
