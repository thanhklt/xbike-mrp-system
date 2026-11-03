"""Audit persistence contract and write-only contract for audit clients."""

from typing import Protocol

from app.modules.audit.schemas import AuditLogResponse, CreationAudit
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class AuditWriter(Protocol):
    async def append(self, entry: CreationAudit) -> None: ...


class AuditRepository(AuditWriter, Protocol):
    async def list_entries(self, params: PageParams) -> RecordPage[AuditLogResponse]: ...
