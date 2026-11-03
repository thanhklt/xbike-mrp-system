"""SQLAlchemy ticket persistence within the caller's shared transaction."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, func, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.ticket_dieu_chinh.models import TicketLoiDieuChinh
from app.modules.ticket_dieu_chinh.schemas import TicketListQuery, TicketRead
from app.shared.records import RecordPage


class SqlAlchemyTicketDieuChinhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_tickets(self, params: TicketListQuery) -> RecordPage[TicketRead]:
        query = select(TicketLoiDieuChinh)
        for field in ("trang_thai", "phieu_nhap_id", "nguoi_tao_id", "nguoi_xu_ly_id"):
            if (value := getattr(params, field)) is not None:
                query = query.where(getattr(TicketLoiDieuChinh, field) == value)
        if params.tu_ngay:
            boundary = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(datetime.combine(params.tu_ngay, time.min), type_=DateTime()),
            )
            query = query.where(TicketLoiDieuChinh.created_at >= boundary)
        if params.den_ngay:
            boundary = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(
                    datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                    type_=DateTime(),
                ),
            )
            query = query.where(TicketLoiDieuChinh.created_at < boundary)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(TicketLoiDieuChinh, params.sort.lstrip("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, TicketLoiDieuChinh.id)
                .offset(offset)
                .limit(params.page_size)
                .options(selectinload(TicketLoiDieuChinh.chi_tiet))
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
        ).all()
        return RecordPage([TicketRead.model_validate(record) for record in records], total)

    async def get_ticket(self, ticket_id: int) -> TicketRead | None:
        record = await self.session.scalar(
            select(TicketLoiDieuChinh)
            .where(TicketLoiDieuChinh.id == ticket_id)
            .options(selectinload(TicketLoiDieuChinh.chi_tiet))
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        return TicketRead.model_validate(record) if record is not None else None

    async def lock_ticket(self, ticket_id: int) -> TicketRead | None:
        record = await self.session.scalar(
            select(TicketLoiDieuChinh)
            .where(TicketLoiDieuChinh.id == ticket_id)
            .options(selectinload(TicketLoiDieuChinh.chi_tiet))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return TicketRead.model_validate(record) if record is not None else None

    async def claim_ticket(self, ticket_id: int, actor_id: int) -> TicketRead:
        await self.session.execute(
            update(TicketLoiDieuChinh)
            .where(TicketLoiDieuChinh.id == ticket_id)
            .values(trang_thai="dang_xu_ly", nguoi_xu_ly_id=actor_id)
        )
        return await self._updated_ticket(ticket_id)

    async def resolve_ticket(
        self, ticket_id: int, actor_id: int, result: str, closed_at: datetime
    ) -> TicketRead:
        await self.session.execute(
            update(TicketLoiDieuChinh)
            .where(TicketLoiDieuChinh.id == ticket_id)
            .values(
                trang_thai="da_xu_ly",
                nguoi_xu_ly_id=actor_id,
                ket_qua_xu_ly=result,
                closed_at=closed_at,
            )
        )
        return await self._updated_ticket(ticket_id)

    async def _updated_ticket(self, ticket_id: int) -> TicketRead:
        record = await self.get_ticket(ticket_id)
        assert record is not None, "Locked ticket must still exist in the current transaction"
        return record
