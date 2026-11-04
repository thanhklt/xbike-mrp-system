"""Manager-only adjustment and ticket endpoints from contract v3 section 12."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.core.request_context import (
    get_if_match,
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import (
    get_phieu_dieu_chinh_kho_service,
    get_ticket_dieu_chinh_service,
    require_roles,
)
from app.modules.dieu_chinh_kho.schemas import (
    EmptyInput,
    ErrorResponse,
    PhieuDieuChinhActionResponse,
    PhieuDieuChinhCreate,
    PhieuDieuChinhListResponse,
    PhieuDieuChinhPatch,
    PhieuDieuChinhQuery,
    PhieuDieuChinhResponse,
    TicketClaimInput,
    TicketErrorResponse,
    TicketListQuery,
    TicketListResponse,
    TicketResolveInput,
    TicketResponse,
)
from app.modules.dieu_chinh_kho.service import PhieuDieuChinhKhoService, TicketDieuChinhService

Manager = Annotated[dict, Depends(require_roles(["quan_ly"]))]
Service = Annotated[TicketDieuChinhService, Depends(get_ticket_dieu_chinh_service)]
TicketId = Annotated[int, Path(gt=0)]
RequestId = Annotated[str, Depends(get_request_id)]
IfMatch = Annotated[str | None, Depends(get_if_match)]
ETAG = {
    "ETag": {
        "schema": {"type": "string"},
        "description": "Strong ETag including resource state and detail lines",
    }
}
ticket_router = APIRouter(
    prefix="/ticket_loi_dieu_chinh",
    tags=["dieu_chinh_kho"],
    responses={code: {"model": TicketErrorResponse} for code in (401, 403, 422, 500)},
)
action_responses = {
    **{code: {"model": TicketErrorResponse} for code in (404, 409, 412, 428)},
    200: {"headers": ETAG},
}


@ticket_router.get(
    "", response_model=TicketListResponse, dependencies=[Depends(reject_repeated_query)]
)
async def list_tickets(
    params: Annotated[TicketListQuery, Query()],
    actor: Manager,
    service: Service,
    request_id: RequestId,
) -> TicketListResponse:
    return await service.list_tickets(params, actor, request_id)


@ticket_router.get(
    "/{id}",
    response_model=TicketResponse,
    dependencies=[Depends(reject_query)],
    responses={404: {"model": TicketErrorResponse}, 200: {"headers": ETAG}},
)
async def get_ticket(
    id: TicketId, actor: Manager, service: Service, request_id: RequestId, response: Response
) -> TicketResponse:
    result, etag = await service.get_ticket(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


PhieuService = Annotated[PhieuDieuChinhKhoService, Depends(get_phieu_dieu_chinh_kho_service)]
router = APIRouter(
    prefix="/phieu_dieu_chinh_kho",
    tags=["dieu_chinh_kho"],
    responses={code: {"model": ErrorResponse} for code in (401, 403, 422, 500)},
)


phieu_action_responses = {
    **{code: {"model": ErrorResponse} for code in (404, 409, 412, 428)},
    200: {"headers": ETAG},
}


@router.get(
    "", response_model=PhieuDieuChinhListResponse, dependencies=[Depends(reject_repeated_query)]
)
async def list_phieu(
    params: Annotated[PhieuDieuChinhQuery, Query()],
    actor: Manager,
    service: PhieuService,
    request_id: RequestId,
) -> PhieuDieuChinhListResponse:
    return await service.list_phieu(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=PhieuDieuChinhResponse,
    dependencies=[Depends(reject_query)],
    responses={404: {"model": ErrorResponse}, 200: {"headers": ETAG}},
)
async def get_phieu(
    id: TicketId, actor: Manager, service: PhieuService, request_id: RequestId, response: Response
) -> PhieuDieuChinhResponse:
    result, response.headers["ETag"] = await service.get_phieu(id, actor, request_id)
    return result


@router.post(
    "",
    status_code=201,
    response_model=PhieuDieuChinhResponse,
    dependencies=[Depends(reject_query)],
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        201: {"headers": {**ETAG, "Location": {"schema": {"type": "string"}}}},
    },
)
async def create_phieu(
    payload: PhieuDieuChinhCreate,
    actor: Manager,
    service: PhieuService,
    request_id: RequestId,
    response: Response,
    request: Request,
) -> PhieuDieuChinhResponse:
    result, response.headers["ETag"] = await service.create(payload, actor, request_id)
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.patch(
    "/{id}",
    response_model=PhieuDieuChinhResponse,
    dependencies=[Depends(reject_query)],
    responses=phieu_action_responses,
)
async def patch_phieu(
    id: TicketId,
    payload: PhieuDieuChinhPatch,
    actor: Manager,
    service: PhieuService,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
) -> PhieuDieuChinhResponse:
    result, response.headers["ETag"] = await service.patch(id, payload, actor, if_match, request_id)
    return result


@router.delete(
    "/{id}",
    status_code=204,
    dependencies=[Depends(reject_query)],
    responses={code: {"model": ErrorResponse} for code in (404, 409, 412, 428)},
)
async def delete_phieu(
    id: TicketId, actor: Manager, service: PhieuService, if_match: IfMatch
) -> Response:
    await service.delete(id, actor, if_match)
    return Response(status_code=204)


@router.post(
    "/{id}/xac_nhan",
    response_model=PhieuDieuChinhActionResponse,
    dependencies=[Depends(reject_query)],
    responses=phieu_action_responses,
)
async def confirm_phieu(
    id: TicketId,
    payload: EmptyInput,
    actor: Manager,
    service: PhieuService,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
) -> PhieuDieuChinhActionResponse:
    result, response.headers["ETag"] = await service.xac_nhan(id, actor, if_match, request_id)
    return result


@ticket_router.post(
    "/{id}/nhan_xu_ly",
    response_model=TicketResponse,
    dependencies=[Depends(reject_query)],
    responses=action_responses,
)
async def claim_ticket(
    id: TicketId,
    payload: TicketClaimInput,
    actor: Manager,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
) -> TicketResponse:
    result, etag = await service.claim_ticket(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@ticket_router.post(
    "/{id}/giai_quyet",
    response_model=TicketResponse,
    dependencies=[Depends(reject_query)],
    responses=action_responses,
)
async def resolve_ticket(
    id: TicketId,
    payload: TicketResolveInput,
    actor: Manager,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
) -> TicketResponse:
    result, etag = await service.resolve_ticket(
        id, payload.ket_qua_xu_ly, actor, if_match, request_id
    )
    response.headers["ETag"] = etag
    return result
