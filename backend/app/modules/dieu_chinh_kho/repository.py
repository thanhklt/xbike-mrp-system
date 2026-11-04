"""Adjustment and ticket persistence within the caller's shared transaction."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, bindparam, delete, func, insert, literal, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ConflictException
from app.modules.dieu_chinh_kho.models import (
    ChiTietPhieuDieuChinhKho,
    ChiTietTicketLoiDieuChinh,
    PhieuDieuChinhKho,
    TicketLoiDieuChinh,
)
from app.modules.dieu_chinh_kho.ports import NguonDieuChinh
from app.modules.dieu_chinh_kho.schemas import (
    DongDieuChinhRead,
    PhieuDieuChinhQuery,
    PhieuDieuChinhRead,
    TicketListQuery,
    TicketRead,
)
from app.shared.records import RecordPage


class SqlAlchemyTicketDieuChinhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def next_ticket_code(self) -> tuple[int, str]:
        return await _next_code(self.session, "TicketLoiDieuChinh", "TKDC")

    async def add_ticket(
        self, phieu_nhap_id: int, nguoi_tao_id: int, mo_ta_loi: str, lines: list[dict]
    ) -> TicketRead:
        ticket_id, code = await self.next_ticket_code()
        await self.session.execute(
            insert(TicketLoiDieuChinh).values(
                id=ticket_id,
                ma_ticket=code,
                phieu_nhap_id=phieu_nhap_id,
                nguoi_tao_id=nguoi_tao_id,
                mo_ta_loi=mo_ta_loi,
            )
        )
        await self.session.execute(
            insert(ChiTietTicketLoiDieuChinh), [{"ticket_id": ticket_id, **line} for line in lines]
        )
        return await self._updated_ticket(ticket_id)

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


async def _next_code(session: AsyncSession, table: str, prefix: str) -> tuple[int, str]:
    row = (
        await session.execute(
            text(
                "SELECT nextval(pg_get_serial_sequence(:table_name, 'id')), "
                "to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')"
            ),
            {"table_name": f'"{table}"'},
        )
    ).one()
    if row[0] > 999999:
        raise ConflictException(message="Document number exceeds six digits")
    return row[0], f"{prefix}-{row[1]}-{row[0]:06d}"


class SqlAlchemyPhieuDieuChinhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def begin_read_snapshot(self) -> None:
        # Authentication has used this session; begin the resource snapshot afterwards.
        await self.session.rollback()
        await self.session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )

    async def _read_records(self, query) -> list[PhieuDieuChinhRead]:
        records = (
            await self.session.scalars(query.execution_options(populate_existing=True))
        ).all()
        if not records:
            return []
        ids = [record.id for record in records]
        details: dict[int, list[DongDieuChinhRead]] = {phieu_id: [] for phieu_id in ids}
        lines = (
            await self.session.scalars(
                select(ChiTietPhieuDieuChinhKho)
                .where(ChiTietPhieuDieuChinhKho.phieu_dieu_chinh_kho_id.in_(ids))
                .order_by(
                    ChiTietPhieuDieuChinhKho.phieu_dieu_chinh_kho_id, ChiTietPhieuDieuChinhKho.id
                )
                .execution_options(populate_existing=True)
            )
        ).all()
        for line in lines:
            details[line.phieu_dieu_chinh_kho_id].append(DongDieuChinhRead.model_validate(line))
        return [
            PhieuDieuChinhRead.model_validate(
                {
                    **{
                        column.name: getattr(record, column.name)
                        for column in PhieuDieuChinhKho.__table__.columns
                    },
                    "chi_tiet": details[record.id],
                }
            )
            for record in records
        ]

    async def list_phieu(self, params: PhieuDieuChinhQuery) -> RecordPage[PhieuDieuChinhRead]:
        query = select(PhieuDieuChinhKho)
        for field in ("trang_thai", "phieu_nhap_id", "nhan_vien_id"):
            if (value := getattr(params, field)) is not None:
                query = query.where(getattr(PhieuDieuChinhKho, field) == value)
        if params.q:
            query = query.where(
                or_(
                    PhieuDieuChinhKho.ma_phieu.icontains(params.q, autoescape=True),
                    PhieuDieuChinhKho.ly_do.icontains(params.q, autoescape=True),
                )
            )
        if params.tu_ngay:
            query = query.where(
                PhieuDieuChinhKho.created_at
                >= func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(datetime.combine(params.tu_ngay, time.min), type_=DateTime()),
                )
            )
        if params.den_ngay:
            query = query.where(
                PhieuDieuChinhKho.created_at
                < func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(
                        datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                        type_=DateTime(),
                    ),
                )
            )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(PhieuDieuChinhKho, params.sort.lstrip("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        return RecordPage(
            await self._read_records(
                query.order_by(ordering, PhieuDieuChinhKho.id)
                .offset(offset)
                .limit(params.page_size)
            ),
            total,
        )

    async def get_phieu(self, phieu_id: int) -> PhieuDieuChinhRead | None:
        rows = await self._read_records(
            select(PhieuDieuChinhKho).where(PhieuDieuChinhKho.id == phieu_id)
        )
        return rows[0] if rows else None

    async def peek_phieu_nhap_id(self, phieu_id: int) -> int | None:
        return await self.session.scalar(
            select(PhieuDieuChinhKho.phieu_nhap_id).where(PhieuDieuChinhKho.id == phieu_id)
        )

    async def lock_phieu_nhap(self, phieu_nhap_id: int, *, update: bool) -> str | None:
        # Only the lock mode is interpolated; resource IDs remain bound parameters.
        mode = "UPDATE" if update else "SHARE"
        return await self.session.scalar(
            text(f'SELECT trang_thai FROM "PhieuNhap" WHERE id=:id FOR {mode}'),
            {"id": phieu_nhap_id},
        )

    async def lock_phieu(self, phieu_id: int) -> PhieuDieuChinhRead | None:
        rows = await self._read_records(
            select(PhieuDieuChinhKho).where(PhieuDieuChinhKho.id == phieu_id).with_for_update()
        )
        return rows[0] if rows else None

    async def nguon(
        self, phieu_nhap_id: int, giao_dich_goc_ids: list[int]
    ) -> dict[int, NguonDieuChinh]:
        rows = (
            await self.session.execute(
                text("""
            SELECT g.id, g.mat_hang_id, n.id AS chi_tiet_phieu_nhap_id,
                   g.so_luong_bien_dong + COALESCE(a.delta, 0) AS so_luong_hieu_luc
            FROM "GiaoDichKho" g JOIN "ChiTietPhieuNhap" n ON n.id=g.chi_tiet_phieu_nhap_id
            LEFT JOIN (
                SELECT c.giao_dich_goc_id, sum(m.so_luong_bien_dong) AS delta
                FROM "ChiTietPhieuDieuChinhKho" c JOIN "GiaoDichKho" m ON m.chi_tiet_phieu_dieu_chinh_id=c.id
                WHERE m.loai_giao_dich='dieu_chinh_ton_kho' GROUP BY c.giao_dich_goc_id
            ) a ON a.giao_dich_goc_id=g.id
            WHERE n.phieu_nhap_id=:pn AND g.id IN :ids
              AND g.loai_giao_dich='nhap_vat_tu' AND n.mat_hang_id=g.mat_hang_id
        """).bindparams(bindparam("ids", expanding=True)),
                {"pn": phieu_nhap_id, "ids": giao_dich_goc_ids},
            )
        ).all()
        return {row[0]: NguonDieuChinh(row[0], row[1], row[2], int(row[3])) for row in rows}

    async def add_phieu(
        self, phieu_nhap_id: int, actor_id: int, ly_do: str, lines: list[dict]
    ) -> PhieuDieuChinhRead:
        phieu_id, code = await _next_code(self.session, "PhieuDieuChinhKho", "DCK")
        await self.session.execute(
            insert(PhieuDieuChinhKho).values(
                id=phieu_id,
                ma_phieu=code,
                phieu_nhap_id=phieu_nhap_id,
                nhan_vien_id=actor_id,
                ly_do=ly_do,
            )
        )
        await self.replace_lines(phieu_id, lines)
        record = await self.get_phieu(phieu_id)
        assert record is not None
        return record

    async def replace_lines(self, phieu_id: int, lines: list[dict]) -> None:
        await self.session.execute(
            delete(ChiTietPhieuDieuChinhKho).where(
                ChiTietPhieuDieuChinhKho.phieu_dieu_chinh_kho_id == phieu_id
            )
        )
        await self.session.execute(
            insert(ChiTietPhieuDieuChinhKho.__table__),
            [
                {
                    "phieu_dieu_chinh_kho_id": phieu_id,
                    **{
                        key: value for key, value in line.items() if key != "chi_tiet_phieu_nhap_id"
                    },
                }
                for line in lines
            ],
        )

    async def update_ly_do(self, phieu_id: int, ly_do: str) -> None:
        await self.session.execute(
            update(PhieuDieuChinhKho).where(PhieuDieuChinhKho.id == phieu_id).values(ly_do=ly_do)
        )

    async def delete_draft(self, phieu_id: int) -> None:
        await self.session.execute(
            delete(ChiTietPhieuDieuChinhKho).where(
                ChiTietPhieuDieuChinhKho.phieu_dieu_chinh_kho_id == phieu_id
            )
        )
        await self.session.execute(
            delete(PhieuDieuChinhKho).where(PhieuDieuChinhKho.id == phieu_id)
        )

    async def mark_confirmed(self, phieu_id: int, confirmed_at: datetime) -> None:
        await self.session.execute(
            update(PhieuDieuChinhKho)
            .where(PhieuDieuChinhKho.id == phieu_id)
            .values(trang_thai="da_xac_nhan", confirmed_at=confirmed_at)
        )

    async def mark_failed(self, phieu_id: int) -> None:
        await self.session.execute(
            update(PhieuDieuChinhKho)
            .where(PhieuDieuChinhKho.id == phieu_id)
            .values(trang_thai="loi")
        )

    async def ledger_ids(self, phieu_id: int) -> list[int]:
        return list(
            (
                await self.session.scalars(
                    text("""SELECT g.id FROM "GiaoDichKho" g
            JOIN "ChiTietPhieuDieuChinhKho" c ON c.id=g.chi_tiet_phieu_dieu_chinh_id
            WHERE c.phieu_dieu_chinh_kho_id=:id ORDER BY g.id"""),
                    {"id": phieu_id},
                )
            ).all()
        )
