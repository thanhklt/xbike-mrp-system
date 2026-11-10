"""Read audit history and append entries in the caller's transaction."""

from app.modules.audit.ports import AuditRepository
from app.modules.audit.schemas import AuditLogResponse, CreationAudit, ThaoTac
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response

__all__ = ["AuditService", "CreationAudit"]


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def append(self, entry: CreationAudit) -> None:
        """Append in the caller's transaction; the caller owns commit/rollback."""
        await self.repository.append(entry)

    async def list_entries(
        self, params: PageParams, actor: dict, *, bo_thao_tac: ThaoTac | None = None
    ) -> PaginatedResponse[AuditLogResponse]:
        result = await self.repository.list_entries(
            params, AuditLogResponse, bo_thao_tac=bo_thao_tac
        )
        return create_paginated_response(result.items, result.total, params.page, params.page_size)
