"""Register employee GET endpoints and delegate business logic to the service."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.request_context import get_request_id
from app.core.request_context import reject_query as validate_detail_query
from app.dependencies import get_current_user_payload, get_users_service
from app.modules.users.schemas import (
    EmployeeSort,
    EmployeeStatus,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/nhan_vien", tags=["nhan_vien"])


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
    service: Annotated[UserService, Depends(get_users_service)],
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
    service: Annotated[UserService, Depends(get_users_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> NhanVienDetailResponse:
    result, etag = await service.get_employee(id, actor, request_id)
    response.headers["ETag"] = etag
    return result
