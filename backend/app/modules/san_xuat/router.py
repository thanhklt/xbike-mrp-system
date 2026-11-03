"""Nine production-request endpoints from contract v3 §8."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_yeu_cau_san_xuat_service, require_roles
from app.modules.san_xuat.schemas import (
    GuiYeuCauInput,
    GuiYeuCauResponse,
    KeHoachPreviewResponse,
    KeHoachResponse,
    LyDoInput,
    SanXuatErrorResponse,
    TinhKeHoachInput,
    YeuCauCreate,
    YeuCauDetailResponse,
    YeuCauListQuery,
    YeuCauListResponse,
    YeuCauPatch,
)
from app.modules.san_xuat.service import YeuCauSanXuatService

read_actor = require_roles(["quan_ly", "nhan_vien"])
write_actor = require_roles(["quan_ly"])
ReadActor = Annotated[dict, Depends(read_actor)]
WriteActor = Annotated[dict, Depends(write_actor)]
Service = Annotated[YeuCauSanXuatService, Depends(get_yeu_cau_san_xuat_service)]
RequestId = Annotated[str, Depends(get_request_id)]
ResourceId = Annotated[int, Path(gt=0)]
IfMatch = Annotated[
    str | None, Header(alias="If-Match", description="Strong ETag; thiếu 428, cũ/weak/* 412")
]
ETAG_HEADER = {"schema": {"type": "string"}, "description": "Strong ETag của yêu cầu"}
router = APIRouter(
    prefix="/yeu_cau_san_xuat",
    tags=["san_xuat"],
    responses={
        code: {"model": SanXuatErrorResponse} for code in (401, 403, 404, 409, 412, 422, 428, 500)
    },
)


def reject_repeated_query(request: Request) -> None:
    repeated = [key for key in request.query_params if len(request.query_params.getlist(key)) > 1]
    if repeated:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", key),
                    "msg": "Query parameter must appear once",
                    "type": "value_error",
                }
                for key in repeated
            ]
        )


@router.get(
    "",
    response_model=YeuCauListResponse,
    dependencies=[Depends(read_actor), Depends(reject_repeated_query)],
)
async def list_entries(
    actor: ReadActor,
    params: Annotated[YeuCauListQuery, Query()],
    service: Service,
    request_id: RequestId,
) -> YeuCauListResponse:
    return await service.list_entries(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=YeuCauDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def get_entry(
    id: ResourceId,
    actor: ReadActor,
    service: Service,
    request_id: RequestId,
    response: Response,
) -> YeuCauDetailResponse:
    result, etag = await service.get_entry(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "",
    status_code=201,
    response_model=YeuCauDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={201: {"headers": {"ETag": ETAG_HEADER, "Location": {"schema": {"type": "string"}}}}},
)
async def create_entry(
    payload: YeuCauCreate,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    request: Request,
    response: Response,
) -> YeuCauDetailResponse:
    result, etag = await service.create_entry(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.patch(
    "/{id}",
    response_model=YeuCauDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def patch_entry(
    id: ResourceId,
    payload: YeuCauPatch,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> YeuCauDetailResponse:
    result, etag = await service.patch_entry(id, payload, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.delete("/{id}", status_code=204, dependencies=[Depends(write_actor), Depends(reject_query)])
async def delete_entry(
    id: ResourceId,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch = None,
) -> Response:
    await service.delete_entry(id, actor, if_match)
    return Response(status_code=204)


@router.post(
    "/{id}/tinh_ke_hoach",
    response_model=KeHoachPreviewResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def tinh_ke_hoach(
    id: ResourceId,
    payload: TinhKeHoachInput,
    actor: ReadActor,
    service: Service,
    request_id: RequestId,
) -> KeHoachPreviewResponse:
    return await service.tinh_ke_hoach(id, actor, request_id)


@router.post(
    "/{id}/gui",
    response_model=GuiYeuCauResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def gui(
    id: ResourceId,
    payload: GuiYeuCauInput,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> GuiYeuCauResponse:
    result, etag = await service.gui(id, payload.ke_hoach_token, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.get(
    "/{id}/ke_hoach",
    response_model=KeHoachResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
)
async def ke_hoach(
    id: ResourceId,
    actor: ReadActor,
    service: Service,
    request_id: RequestId,
) -> KeHoachResponse:
    return await service.ke_hoach(id, actor, request_id)


@router.post(
    "/{id}/huy",
    response_model=YeuCauDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def huy(
    id: ResourceId,
    payload: LyDoInput,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> YeuCauDetailResponse:
    result, etag = await service.huy(id, payload.ly_do, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result
