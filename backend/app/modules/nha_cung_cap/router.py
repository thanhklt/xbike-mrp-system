"""Persisted suppliers endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import get_request_id, reject_query
from app.dependencies import (
    get_suppliers_service,
    require_roles,
)
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapDetailResponse,
    NhaCungCapListQuery,
    NhaCungCapListResponse,
    SupplierErrorResponse,
)
from app.modules.nha_cung_cap.service import SupplierService


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


read_actor = require_roles(["quan_ly"])
write_actor = require_roles(["quan_ly"])
router = APIRouter(
    prefix="/nha_cung_cap",
    tags=["nha_cung_cap"],
    responses={code: {"model": SupplierErrorResponse} for code in (401, 403, 422, 500)},
)


@router.get(
    "",
    response_model=NhaCungCapListResponse,
    dependencies=[Depends(read_actor), Depends(reject_repeated_query)],
)
async def list_suppliers(
    params: Annotated[NhaCungCapListQuery, Query()],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhaCungCapListResponse:
    return await service.list_suppliers(params, request_id)


@router.get(
    "/{id}",
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
    responses={404: {"model": SupplierErrorResponse}},
)
async def get_supplier(
    id: Annotated[int, Path(gt=0)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhaCungCapDetailResponse:
    return await service.get_supplier(id, request_id)


@router.post(
    "",
    status_code=201,
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
        409: {"model": SupplierErrorResponse},
    },
)
async def create_supplier(
    payload: NhaCungCapCreate,
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
    request: Request,
) -> NhaCungCapDetailResponse:
    result = await service.create_supplier(payload, actor, request_id)
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result
