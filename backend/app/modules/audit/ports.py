"""Separate read and append contracts for the audit trail."""

from typing import Protocol

from app.modules.audit.schemas import AuditLogResponse, CreationAudit
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class AuditRepository(Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[AuditLogResponse]: ...


class AuditWriter(Protocol):
    async def append(self, entry: CreationAudit) -> None: ...
