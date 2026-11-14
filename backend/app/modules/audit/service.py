"""Read audit history and append entries in the caller's transaction."""

from dataclasses import fields
from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.core.errors import ForbiddenException, NotFoundException
from app.modules.audit.ports import AuditRepository
from app.modules.audit.schemas import (
    MAX_AUDIT_ID,
    AuditDetailResponse,
    AuditListQuery,
    AuditLogResponse,
    AuditRecord,
    CreationAudit,
)
from app.shared.pagination import PaginatedResponse, create_paginated_response

__all__ = ["AuditService", "CreationAudit"]

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
SECRET_KEYS = frozenset(
    "password matkhau hash passwordhash matkhauhash oldpassword newpassword currentpassword "
    "matkhaucu matkhaumoi token accesstoken refreshtoken idtoken authorization cookie "
    "secret secretkey credentialversion pwdv".split()
)


def _require_reader(actor: dict) -> None:
    roles = actor.get("roles")
    if not isinstance(roles, (list, tuple, set, frozenset)) or not {
        "quan_tri_vien",
        "quan_ly",
    }.intersection(roles):
        raise ForbiddenException(message="Only administrators and managers may read audit history")


def _without_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_secrets(item)
            for key, item in value.items()
            if key.lower().replace("_", "").replace("-", "") not in SECRET_KEYS
        }
    if isinstance(value, list):
        return [_without_secrets(item) for item in value]
    return value


def _public_record(record: AuditRecord) -> AuditLogResponse:
    values = {field.name: getattr(record, field.name) for field in fields(record)}
    values["du_lieu_truoc"] = _without_secrets(record.du_lieu_truoc)
    values["du_lieu_sau"] = _without_secrets(record.du_lieu_sau)
    return AuditLogResponse.model_validate(values)


class AuditService:
    """UC-43 reads: specs/use_cases/audit/UC-43.md; append belongs to the source UC."""

    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def append(self, entry: CreationAudit) -> None:
        """Append in the caller's transaction; the caller owns commit/rollback."""
        await self.repository.append(entry)

    async def list_entries(
        self, params: AuditListQuery, actor: dict
    ) -> PaginatedResponse[AuditLogResponse]:
        """UC-43 / AC-07..12,15,17: authorized, filtered, read-only history."""
        _require_reader(actor)
        created_from = (
            datetime.combine(params.tu_ngay, time.min, LOCAL_TZ).astimezone(timezone.utc)
            if params.tu_ngay is not None
            else None
        )
        created_before = (
            datetime.combine(params.den_ngay + timedelta(days=1), time.min, LOCAL_TZ).astimezone(
                timezone.utc
            )
            if params.den_ngay is not None
            else None
        )
        result = await self.repository.list_entries(
            params, created_from=created_from, created_before=created_before
        )
        return create_paginated_response(
            [_public_record(record) for record in result.items],
            result.total,
            params.page,
            params.page_size,
        )

    async def get_entry(self, entry_id: int, actor: dict) -> AuditDetailResponse:
        """UC-43 / AC-1,4,5,07,08,13..15,17: immutable evidence by ID."""
        _require_reader(actor)
        if not 1 <= entry_id <= MAX_AUDIT_ID:
            raise NotFoundException()
        record = await self.repository.get_entry(entry_id)
        if record is None:
            raise NotFoundException()
        return AuditDetailResponse(data=_public_record(record))
