"""Persisted receiving endpoints. Demo data lives only in seed.sql."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.core.request_context import (
    get_if_match,
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import (
    get_current_user_payload,
    get_pagination_params,
    get_receiving_service,
    require_roles,
)
from app.modules.phieu_nhap.schemas import (
    GoodsReceiptNoteCreate,
    GoodsReceiptNoteResponse,
    PhieuNhapActionResponse,
    PhieuNhapCompleteInput,
    PhieuNhapCreate,
    PhieuNhapDetailResponse,
    PhieuNhapErrorResponse,
    PhieuNhapListQuery,
    PhieuNhapListResponse,
    PhieuNhapPatch,
)
from app.modules.phieu_nhap.service import ReceivingService
from app.shared.pagination import PageParams, PaginatedResponse

legacy_router = APIRouter(
    prefix="/receiving", tags=["Receiving"], dependencies=[Depends(get_current_user_payload)]
)


@legacy_router.get("", response_model=PaginatedResponse[GoodsReceiptNoteResponse])
async def list_entries(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
):
    return await service.list_entries(params)


@legacy_router.get("/{grn_id}", response_model=GoodsReceiptNoteResponse)
async def get_entry(
    grn_id: int, service: Annotated[ReceivingService, Depends(get_receiving_service)]
):
    return await service.get_entry(grn_id)


@legacy_router.post("", response_model=GoodsReceiptNoteResponse, status_code=201)
async def create_entry(
    payload: GoodsReceiptNoteCreate,
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly", "nhan_vien"]))],
):
    return await service.create_entry(payload, actor)


receipt_actor = require_roles(["quan_ly"])
contract_router = APIRouter(
    prefix="/phieu_nhap",
    tags=["phieu_nhap"],
    dependencies=[Depends(receipt_actor)],
    responses={code: {"model": PhieuNhapErrorResponse} for code in (401, 403, 422, 500)},
)
detail_headers = {
    "ETag": {"schema": {"type": "string"}, "description": "Strong ETag including receipt items"}
}


@contract_router.get(
    "", response_model=PhieuNhapListResponse, dependencies=[Depends(reject_repeated_query)]
)
async def list_receipts(
    params: Annotated[PhieuNhapListQuery, Query()],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> PhieuNhapListResponse:
    return await service.list_receipts(params, request_id)


@contract_router.get(
    "/{id}",
    response_model=PhieuNhapDetailResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": detail_headers}, 404: {"model": PhieuNhapErrorResponse}},
)
async def get_receipt(
    id: Annotated[int, Path(gt=0)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.get_receipt(id, request_id)
    response.headers["ETag"] = etag
    return result


@contract_router.post(
    "",
    status_code=201,
    response_model=PhieuNhapDetailResponse,
    dependencies=[Depends(reject_query)],
    responses={
        201: {"headers": {**detail_headers, "Location": {"schema": {"type": "string"}}}},
        404: {"model": PhieuNhapErrorResponse},
        409: {"model": PhieuNhapErrorResponse},
    },
)
async def create_receipt(
    payload: PhieuNhapCreate,
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    request: Request,
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.create_receipt(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


mutation_errors = {code: {"model": PhieuNhapErrorResponse} for code in (404, 409, 412, 428)}


@contract_router.patch(
    "/{id}",
    response_model=PhieuNhapDetailResponse,
    dependencies=[Depends(reject_query)],
    responses={**mutation_errors, 200: {"headers": detail_headers}},
)
async def patch_receipt(
    id: Annotated[int, Path(gt=0)],
    payload: PhieuNhapPatch,
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    if_match: Annotated[str | None, Depends(get_if_match)],
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.patch_receipt(id, payload, if_match, actor, request_id)
    response.headers["ETag"] = etag
    return result


@contract_router.delete(
    "/{id}",
    status_code=204,
    response_class=Response,
    dependencies=[Depends(reject_query)],
    responses=mutation_errors,
)
async def delete_receipt(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    if_match: Annotated[str | None, Depends(get_if_match)],
) -> Response:
    await service.delete_receipt(id, if_match, actor)
    return Response(status_code=204)


@contract_router.post(
    "/{id}/hoan_tat",
    response_model=PhieuNhapActionResponse,
    dependencies=[Depends(reject_query)],
    responses={**mutation_errors, 200: {"headers": detail_headers}},
)
async def complete_receipt(
    id: Annotated[int, Path(gt=0)],
    payload: PhieuNhapCompleteInput,
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[ReceivingService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    if_match: Annotated[str | None, Depends(get_if_match)],
    response: Response,
) -> PhieuNhapActionResponse:
    result, etag = await service.complete_receipt(id, if_match, actor, request_id)
    response.headers["ETag"] = etag
    return result


router = APIRouter()
router.include_router(contract_router)
router.include_router(legacy_router)
