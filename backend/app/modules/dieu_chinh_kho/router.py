"""Nine correction endpoints, restricted to managers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_audit_service, require_roles
from app.modules.audit.service import AuditService
from app.modules.dieu_chinh_kho.errors import DieuChinhError
from app.modules.dieu_chinh_kho.incidents import DieuChinhIncidents
from app.modules.dieu_chinh_kho.repository import SqlAlchemyDieuChinhRepository
from app.modules.dieu_chinh_kho.schemas import (
    DieuChinhCreate,
    DieuChinhListResponse,
    DieuChinhPatch,
    DieuChinhQuery,
    DieuChinhResponse,
    EmptyInput,
    LyDoInput,
)
from app.modules.dieu_chinh_kho.service import DieuChinhService, etag


def get_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> DieuChinhService:
    return DieuChinhService(SqlAlchemyDieuChinhRepository(db), audit, DieuChinhIncidents())


Service = Annotated[DieuChinhService, Depends(get_service)]
Actor = Annotated[dict, Depends(require_roles(["quan_ly"]))]
Id = Annotated[int, Path(gt=0, le=2147483647)]
Token = Annotated[str | None, Header(alias="If-Match")]


class DieuChinhRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def handle(request: Request):
            try:
                return await handler(request)
            except SQLAlchemyError:
                return await handle_error(
                    request,
                    DieuChinhError(
                        503,
                        "dich_vu_tam_thoi_khong_kha_dung",
                        "Cơ sở dữ liệu tạm thời không khả dụng",
                        ticket_id=None,
                        ticket_da_luu=False,
                    ),
                )

        return handle


router = APIRouter(
    prefix="/phieu_dieu_chinh_kho", tags=["Điều chỉnh kho"], route_class=DieuChinhRoute
)


async def handle_error(request: Request, error: DieuChinhError):
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {"code": error.code, "message": error.message, "details": [], **error.extra},
            "meta": {"request_id": get_request_id(request)},
        },
        headers={"Cache-Control": "no-store"},
    )


def detail(record, request, response, **extra):
    response.headers["ETag"] = etag(record)
    return {"data": record, "meta": {"request_id": get_request_id(request)}, **extra}


@router.get("", response_model=DieuChinhListResponse)
async def list_phieu(
    query: Annotated[DieuChinhQuery, Query()], service: Service, actor: Actor, request: Request
):
    records, total = await service.repo.list(query)
    return {
        "data": records,
        "meta": {
            "request_id": get_request_id(request),
            "page": query.page,
            "page_size": query.page_size,
            "total": total,
            "total_pages": (total + query.page_size - 1) // query.page_size,
        },
    }


@router.get(
    "/{id}",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def get_phieu(id: Id, service: Service, actor: Actor, request: Request, response: Response):
    return detail(await service.get(id), request, response)


@router.post(
    "",
    status_code=201,
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def create_phieu(
    payload: DieuChinhCreate, service: Service, actor: Actor, request: Request, response: Response
):
    record = await service.create(payload, actor)
    response.headers["Location"] = f"/api/v1/phieu_dieu_chinh_kho/{record['id']}"
    return detail(record, request, response)


@router.patch(
    "/{id}",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def patch_phieu(
    id: Id,
    payload: DieuChinhPatch,
    service: Service,
    actor: Actor,
    request: Request,
    response: Response,
    if_match: Token = None,
):
    return detail(await service.mutate(id, "sua", payload, if_match, actor), request, response)


@router.delete("/{id}", status_code=204, dependencies=[Depends(reject_query)])
async def delete_phieu(id: Id, service: Service, actor: Actor, if_match: Token = None):
    await service.mutate(id, "xoa_nhap", None, if_match, actor)
    return Response(status_code=204)


@router.post(
    "/{id}/gui",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def gui_phieu(
    id: Id,
    payload: EmptyInput,
    service: Service,
    actor: Actor,
    request: Request,
    response: Response,
    if_match: Token = None,
):
    return detail(await service.mutate(id, "gui", payload, if_match, actor), request, response)


@router.post(
    "/{id}/duyet",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def duyet_phieu(
    id: Id,
    payload: EmptyInput,
    service: Service,
    actor: Actor,
    request: Request,
    response: Response,
    if_match: Token = None,
):
    record, ids, previous = await service.approve(id, if_match, actor)
    return detail(record, request, response, giao_dich_kho_ids=ids, da_ghi_so_truoc_do=previous)


@router.post(
    "/{id}/tu_choi",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def tu_choi_phieu(
    id: Id,
    payload: LyDoInput,
    service: Service,
    actor: Actor,
    request: Request,
    response: Response,
    if_match: Token = None,
):
    return detail(await service.mutate(id, "tu_choi", payload, if_match, actor), request, response)


@router.post(
    "/{id}/ve_nhap",
    response_model=DieuChinhResponse,
    response_model_exclude_unset=True,
    dependencies=[Depends(reject_query)],
)
async def ve_nhap_phieu(
    id: Id,
    payload: LyDoInput,
    service: Service,
    actor: Actor,
    request: Request,
    response: Response,
    if_match: Token = None,
):
    return detail(await service.mutate(id, "ve_nhap", payload, if_match, actor), request, response)
