"""Six receipt endpoints under the shared /phieu_nhap router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import (
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import (
    get_receiving_service,
    require_roles,
)
from app.modules.phieu_nhap.schemas import (
    PhieuNhapActionResponse,
    PhieuNhapCompleteInput,
    PhieuNhapCreate,
    PhieuNhapDetailResponse,
    PhieuNhapErrorResponse,
    PhieuNhapListQuery,
    PhieuNhapListResponse,
    PhieuNhapPatch,
)
from app.modules.phieu_nhap.service import PhieuNhapService


async def reject_body(request: Request) -> None:
    if await request.body():
        raise RequestValidationError(
            [{"loc": ("body",), "msg": "Body is not allowed", "type": "extra_forbidden"}]
        )


def get_phieu_nhap_if_match(
    request: Request,
    if_match: Annotated[
        str | None,
        Header(description="One quoted SHA-256 ETag; required (428), invalid/repeated (412)"),
    ] = None,
) -> str | None:
    # Preserve physical duplicates for validation under the service's transaction lock.
    values = request.headers.getlist("if-match")
    return ",".join(values) if values else if_match


receipt_actor = require_roles(["quan_ly"])
router = APIRouter(
    prefix="/phieu_nhap",
    tags=["phieu_nhap"],
    dependencies=[Depends(receipt_actor)],
    responses={code: {"model": PhieuNhapErrorResponse} for code in (401, 403, 422, 500)},
)
detail_headers = {
    "ETag": {"schema": {"type": "string"}, "description": "Strong ETag including receipt items"}
}


@router.get(
    "",
    response_model=PhieuNhapListResponse,
    description="UC-22; specs/use_cases/goods_receipt/README.md",
    dependencies=[Depends(reject_repeated_query), Depends(reject_body)],
)
async def list_receipts(
    actor: Annotated[dict, Depends(receipt_actor)],
    params: Annotated[PhieuNhapListQuery, Query()],
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> PhieuNhapListResponse:
    return await service.list_receipts(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=PhieuNhapDetailResponse,
    description="UC-22; specs/use_cases/goods_receipt/README.md",
    dependencies=[Depends(reject_query), Depends(reject_body)],
    responses={200: {"headers": detail_headers}, 404: {"model": PhieuNhapErrorResponse}},
)
async def get_receipt(
    actor: Annotated[dict, Depends(receipt_actor)],
    id: Annotated[int, Path(gt=0)],
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.get_receipt(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "",
    status_code=201,
    description="UC-20; specs/use_cases/goods_receipt/README.md",
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
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    request: Request,
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.create_receipt(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


mutation_errors: dict[int | str, dict[str, Any]] = {
    code: {"model": PhieuNhapErrorResponse} for code in (404, 409, 412, 428)
}


@router.patch(
    "/{id}",
    description="UC-20; specs/use_cases/goods_receipt/README.md",
    response_model=PhieuNhapDetailResponse,
    dependencies=[Depends(reject_query)],
    responses={**mutation_errors, 200: {"headers": detail_headers}},
)
async def patch_receipt(
    id: Annotated[int, Path(gt=0)],
    payload: PhieuNhapPatch,
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    if_match: Annotated[str | None, Depends(get_phieu_nhap_if_match)],
    response: Response,
) -> PhieuNhapDetailResponse:
    result, etag = await service.patch_receipt(id, payload, if_match, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.delete(
    "/{id}",
    status_code=204,
    description="UC-20; specs/use_cases/goods_receipt/README.md",
    response_class=Response,
    dependencies=[Depends(reject_query), Depends(reject_body)],
    responses=mutation_errors,
)
async def delete_receipt(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    if_match: Annotated[str | None, Depends(get_phieu_nhap_if_match)],
) -> Response:
    await service.delete_receipt(id, if_match, actor)
    return Response(status_code=204)


@router.post(
    "/{id}/hoan_tat",
    description="UC-21; specs/use_cases/goods_receipt/README.md",
    response_model=PhieuNhapActionResponse,
    dependencies=[Depends(reject_query)],
    responses={**mutation_errors, 200: {"headers": detail_headers}},
)
async def complete_receipt(
    id: Annotated[int, Path(gt=0)],
    payload: PhieuNhapCompleteInput,
    actor: Annotated[dict, Depends(receipt_actor)],
    service: Annotated[PhieuNhapService, Depends(get_receiving_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    if_match: Annotated[str | None, Depends(get_phieu_nhap_if_match)],
    response: Response,
) -> PhieuNhapActionResponse:
    result, etag = await service.complete_receipt(id, if_match, actor, request_id)
    response.headers["ETag"] = etag
    return result
