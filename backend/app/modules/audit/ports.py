"""Separate read and append contracts for the audit trail."""

from typing import Protocol, TypeVar

from app.modules.audit.schemas import AuditLogResponse, CreationAudit, ThaoTac
from app.shared.pagination import PageParams
from app.shared.records import RecordPage

T = TypeVar("T", bound=AuditLogResponse)


class AuditRepository(Protocol):
    async def list_entries(
        self, params: PageParams, schema: type[T], *, bo_thao_tac: ThaoTac | None = None
    ) -> RecordPage[T]: ...

    async def append(self, entry: CreationAudit) -> None: ...


class AuditWriter(Protocol):
    async def append(self, entry: CreationAudit) -> None: ...
