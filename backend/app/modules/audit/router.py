"""Read the persisted database; no in-memory fixtures."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request
from fastapi.exceptions import RequestValidationError

from app.dependencies import (
    get_audit_service,
    get_current_user_payload,
    require_roles,
)
from app.modules.audit.schemas import (
    AuditDetailResponse,
    AuditErrorResponse,
    AuditInternalError,
    AuditListQuery,
    AuditLogResponse,
)
from app.modules.audit.service import AuditService
from app.shared.pagination import PaginatedResponse

AuditActor = Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))]
AuditApplication = Annotated[AuditService, Depends(get_audit_service)]

router = APIRouter(
    prefix="/audit",
    tags=["Audit"],
    dependencies=[Depends(get_current_user_payload)],
    responses={
        **{status: {"model": AuditErrorResponse} for status in (401, 403, 422)},
        500: {"model": AuditInternalError},
    },
)


def _reject_query_fields(request: Request, *, allow_fields: bool) -> None:
    errors = []
    for key in request.query_params:
        if not allow_fields or len(request.query_params.getlist(key)) != 1:
            errors.append(
                {
                    "type": "value_error",
                    "loc": ("query", key),
                    "msg": "Unexpected or repeated query parameter",
                    "input": None,
                }
            )
    if errors:
        raise RequestValidationError(errors)


def get_audit_query(request: Request, params: Annotated[AuditListQuery, Query()]) -> AuditListQuery:
    _reject_query_fields(request, allow_fields=True)
    return params


def reject_detail_query(request: Request) -> None:
    _reject_query_fields(request, allow_fields=False)


@router.get(
    "",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="UC-43: Xem danh sách lịch sử thao tác",
    description="UC-43 — specs/use_cases/audit/UC-43.md. QTV/QLK, chỉ đọc; filter kết hợp AND, ngày theo Asia/Ho_Chi_Minh. Giữ envelope danh sách legacy.",
)
async def list_entries(
    actor: AuditActor,
    params: Annotated[AuditListQuery, Depends(get_audit_query)],
    service: AuditApplication,
) -> PaginatedResponse[AuditLogResponse]:
    return await service.list_entries(params, actor)


@router.get(
    "/{id}",
    response_model=AuditDetailResponse,
    responses={404: {"model": AuditErrorResponse}},
    dependencies=[Depends(reject_detail_query)],
    summary="UC-43: Xem chi tiết lịch sử thao tác",
    description="UC-43 — specs/use_cases/audit/UC-43.md. Bằng chứng đã lưu, giữ null, loại bí mật; không sửa/xóa lịch sử và không cần If-Match.",
)
async def get_entry(
    id: Annotated[int, Path(gt=0)], actor: AuditActor, service: AuditApplication
) -> AuditDetailResponse:
    return await service.get_entry(id, actor)
