"""Register employee GET endpoints and delegate business logic to the service."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload
from app.modules.users import service
from app.modules.users.schemas import (
    EmployeeSort,
    EmployeeStatus,
    NhanVienDetailResponse,
    NhanVienListQuery,
    NhanVienListResponse,
)

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
        values = dict(request.query_params)
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


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None) or str(uuid4())
    request.state.request_id = request_id
    return request_id


def validate_detail_query(request: Request) -> None:
    if request.query_params:
        raise RequestValidationError(
            [
                {
                    "loc": ("query", key),
                    "msg": "Extra inputs are not permitted",
                    "type": "extra_forbidden",
                }
                for key in request.query_params
            ]
        )


@router.get("", response_model=NhanVienListResponse)
async def list_entries(
    actor: Annotated[dict, Depends(get_current_user_payload)],
    params: Annotated[NhanVienListQuery, Depends(get_list_query)],
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhanVienListResponse:
    return await service.list_employees(db, params, actor, request_id)


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
    db: Annotated[AsyncSession, Depends(get_db)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> NhanVienDetailResponse:
    result, etag = await service.get_employee(db, id, actor, request_id)
    response.headers["ETag"] = etag
    return result
