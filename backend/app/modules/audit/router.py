from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.modules.audit.schemas import AuditLogResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response, get_pagination_params

router = APIRouter(prefix="/audit", tags=["Compliance & Audit Logs"])

SAMPLE_AUDIT_LOGS: List[AuditLogResponse] = [
    AuditLogResponse(
        id=1,
        user_id=1,
        user_email="admin@xbike.local",
        action="CREATE_WORK_ORDER",
        resource_type="WORK_ORDER",
        resource_id="WO-2026-0012",
        details="Authorized batch production of 25 Urban Commuter bikes",
        ip_address="192.168.1.50",
        timestamp=datetime.now(timezone.utc),
    ),
    AuditLogResponse(
        id=2,
        user_id=2,
        user_email="warehouse@xbike.local",
        action="POST_GOODS_RECEIPT",
        resource_type="GRN",
        resource_id="GRN-2026-0089",
        details="Received 50 units of 11-speed bicycle chains",
        ip_address="192.168.1.62",
        timestamp=datetime.now(timezone.utc),
    ),
]


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
async def list_audit_logs(
    params: PageParams = Depends(get_pagination_params),
    _=Depends(require_roles(["ADMIN", "AUDITOR"])),
):
    """Retrieve immutable audit trail records."""
    return create_paginated_response(
        items=SAMPLE_AUDIT_LOGS,
        total_items=len(SAMPLE_AUDIT_LOGS),
        page=params.page,
        page_size=params.page_size,
    )
