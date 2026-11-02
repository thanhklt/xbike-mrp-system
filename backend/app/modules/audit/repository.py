"""Read and append audit rows in the caller's transaction."""

from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import select_page
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.schemas import AuditLogSummary, CreationAudit
from app.shared.pagination import PageParams
from app.shared.records import RecordPage

T = TypeVar("T", bound=AuditLogSummary)


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams, schema: type[T]) -> RecordPage[T]:
        return await select_page(self.session, LichSuThaoTac, schema, params)

    async def append(self, entry: CreationAudit) -> None:
        self.session.add(LichSuThaoTac(**entry.model_dump()))
