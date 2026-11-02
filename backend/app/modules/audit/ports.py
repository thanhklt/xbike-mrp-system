"""Separate read and append contracts for the audit trail."""

from typing import Protocol, TypeVar

from app.modules.audit.schemas import AuditLogSummary, CreationAudit
from app.shared.pagination import PageParams
from app.shared.records import RecordPage

T = TypeVar("T", bound=AuditLogSummary)


class AuditRepository(Protocol):
    async def list_entries(self, params: PageParams, schema: type[T]) -> RecordPage[T]: ...

    async def append(self, entry: CreationAudit) -> None: ...


class AuditWriter(Protocol):
    async def append(self, entry: CreationAudit) -> None: ...
