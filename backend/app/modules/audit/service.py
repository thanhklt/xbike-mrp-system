"""Read audit history and append entries in the caller's transaction."""

from app.modules.audit.ports import AuditRepository
from app.modules.audit.schemas import AuditLogResponse, AuditLogSummary, CreationAudit
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response

__all__ = ["AuditService", "CreationAudit"]


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def append(self, entry: CreationAudit) -> None:
        """Append in the caller's transaction; the caller owns commit/rollback."""
        await self.repository.append(entry)

    async def list_entries(
        self, params: PageParams, actor: dict
    ) -> PaginatedResponse[AuditLogResponse] | PaginatedResponse[AuditLogSummary]:
        schema = AuditLogSummary if "quan_tri_vien" in actor["roles"] else AuditLogResponse
        if schema is AuditLogSummary and params.sort_by in {"du_lieu_truoc", "du_lieu_sau"}:
            params = params.model_copy(update={"sort_by": "created_at"})
        result = await self.repository.list_entries(params, schema)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)
