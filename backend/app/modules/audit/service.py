"""Read-only audit use case."""

from app.modules.audit.ports import AuditRepository
from app.modules.audit.schemas import AuditLogResponse
from app.shared.pagination import PageParams, PaginatedResponse, create_paginated_response


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def list_entries(self, params: PageParams) -> PaginatedResponse[AuditLogResponse]:
        result = await self.repository.list_entries(params)
        return create_paginated_response(result.items, result.total, params.page, params.page_size)
