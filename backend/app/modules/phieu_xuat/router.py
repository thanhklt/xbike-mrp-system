"""Six v4 issue endpoints; specs/use_cases/goods_issue/README.md (UC-34..40)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError

from app.core.request_context import (
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
    PhieuXuatCuaToiListResponse,
    PhieuXuatCuaToiQuery,
    PhieuXuatErrorResponse,
    PhieuXuatListResponse,
    PhieuXuatPreviewQuery,
    PhieuXuatPreviewResponse,
    PhieuXuatQuery,
    PhieuXuatResponse,
    PhieuXuatSourceResponse,
)
from app.modules.phieu_xuat.service import PhieuXuatService


async def reject_get_body(request: Request) -> None:
    if await request.body():
        raise RequestValidationError(
            [{"loc": ("body",), "msg": "GET body is not allowed", "type": "extra_forbidden"}]
        )


def get_phieu_xuat_if_match(
    request: Request,
    if_match: Annotated[
        str | None,
        Header(description="One quoted SHA-256 ETag; required (428), invalid/repeated (412)"),
    ] = None,
) -> str | None:
    # Preserve every physical header for validation under the service's row lock.
    values = request.headers.getlist("if-match")
    return ",".join(values) if values else if_match


ReadActor = Annotated[dict, Depends(require_roles(["quan_ly", "nhan_vien"]))]
EmployeeActor = Annotated[dict, Depends(require_roles(["nhan_vien"]))]
WriteActor = Annotated[dict, Depends(require_roles(["quan_ly"]))]
Service = Annotated[PhieuXuatService, Depends(get_phieu_xuat_service)]
ResourceId = Annotated[int, Path(gt=0)]
RequestId = Annotated[str, Depends(get_request_id)]
IfMatch = Annotated[str | None, Depends(get_phieu_xuat_if_match)]
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


@router.get(
    "",
    response_model=PhieuXuatListResponse,
    description="UC-40; specs/use_cases/goods_issue/README.md",
    dependencies=[Depends(reject_repeated_query), Depends(reject_get_body)],
)
async def list_issues(
    params: Annotated[PhieuXuatQuery, Query()],
    actor: WriteActor,
    service: Service,
    request_id: RequestId,
):
    return await service.list_issues(params, actor, request_id)


@router.get(
    "/theo_yeu_cau/{id}",
    response_model=PhieuXuatSourceResponse,
    dependencies=[Depends(reject_query), Depends(reject_get_body)],
)
async def source_issues(id: ResourceId, actor: ReadActor, service: Service, request_id: RequestId):
    return await service.source_issues(id, actor, request_id)


@router.get(
    "/xem_truoc/{id}",
    response_model=PhieuXuatPreviewResponse,
    dependencies=[Depends(reject_repeated_query), Depends(reject_get_body)],
)
async def preview_issue(
    id: ResourceId,
    params: Annotated[PhieuXuatPreviewQuery, Query()],
    actor: EmployeeActor,
    service: Service,
    request_id: RequestId,
):
    return await service.preview(id, params.loai_phieu, actor, request_id)


@router.get(
    "/cua_toi",
    response_model=PhieuXuatCuaToiListResponse,
    description="Scoped issues for the current employee.",
    dependencies=[Depends(reject_repeated_query), Depends(reject_get_body)],
)
async def list_my_issues(
    params: Annotated[PhieuXuatCuaToiQuery, Query()],
    actor: EmployeeActor,
    service: Service,
    request_id: RequestId,
):
    return await service.list_my_issues(params, actor, request_id)


@router.get(
    "/{id}",
    response_model=PhieuXuatResponse,
    description="UC-40; specs/use_cases/goods_issue/README.md",
    dependencies=[Depends(reject_query), Depends(reject_get_body)],
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
    description="UC-34/37; specs/use_cases/goods_issue/README.md",
    dependencies=[Depends(reject_query)],
    responses={201: {"headers": {**ETAG, "Location": {"schema": {"type": "string"}}}}},
)
async def create_issue(
    payload: PhieuXuatCreate,
    actor: EmployeeActor,
    service: Service,
    request_id: RequestId,
    request: Request,
    response: Response,
):
    result, etag = await service.create_issue(payload, actor, request_id)
    response.headers["ETag"] = etag
    response.headers["Location"] = f"{request.url.path}/{result.data.id}"
    return result


@router.post(
    "/{id}/gui",
    description="UC-34/37; submit/resubmit; specs/use_cases/goods_issue/README.md",
    response_model=PhieuXuatResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": ETAG}},
)
async def submit_issue(
    id: ResourceId,
    payload: EmptyInput,
    actor: EmployeeActor,
    service: Service,
    if_match: IfMatch,
    request_id: RequestId,
    response: Response,
):
    result, etag = await service.submit_issue(id, actor, if_match, request_id)
    response.headers["ETag"] = etag
    return result


@router.post(
    "/{id}/duyet",
    description="UC-35/38; specs/use_cases/goods_issue/README.md",
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
    description="UC-36/39; specs/use_cases/goods_issue/README.md",
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
    result, etag = await service.reject_issue(id, actor, if_match, request_id, payload.ly_do)
    response.headers["ETag"] = etag
    return result
