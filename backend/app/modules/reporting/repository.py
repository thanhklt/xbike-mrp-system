"""Dashboard aggregation over existing ORM mappings."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Part
from app.modules.material_issuing.models import IssueNote
from app.modules.production.models import WorkOrder


class SqlAlchemyReportingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def count_active_work_orders(self) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(WorkOrder)
                .where(WorkOrder.trang_thai.in_(["da_gui", "dang_thuc_hien"]))
            )
            or 0
        )

    async def count_catalog_parts(self) -> int:
        return await self.session.scalar(select(func.count()).select_from(Part)) or 0

    async def count_dispatches(self, start: datetime, end: datetime) -> int:
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(IssueNote)
                .where(
                    IssueNote.loai_phieu == "xuat_thanh_pham",
                    IssueNote.trang_thai == "da_duyet",
                    IssueNote.created_at >= start,
                    IssueNote.created_at < end,
                )
            )
            or 0
        )
