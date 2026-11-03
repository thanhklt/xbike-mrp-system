"""Four manager-only ticket endpoints from contract v3 section 12.2."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.core.request_context import (
    get_if_match,
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import get_ticket_dieu_chinh_service, require_roles
from app.modules.ticket_dieu_chinh.schemas import (
    TicketClaimInput,
    TicketErrorResponse,
    TicketListQuery,
    TicketListResponse,
    TicketResolveInput,
    TicketResponse,
)
from app.modules.ticket_dieu_chinh.service import TicketDieuChinhService

Manager = Annotated[dict, Depends(require_roles(["quan_ly"]))]
Service = Annotated[TicketDieuChinhService, Depends(get_ticket_dieu_chinh_service)]
TicketId = Annotated[int, Path(gt=0)]
RequestId = Annotated[str, Depends(get_request_id)]
IfMatch = Annotated[str | None, Depends(get_if_match)]
ETAG = {
    "ETag": {
        "schema": {"type": "string"},
        "description": "Strong ETag including immutable ticket details",
    }
}
router = APIRouter(
    prefix="/ticket_loi_dieu_chinh",
    tags=["ticket_dieu_chinh"],
    responses={code: {"model": TicketErrorResponse} for code in (401, 403, 422, 500)},
)
action_responses = {
    **{code: {"model": TicketErrorResponse} for code in (404, 409, 412, 428)},
    200: {"headers": ETAG},
}


@router.get("", response_model=TicketListResponse, dependencies=[Depends(reject_repeated_query)])
async def list_tickets(
    params: Annotated[TicketListQuery, Query()],
    actor: Manager,
    service: Service,
    request_id: RequestId,
) -> TicketListResponse:
    return await service.list_tickets(params, actor, request_id)


@router.get(
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


@router.post(
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


@router.post(
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
