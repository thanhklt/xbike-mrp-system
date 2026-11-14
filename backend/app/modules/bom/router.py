"""BOM endpoints: immutable formulas and explicit activation of versions."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Header, Path, Query, Request, Response

from app.core.errors import InvalidInputException
from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_bom_service, require_roles
from app.modules.bom.schemas import (
    BomDetailResponse,
    BomErrorResponse,
    BomFormula,
    BomListQuery,
    BomListResponse,
    BomTreeResponse,
    KichHoatBomInput,
)
from app.modules.bom.service import BomService

read_actor = require_roles(["quan_ly", "nhan_vien"])
write_actor = require_roles(["quan_ly"])


async def reject_body(request: Request) -> None:
    if await request.body():
        raise InvalidInputException(message="Endpoint không nhận request body")


router = APIRouter(
    prefix="/bom",
    tags=["BOM"],
    responses={code: {"model": BomErrorResponse} for code in (401, 403, 409, 412, 422, 428, 500)},
)


@router.get(
    "",
    response_model=BomListResponse,
    dependencies=[Depends(read_actor), Depends(reject_body)],
    description="UC-15 — specs/use_cases/bom/UC-15.md: xem phiên bản, lọc và phân trang.",
)
async def list_bom(
    params: Annotated[BomListQuery, Query()],
    actor: Annotated[dict, Depends(read_actor)],
    request: Request,
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomListResponse:
    if len(request.query_params.multi_items()) != len(set(request.query_params.keys())):
        raise InvalidInputException(message="Duplicate query parameter")
    return await service.list_bom(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=BomDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query), Depends(reject_body)],
    description="UC-15 — specs/use_cases/bom/UC-15.md; strong ETag dùng cho đúng ID này.",
    responses={
        200: {"headers": {"ETag": {"schema": {"type": "string"}}}},
        404: {"model": BomErrorResponse},
    },
)
async def get_bom(
    actor: Annotated[dict, Depends(read_actor)],
    response: Response,
    id: Annotated[int, Path(gt=0)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomDetailResponse:
    result, etag = await service.get_bom(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.get(
    "/{id}/cau_truc",
    response_model=BomTreeResponse,
    dependencies=[Depends(read_actor), Depends(reject_query), Depends(reject_body)],
    description="UC-15 — specs/use_cases/bom/UC-15.md; cây một cấp của version đã chọn.",
    responses={404: {"model": BomErrorResponse}, 409: {"model": BomErrorResponse}},
)
async def get_cau_truc(
    actor: Annotated[dict, Depends(read_actor)],
    id: Annotated[int, Path(gt=0)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomTreeResponse:
    return await service.get_cau_truc(id, actor, request_id)


@router.post(
    "/{id}/phien_ban",
    description="UC-17 — specs/use_cases/bom/UC-17.md; tạo version mới, If-Match từ GET cùng ID.",
    status_code=201,
    response_model=BomDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        201: {
            "headers": {
                "Location": {"schema": {"type": "string"}},
                "ETag": {"schema": {"type": "string"}},
            }
        },
        404: {"model": BomErrorResponse},
        409: {"model": BomErrorResponse},
    },
)
async def create_version(
    id: Annotated[int, Path(gt=0)],
    payload: BomFormula,
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> BomDetailResponse:
    result, etag = await service.create_version(id, payload, actor, if_match, request_id)
    response.headers["Location"] = f"/api/v1/bom/{result.data.id}"
    response.headers["ETag"] = etag
    return result


@router.delete(
    "/{id}",
    status_code=204,
    dependencies=[Depends(write_actor), Depends(reject_query), Depends(reject_body)],
    description="UC-19 — specs/use_cases/bom/UC-19.md; ngừng công thức/thành phẩm, không xóa cứng.",
    responses={404: {"model": BomErrorResponse}},
)
async def delete_bom(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> Response:
    await service.delete_bom(id, actor, if_match)
    return Response(status_code=204)


@router.post(
    "/{id}/kich_hoat",
    description="UC-18 — specs/use_cases/bom/UC-18.md; dùng lại version và thành phẩm cùng transaction.",
    response_model=BomDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={404: {"model": BomErrorResponse}, 409: {"model": BomErrorResponse}},
)
async def activate_bom(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    payload: Annotated[KichHoatBomInput, Body()],
    response: Response,
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> BomDetailResponse:
    result, etag = await service.activate_bom(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result
