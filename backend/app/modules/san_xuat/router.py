"""Production endpoints: requests (§8), orders (§9) and completion documents (§11)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import get_request_id, reject_query
from app.dependencies import (
    get_yeu_cau_san_xuat_service,
    require_roles,
)
from app.modules.san_xuat.schemas import (
    GuiYeuCauInput,
    GuiYeuCauResponse,
    HuyPreviewResponse,
    KiemTraInput,
    KiemTraPreviewResponse,
    KiemTraResponse,
    LyDoInput,
    NhuCauBoSungResponse,
    SanXuatErrorResponse,
    YeuCauCreate,
    YeuCauDetailResponse,
    YeuCauListQuery,
    YeuCauListResponse,
    YeuCauPatch,
)
from app.modules.san_xuat.service import (
    YeuCauSanXuatService,
)

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
CheckActor = Annotated[dict, Depends(require_roles(["nhan_vien"]))]
ETAG_HEADER = {"schema": {"type": "string"}, "description": "Strong ETag của yêu cầu"}
yeu_cau_sx_router = APIRouter(
    prefix="/yeu_cau_san_xuat",
    tags=["san_xuat"],
    responses={
        code: {"model": SanXuatErrorResponse} for code in (401, 403, 404, 409, 412, 422, 428, 500)
    },
)


nhu_cau_bo_sung_router = APIRouter(
    prefix="/nhu_cau_bo_sung_linh_kien",
    tags=["san_xuat"],
    responses={code: {"model": SanXuatErrorResponse} for code in (401, 403, 422, 500)},
)


# UC-27 Xem nhu cầu bổ sung linh kiện — Main 1–3; A1 endpoint chỉ đọc cho QLK (specs/use_cases/production/UC-27.md)
@nhu_cau_bo_sung_router.get(
    "", response_model=NhuCauBoSungResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
)
async def xem_nhu_cau_bo_sung(
    actor: WriteActor, service: Service, request_id: RequestId,
) -> NhuCauBoSungResponse:
    return await service.xem_nhu_cau_bo_sung(actor, request_id)


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


# UC-25 Xem danh sách yêu cầu sản xuất — Main 1–3; A1, A3 (specs/use_cases/production/UC-25.md)
@yeu_cau_sx_router.get(
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


# UC-25 Xem danh sách yêu cầu sản xuất — Main 4; A2 (specs/use_cases/production/UC-25.md)
@yeu_cau_sx_router.get(
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


# UC-23 Lập và gửi yêu cầu sản xuất — Main 4–6; A1 (specs/use_cases/production/UC-23.md)
@yeu_cau_sx_router.post(
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


# UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A1 sửa Nháp (specs/use_cases/production/UC-24.md)
@yeu_cau_sx_router.patch(
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


# UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — A2 xóa Nháp (specs/use_cases/production/UC-24.md)
@yeu_cau_sx_router.delete("/{id}", status_code=204, dependencies=[Depends(write_actor), Depends(reject_query)])
async def delete_entry(
    id: ResourceId,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch = None,
) -> Response:
    await service.delete_entry(id, actor, if_match)
    return Response(status_code=204)


# UC-23 Lập và gửi yêu cầu sản xuất — Main 7–9; A3 (specs/use_cases/production/UC-23.md)
# UC-24 Sửa, xóa, gửi yêu cầu sản xuất nháp — Main 5–7; A4, A5 (specs/use_cases/production/UC-24.md)
@yeu_cau_sx_router.post(
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
    result, etag = await service.gui(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


# UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 2–4; A5 xem trước chỉ đọc (specs/use_cases/production/UC-26.md)
@yeu_cau_sx_router.get(
    "/{id}/kiem_tra", response_model=KiemTraPreviewResponse,
    dependencies=[Depends(reject_query)],
)
async def xem_truoc_kiem_tra(
    id: ResourceId, actor: CheckActor, service: Service, request_id: RequestId,
) -> KiemTraPreviewResponse:
    return await service.xem_truoc_kiem_tra(id, actor, request_id)


# UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 5–8; A6 xác nhận với If-Match (specs/use_cases/production/UC-26.md)
@yeu_cau_sx_router.post(
    "/{id}/kiem_tra", response_model=KiemTraResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def kiem_tra(
    id: ResourceId, payload: KiemTraInput, actor: CheckActor, service: Service,
    request_id: RequestId, response: Response, if_match: IfMatch = None,
) -> KiemTraResponse:
    result, etag = await service.kiem_tra(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


# UC-28 Hủy yêu cầu sản xuất — D4 xem trước cho QLK (specs/use_cases/production/UC-28.md)
@yeu_cau_sx_router.get(
    "/{id}/huy", response_model=HuyPreviewResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
)
async def xem_truoc_huy(
    id: ResourceId, actor: WriteActor, service: Service, request_id: RequestId,
) -> HuyPreviewResponse:
    return await service.xem_truoc_huy(id, actor, request_id)


# UC-28 Hủy yêu cầu sản xuất — Main 3, 6–7 xác nhận với lý do và If-Match (specs/use_cases/production/UC-28.md)
@yeu_cau_sx_router.post(
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


# UC-29 Bắt đầu sản xuất — Main 2–5; A1, A2 kiểm quyền, body và ETag (specs/use_cases/production/UC-29.md)
@yeu_cau_sx_router.post(
    "/{id}/bat_dau", response_model=YeuCauDetailResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def bat_dau(
    id: ResourceId, payload: GuiYeuCauInput, actor: CheckActor, service: Service,
    request_id: RequestId, response: Response, if_match: IfMatch = None,
) -> YeuCauDetailResponse:
    result, etag = await service.bat_dau(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result
