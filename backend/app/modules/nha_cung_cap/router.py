"""Persisted suppliers endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import get_request_id, reject_query
from app.dependencies import (
    get_current_user_payload,
    get_pagination_params,
    get_suppliers_service,
    require_roles,
)
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapDetailResponse,
    NhaCungCapListQuery,
    NhaCungCapListResponse,
    NhaCungCapPatch,
    SupplierCreate,
    SupplierErrorResponse,
    SupplierResponse,
)
from app.modules.nha_cung_cap.service import SupplierService
from app.shared.pagination import PageParams, PaginatedResponse

legacy_router = APIRouter(
    prefix="/suppliers", tags=["Suppliers"], dependencies=[Depends(get_current_user_payload)]
)

@legacy_router.get("", response_model=PaginatedResponse[SupplierResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
):
    return await service.list_entries(params)


@legacy_router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_entry(
    supplier_id: int, service: Annotated[SupplierService, Depends(get_suppliers_service)]
):
    return await service.get_entry(supplier_id)


@legacy_router.post("", response_model=SupplierResponse, status_code=201)
async def create_entry(
    payload: SupplierCreate,
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.create_entry(payload, actor)


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


def get_if_match(
    request: Request,
    if_match: Annotated[
        str | None,
        Header(description="Strong ETag from GET detail; required at runtime (428 if missing)"),
    ] = None,
) -> str | None:
    if len(request.headers.getlist("if-match")) > 1:
        raise RequestValidationError(
            [
                {
                    "loc": ("header", "If-Match"),
                    "msg": "If-Match must appear once",
                    "type": "value_error",
                }
            ]
        )
    return if_match


read_actor = require_roles(["quan_tri_vien", "quan_ly"])
write_actor = require_roles(["quan_ly"])
contract_router = APIRouter(
    prefix="/nha_cung_cap",
    tags=["nha_cung_cap"],
    responses={code: {"model": SupplierErrorResponse} for code in (401, 403, 422, 500)},
)
detail_headers = {"ETag": {"schema": {"type": "string"}, "description": "Strong resource ETag"}}
mutation_errors = {code: {"model": SupplierErrorResponse} for code in (404, 409, 412, 428)}


@contract_router.get(
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


@contract_router.get(
    "/{id}",
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
    responses={200: {"headers": detail_headers}, 404: {"model": SupplierErrorResponse}},
)
async def get_supplier(
    id: Annotated[int, Path(gt=0)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> NhaCungCapDetailResponse:
    result, etag = await service.get_supplier(id, request_id)
    response.headers["ETag"] = etag
    return result


@contract_router.post(
    "",
    status_code=201,
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        201: {"headers": {**detail_headers, "Location": {"schema": {"type": "string"}}}},
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
    result, etag = await service.create_supplier(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@contract_router.patch(
    "/{id}",
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={**mutation_errors, 200: {"headers": detail_headers}},
)
async def patch_supplier(
    id: Annotated[int, Path(gt=0)],
    payload: NhaCungCapPatch,
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    if_match: Annotated[str | None, Depends(get_if_match)],
    response: Response,
) -> NhaCungCapDetailResponse:
    result, etag = await service.patch_supplier(id, payload, if_match, actor, request_id)
    response.headers["ETag"] = etag
    return result


@contract_router.delete(
    "/{id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses=mutation_errors,
)
async def delete_supplier(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    if_match: Annotated[str | None, Depends(get_if_match)],
) -> Response:
    await service.delete_supplier(id, if_match, actor)
    return Response(status_code=204)


router = APIRouter()
router.include_router(contract_router)
router.include_router(legacy_router)
