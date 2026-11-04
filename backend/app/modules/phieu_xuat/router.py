"""Nine issue endpoints from API contract v3 section 10."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.core.request_context import (
    get_if_match,
    get_request_id,
    reject_query,
    reject_repeated_query,
)
from app.dependencies import get_phieu_xuat_service, require_roles
from app.modules.phieu_xuat.schemas import (
    EmptyInput,
    LyDoInput,
    PhieuXuatActionResponse,
    PhieuXuatCreate,
    PhieuXuatErrorResponse,
    PhieuXuatListResponse,
    PhieuXuatPatch,
    PhieuXuatQuery,
    PhieuXuatResponse,
)
from app.modules.phieu_xuat.service import PhieuXuatService

ReadActor = Annotated[dict, Depends(require_roles(["quan_ly", "nhan_vien"]))]
WriteActor = Annotated[dict, Depends(require_roles(["quan_ly"]))]
Service = Annotated[PhieuXuatService, Depends(get_phieu_xuat_service)]
ResourceId = Annotated[int, Path(gt=0)]
RequestId = Annotated[str, Depends(get_request_id)]
IfMatch = Annotated[str | None, Depends(get_if_match)]
ETAG = {
    "ETag": {"schema": {"type": "string"}, "description": "Strong ETag of the issue and its lines"}
}
router = APIRouter(
    prefix="/phieu_xuat",
    tags=["phieu_xuat"],
    responses={
        code: {"model": PhieuXuatErrorResponse} for code in (401, 403, 404, 409, 412, 422, 428, 500)
    },
)


@router.get("", response_model=PhieuXuatListResponse, dependencies=[Depends(reject_repeated_query)])
async def list_issues(
    params: Annotated[PhieuXuatQuery, Query()],
    actor: ReadActor,
    service: Service,
    request_id: RequestId,
):
    return await service.list_issues(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def get_issue(
    id: ResourceId, actor: ReadActor, service: Service, request_id: RequestId, response: Response
):
    result, etag = await service.get_issue(id, actor, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "",
    response_model=PhieuXuatResponse,
    status_code=201,
    dependencies=[Depends(reject_query)],
    responses={201: {"headers": {**ETAG, "Location": {"schema": {"type": "string"}}}}},
)
async def create_issue(
    payload: PhieuXuatCreate,
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
    request: Request,
    response: Response,
):
    result, etag = await service.create_issue(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.patch(
    "/{id}",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def patch_issue(
    id: ResourceId,
    payload: PhieuXuatPatch,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.patch_issue(id, payload, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.delete("/{id}", status_code=204, dependencies=[Depends(reject_query)])
async def delete_issue(
    id: ResourceId, actor: WriteActor, service: Service, if_match: IfMatch
) -> Response:
    await service.delete_issue(id, actor, if_match)
    return Response(status_code=204)


@router.post(
    "/{id}/gui",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def submit_issue(
    id: ResourceId,
    payload: EmptyInput,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.transition(id, "gui", actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/duyet",
    response_model=PhieuXuatActionResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def approve_issue(
    id: ResourceId,
    payload: EmptyInput,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.approve(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/tu_choi",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def reject_issue(
    id: ResourceId,
    payload: LyDoInput,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.transition(
        id, "tu_choi", actor, if_match, request_id, payload.ly_do
    )
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/ve_nhap",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def revert_issue(
    id: ResourceId,
    payload: LyDoInput,
    actor: WriteActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.transition(
        id, "ve_nhap", actor, if_match, request_id, payload.ly_do
    )
    response.headers["ETag"] = etag
    return result
