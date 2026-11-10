"""Employee and role endpoints delegate account policy to the public service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.request_context import get_request_id
from app.core.request_context import reject_query as validate_detail_query
from app.dependencies import get_current_user_payload, get_nhan_vien_service
from app.modules.nhan_vien.schemas import (
    DatLaiMatKhauInput,
    DoiVaiTroInput,
    EmployeeSort,
    EmployeeStatus,
    LyDoInput,
    NhanVienCreate,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
    NhanVienPatch,
    VaiTroListQuery,
    VaiTroListResponse,
)
from app.modules.nhan_vien.service import NhanVienService

router = APIRouter(prefix="/nhan_vien", tags=["nhan_vien"])
vai_tro_router = APIRouter(prefix="/vai_tro", tags=["nhan_vien"])

Actor = Annotated[dict, Depends(get_current_user_payload)]
Service = Annotated[NhanVienService, Depends(get_nhan_vien_service)]
RequestId = Annotated[str, Depends(get_request_id)]
EmployeeId = Annotated[int, Path(gt=0)]
IfMatch = Annotated[
    str | None,
    Header(alias="If-Match", description="Strong ETag từ GET chi tiết; thiếu trả 428, cũ trả 412"),
]

ETAG_HEADER = {"schema": {"type": "string"}, "description": "Strong resource ETag"}


def get_list_query(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    q: Annotated[str | None, Query()] = None,
    sort: Annotated[EmployeeSort, Query()] = "id",
    vai_tro_id: Annotated[int | None, Query(gt=0)] = None,
    trang_thai: Annotated[EmployeeStatus | None, Query()] = None,
) -> NhanVienListQuery:
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
    try:
        values: dict[str, object] = dict(request.query_params)
        values.update(
            page=page,
            page_size=page_size,
            q=q,
            sort=sort,
            vai_tro_id=vai_tro_id,
            trang_thai=trang_thai,
        )
        return NhanVienListQuery.model_validate(values)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("query", *error["loc"])} for error in exc.errors()]
        ) from exc


@router.get("", response_model=NhanVienListResponse)
async def list_entries(
    actor: Annotated[dict, Depends(get_current_user_payload)],
    params: Annotated[NhanVienListQuery, Depends(get_list_query)],
    service: Annotated[NhanVienService, Depends(get_nhan_vien_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhanVienListResponse:
    return await service.list_employees(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=NhanVienDetailResponse,
    dependencies=[Depends(validate_detail_query)],
    responses={
        200: {
            "headers": {
                "ETag": {"schema": {"type": "string"}, "description": "Strong resource ETag"}
            }
        }
    },
)
async def get_entry(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(get_current_user_payload)],
    service: Annotated[NhanVienService, Depends(get_nhan_vien_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> NhanVienDetailResponse:
    result, etag = await service.get_employee(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "",
    response_model=NhanVienDetailResponse,
    status_code=201,
    dependencies=[Depends(validate_detail_query)],
    responses={
        201: {
            "headers": {
                "ETag": ETAG_HEADER,
                "Location": {"schema": {"type": "string"}, "description": "Employee detail URL"},
            }
        }
    },
)
async def create_entry(
    params: NhanVienCreate,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    request: Request,
    response: Response,
) -> NhanVienDetailResponse:
    result, etag = await service.create_employee(params, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path.rstrip('/')}/{result.data.id}"
    return result


@router.patch(
    "/{id}",
    response_model=NhanVienDetailResponse,
    dependencies=[Depends(validate_detail_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def patch_entry(
    id: EmployeeId,
    params: NhanVienPatch,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> NhanVienDetailResponse:
    result, etag = await service.patch_employee(id, params, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.delete(
    "/{id}",
    status_code=204,
    dependencies=[Depends(validate_detail_query)],
    responses={204: {"headers": {"ETag": ETAG_HEADER}}},
)
async def delete_entry(
    id: EmployeeId,
    params: LyDoInput,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    if_match: IfMatch = None,
) -> Response:
    _, etag = await service.soft_delete_employee(id, actor, if_match, params.ly_do, request_id)
    return Response(status_code=204, headers={"ETag": etag})


@router.put(
    "/{id}/vai_tro",
    response_model=NhanVienDetailResponse,
    dependencies=[Depends(validate_detail_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def change_role(
    id: EmployeeId,
    params: DoiVaiTroInput,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> NhanVienDetailResponse:
    result, etag = await service.change_role(id, params.vai_tro_id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/mo_khoa",
    response_model=NhanVienDetailResponse,
    dependencies=[Depends(validate_detail_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def unlock_entry(
    id: EmployeeId,
    params: LyDoInput,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> NhanVienDetailResponse:
    result, etag = await service.unlock_employee(id, actor, if_match, params.ly_do, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/dat_lai_mat_khau",
    response_model=NhanVienDetailResponse,
    dependencies=[Depends(validate_detail_query)],
    responses={200: {"headers": {"ETag": ETAG_HEADER}}},
)
async def reset_password_entry(
    id: EmployeeId,
    params: DatLaiMatKhauInput,
    actor: Actor,
    service: Service,
    request_id: RequestId,
    response: Response,
    if_match: IfMatch = None,
) -> NhanVienDetailResponse:
    result, etag = await service.reset_password(
        id, params.mat_khau_moi.get_secret_value(), actor, if_match, request_id
    )
    response.headers["ETag"] = etag
    return result


def get_role_query(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> VaiTroListQuery:
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
    try:
        values: dict[str, object] = dict(request.query_params)
        values.update(page=page, page_size=page_size)
        return VaiTroListQuery.model_validate(values)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**error, "loc": ("query", *error["loc"])} for error in exc.errors()]
        ) from exc


@vai_tro_router.get("", response_model=VaiTroListResponse)
async def list_roles(
    actor: Actor,
    service: Service,
    request_id: RequestId,
    params: Annotated[VaiTroListQuery, Depends(get_role_query)],
) -> VaiTroListResponse:
    return await service.list_roles(params, actor, request_id)
