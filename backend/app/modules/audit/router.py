"""Read the persisted database; no in-memory fixtures."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import (
    get_audit_service,
    get_current_user_payload,
    get_pagination_params,
    require_roles,
)
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService
from app.shared.pagination import PageParams, PaginatedResponse

router = APIRouter(
    prefix="/audit", tags=["Audit"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_0(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    service: Annotated[AuditService, Depends(get_audit_service)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await service.list_entries(params)
