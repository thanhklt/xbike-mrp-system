"""Read the persisted database; no in-memory fixtures."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_payload, require_roles
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.schemas import AuditLogResponse
from app.shared.database_queries import list_records
from app.shared.pagination import PageParams, PaginatedResponse, get_pagination_params

router = APIRouter(
    prefix="/audit", tags=["Audit"], dependencies=[Depends(get_current_user_payload)]
)


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_0(
    params: Annotated[PageParams, Depends(get_pagination_params)],
    db: Annotated[AsyncSession, Depends(get_db)],
    actor: Annotated[dict, Depends(require_roles(["quan_tri_vien", "quan_ly"]))],
):
    return await list_records(db, AuditTrailLog, AuditLogResponse, params)
