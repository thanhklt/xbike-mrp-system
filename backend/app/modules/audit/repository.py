"""Read and append audit rows in the caller's transaction."""

from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import select_page
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.schemas import AuditLogResponse, CreationAudit, ThaoTac
from app.shared.pagination import PageParams
from app.shared.records import RecordPage

T = TypeVar("T", bound=AuditLogResponse)


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(
        self, params: PageParams, schema: type[T], *, bo_thao_tac: ThaoTac | None = None
    ) -> RecordPage[T]:
        filters = () if bo_thao_tac is None else (LichSuThaoTac.thao_tac != bo_thao_tac,)
        return await select_page(self.session, LichSuThaoTac, schema, params, *filters)

    async def append(self, entry: CreationAudit) -> None:
        self.session.add(LichSuThaoTac(**entry.model_dump()))
