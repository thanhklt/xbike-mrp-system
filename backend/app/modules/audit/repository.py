"""Read and append audit rows in the caller's transaction."""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.schemas import AuditListQuery, AuditRecord, CreationAudit
from app.shared.records import RecordPage


def _record(row: LichSuThaoTac) -> AuditRecord:
    return AuditRecord(**{name: getattr(row, name) for name in AuditRecord.__dataclass_fields__})


class SqlAlchemyAuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(
        self,
        params: AuditListQuery,
        *,
        created_from: datetime | None,
        created_before: datetime | None,
    ) -> RecordPage[AuditRecord]:
        query = select(LichSuThaoTac)
        for name in ("nhan_vien_id", "loai_doi_tuong", "doi_tuong_id", "thao_tac"):
            value = getattr(params, name)
            if value is not None:
                query = query.where(getattr(LichSuThaoTac, name) == value)
        if params.bo_thao_tac is not None:
            query = query.where(LichSuThaoTac.thao_tac != params.bo_thao_tac)
        if params.search is not None:
            query = query.where(
                or_(
                    *(
                        column.icontains(params.search, autoescape=True)
                        for column in (
                            LichSuThaoTac.loai_doi_tuong,
                            LichSuThaoTac.thao_tac,
                            LichSuThaoTac.ly_do,
                        )
                    )
                )
            )
        if created_from is not None:
            query = query.where(LichSuThaoTac.created_at >= created_from)
        if created_before is not None:
            query = query.where(LichSuThaoTac.created_at < created_before)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        sort_column = getattr(LichSuThaoTac, params.sort_by)
        descending = params.sort_order == "desc"
        ordering = sort_column.desc() if descending else sort_column.asc()
        tiebreak = LichSuThaoTac.id.desc() if descending else LichSuThaoTac.id.asc()
        rows = (
            await self.session.scalars(
                query.order_by(ordering, tiebreak).offset(offset).limit(params.page_size)
            )
        ).all()
        return RecordPage([_record(row) for row in rows], total)

    async def get_entry(self, entry_id: int) -> AuditRecord | None:
        row = await self.session.get(LichSuThaoTac, entry_id)
        return _record(row) if row is not None else None

    async def append(self, entry: CreationAudit) -> None:
        self.session.add(LichSuThaoTac(**entry.model_dump()))
