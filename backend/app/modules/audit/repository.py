"""Read and append audit rows in the caller's transaction."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import select_page
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.schemas import AuditLogResponse, CreationAudit
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[AuditLogResponse]:
        return await select_page(self.session, AuditTrailLog, AuditLogResponse, params)

    async def append(self, entry: CreationAudit) -> None:
        # Missing snapshots are SQL NULL, not the JSONB literal null.
        self.session.add(AuditTrailLog(**entry.model_dump(exclude_none=True)))
