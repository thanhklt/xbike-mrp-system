"""Separate read and append contracts for the audit trail."""

from datetime import datetime
from typing import Protocol

from app.modules.audit.schemas import AuditListQuery, AuditRecord, CreationAudit
from app.shared.records import RecordPage


class AuditRepository(Protocol):
    async def list_entries(
        self,
        params: AuditListQuery,
        *,
        created_from: datetime | None,
        created_before: datetime | None,
    ) -> RecordPage[AuditRecord]: ...

    async def get_entry(self, entry_id: int) -> AuditRecord | None: ...

    async def append(self, entry: CreationAudit) -> None: ...


class AuditWriter(Protocol):
    async def append(self, entry: CreationAudit) -> None: ...
