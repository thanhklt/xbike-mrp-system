"""BOM endpoints: immutable formulas and explicit activation of versions."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response

from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_bom_service, require_roles
from app.modules.bom.schemas import (
    BomCreate,
    BomDetailResponse,
    BomErrorResponse,
    BomListQuery,
    BomListResponse,
    BomTreeResponse,
    KichHoatBomInput,
)
from app.modules.bom.service import BomService

read_actor = require_roles(["quan_ly", "nhan_vien"])
write_actor = require_roles(["quan_ly"])
_empty_activation = KichHoatBomInput()
router = APIRouter(
    prefix="/bom",
    tags=["BOM"],
    responses={code: {"model": BomErrorResponse} for code in (401, 403, 422, 500)},
)


@router.get("", response_model=BomListResponse, dependencies=[Depends(read_actor)])
async def list_bom(
    params: Annotated[BomListQuery, Query()],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomListResponse:
    return await service.list_bom(params, request_id)


@router.get(
    "/{id}",
    response_model=BomDetailResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
    responses={404: {"model": BomErrorResponse}},
)
async def get_bom(
    id: Annotated[int, Path(gt=0)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomDetailResponse:
    return await service.get_bom(id, request_id)


@router.get(
    "/{id}/cau_truc",
    response_model=BomTreeResponse,
    dependencies=[Depends(read_actor), Depends(reject_query)],
    responses={404: {"model": BomErrorResponse}, 409: {"model": BomErrorResponse}},
)
async def get_cau_truc(
    id: Annotated[int, Path(gt=0)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> BomTreeResponse:
    return await service.get_cau_truc(id, request_id)


@router.post(
    "",
    status_code=201,
    response_model=BomDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={
        201: {"headers": {"Location": {"schema": {"type": "string"}}}},
        404: {"model": BomErrorResponse},
        409: {"model": BomErrorResponse},
    },
)
async def create_bom(
    payload: BomCreate,
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
    request: Request,
) -> BomDetailResponse:
    result = await service.create_bom(payload, actor, request_id)
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.delete(
    "/{id}",
    status_code=204,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={404: {"model": BomErrorResponse}},
)
async def delete_bom(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
) -> Response:
    await service.delete_bom(id, actor)
    return Response(status_code=204)


@router.post(
    "/{id}/kich_hoat",
    response_model=BomDetailResponse,
    dependencies=[Depends(write_actor), Depends(reject_query)],
    responses={404: {"model": BomErrorResponse}, 409: {"model": BomErrorResponse}},
)
async def activate_bom(
    id: Annotated[int, Path(gt=0)],
    actor: Annotated[dict, Depends(write_actor)],
    service: Annotated[BomService, Depends(get_bom_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    payload: Annotated[KichHoatBomInput, Body()] = _empty_activation,
) -> BomDetailResponse:
    return await service.activate_bom(id, actor, request_id)
