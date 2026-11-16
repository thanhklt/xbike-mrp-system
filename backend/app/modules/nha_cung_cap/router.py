"""Persisted suppliers endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.core.request_context import (
    get_request_id,
    get_strong_if_match,
    reject_body,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import (
    get_suppliers_service,
    require_roles,
)
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapDetailResponse,
    NhaCungCapListQuery,
    NhaCungCapListResponse,
    NhaCungCapPatch,
    SupplierErrorResponse,
)
from app.modules.nha_cung_cap.service import SupplierService

read_actor = require_roles(["quan_tri_vien", "quan_ly"])
write_actor = require_roles(["quan_ly"])
etag_header = {
    "ETag": {
        "schema": {"type": "string"},
        "description": "Strong ETag of current supplier information",
    }
}
router = APIRouter(
    prefix="/nha_cung_cap",
    tags=["nha_cung_cap"],
    responses={code: {"model": SupplierErrorResponse} for code in (401, 403, 422, 500)},
)


@router.get(
    "",
    response_model=NhaCungCapListResponse,
    dependencies=[Depends(read_actor), Depends(reject_repeated_query), Depends(reject_body)],
)
async def list_suppliers(
    params: Annotated[NhaCungCapListQuery, Query()],
    actor: Annotated[dict, Depends(read_actor)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhaCungCapListResponse:
    """UC-13: specs/use_cases/catalog/UC-13.md. Combined filters and stable pagination."""
    return await service.list_suppliers(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query), Depends(reject_body)],
    responses={200: {"headers": etag_header}, 404: {"model": SupplierErrorResponse}},
)
async def get_supplier(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(read_actor)],
    response: Response,
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> NhaCungCapDetailResponse:
    """UC-13: specs/use_cases/catalog/UC-13.md."""
    result, tag = await service.get_supplier(id, actor, request_id)
    response.headers["ETag"] = tag
    return result


@router.post(
    "",
    status_code=201,
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        201: {"headers": {**etag_header, "Location": {"schema": {"type": "string"}}}},
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
    """UC-14: specs/use_cases/catalog/UC-14.md."""
    result, tag = await service.create_supplier(payload, actor, request_id)
    response.headers["ETag"] = tag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.patch(
    "/{id}",
    response_model=NhaCungCapDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        200: {"headers": etag_header},
        **{code: {"model": SupplierErrorResponse} for code in (404, 409, 412, 428)},
    },
)
async def patch_supplier(
    id: Annotated[int, Path(gt=0)],
    payload: NhaCungCapPatch,
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[SupplierService, Depends(get_suppliers_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
    if_match: Annotated[str | None, Depends(get_strong_if_match)] = None,
) -> NhaCungCapDetailResponse:
    """UC-44: specs/use_cases/catalog/UC-44.md. If-Match is required (428)."""
    result, tag = await service.patch_supplier(id, payload, actor, if_match, request_id)
    response.headers["ETag"] = tag
    return result
