"""Production completion persistence; the service owns commit and rollback."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, delete, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.core.errors import ConflictException
from app.modules.san_xuat.models import (
    ChiTietLenhSanXuat,
    ChungTuHoanThanhSx,
    LenhSanXuat,
    YeuCauSanXuat,
)
from app.modules.san_xuat.ports import (
    HoanThanhContext,
    HoanThanhOrder,
    HoanThanhOutput,
    HoanThanhPosting,
)
from app.modules.san_xuat.schemas import (
    ChungTuRead,
    HoanThanhCreate,
    HoanThanhQuery,
    HoanThanhRead,
    LenhRead,
)
from app.shared.records import RecordPage


class SqlAlchemyHoanThanhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _order_context(order: LenhSanXuat) -> HoanThanhOrder:
        return HoanThanhOrder(
            order.id,
            order.yeu_cau_san_xuat_id,
            order.mat_hang_id,
            order.so_luong,
            order.trang_thai,
            order.nhan_vien_id,
            order.started_at,
        )

    @staticmethod
    def _document(record: ChungTuHoanThanhSx, item_id: int) -> HoanThanhRead:
        return HoanThanhRead.model_validate(
            {
                **ChungTuRead.model_validate(record).model_dump(),
                "mat_hang_id": item_id,
            }
        )

    async def list_entries(
        self, params: HoanThanhQuery, actor_id: int | None
    ) -> RecordPage[HoanThanhRead]:
        query = select(ChungTuHoanThanhSx, LenhSanXuat.mat_hang_id).join(
            LenhSanXuat,
            LenhSanXuat.id == ChungTuHoanThanhSx.lenh_san_xuat_id,
        )
        if actor_id is not None:
            query = query.where(
                ChungTuHoanThanhSx.nhan_vien_id == actor_id,
                LenhSanXuat.nhan_vien_id == actor_id,
            )
        for name in ("lenh_san_xuat_id", "nhan_vien_id", "trang_thai"):
            value = getattr(params, name)
            if value is not None:
                query = query.where(getattr(ChungTuHoanThanhSx, name) == value)
        if params.mat_hang_id is not None:
            query = query.where(LenhSanXuat.mat_hang_id == params.mat_hang_id)
        if params.q:
            query = query.where(ChungTuHoanThanhSx.ma_phieu.icontains(params.q, autoescape=True))
        if params.tu_ngay:
            start = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(
                    datetime.combine(params.tu_ngay, time.min),
                    type_=DateTime(),
                ),
            )
            query = query.where(ChungTuHoanThanhSx.finish_time >= start)
        if params.den_ngay:
            end = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(
                    datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                    type_=DateTime(),
                ),
            )
            query = query.where(ChungTuHoanThanhSx.finish_time < end)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(ChungTuHoanThanhSx, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        rows = (
            await self.session.execute(
                query.order_by(ordering.nulls_last(), ChungTuHoanThanhSx.id)
                .offset(offset)
                .limit(params.page_size)
                .execution_options(populate_existing=True)
            )
        ).all()
        return RecordPage([self._document(record, item_id) for record, item_id in rows], total)

    async def get_by_id(self, document_id: int) -> HoanThanhContext | None:
        row = (
            await self.session.execute(
                select(ChungTuHoanThanhSx, LenhSanXuat)
                .join(LenhSanXuat, LenhSanXuat.id == ChungTuHoanThanhSx.lenh_san_xuat_id)
                .where(ChungTuHoanThanhSx.id == document_id)
                .options(lazyload("*"))
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        if row is None:
            return None
        record, order = row
        return HoanThanhContext(
            self._document(record, order.mat_hang_id), self._order_context(order)
        )

    async def lock_for_create(self, order_id: int) -> HoanThanhOrder | None:
        request_id = await self.session.scalar(
            select(LenhSanXuat.yeu_cau_san_xuat_id).where(LenhSanXuat.id == order_id)
        )
        if request_id is None:
            return None
        request = await self.session.scalar(
            select(YeuCauSanXuat)
            .where(YeuCauSanXuat.id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order = await self.session.scalar(
            select(LenhSanXuat)
            .where(LenhSanXuat.id == order_id)
            .options(lazyload("*"))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if request is None or order is None:
            return None
        if order.yeu_cau_san_xuat_id != request_id:
            raise ConflictException(message="Nguồn lệnh sản xuất đã thay đổi")
        return self._order_context(order)

    async def lock_context(self, document_id: int) -> HoanThanhContext | None:
        order_id = await self.session.scalar(
            select(ChungTuHoanThanhSx.lenh_san_xuat_id).where(ChungTuHoanThanhSx.id == document_id)
        )
        if order_id is None:
            return None
        order = await self.lock_for_create(order_id)
        if order is None:
            return None
        record = await self.session.scalar(
            select(ChungTuHoanThanhSx)
            .where(ChungTuHoanThanhSx.id == document_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            return None
        if record.lenh_san_xuat_id != order.id:
            raise ConflictException(message="Nguồn chứng từ hoàn thành đã thay đổi")
        return HoanThanhContext(self._document(record, order.mat_hang_id), order)

    async def next_hoan_thanh_code(self) -> tuple[int, str]:
        record_id, month = (
            await self.session.execute(
                text("""
            SELECT nextval(pg_get_serial_sequence('"ChungTuHoanThanhSx"', 'id')),
                   to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')
        """)
            )
        ).one()
        if record_id > 999999:
            raise ConflictException(message="Hết dải mã chứng từ hoàn thành")
        return record_id, f"HTSX-{month}-{record_id:06d}"

    async def add(self, payload: HoanThanhCreate, actor_id: int) -> HoanThanhRead:
        record_id, code = await self.next_hoan_thanh_code()
        record = ChungTuHoanThanhSx(
            id=record_id,
            ma_phieu=code,
            nhan_vien_id=actor_id,
            trang_thai="nhap",
            **payload.model_dump(),
        )
        self.session.add(record)
        await self.session.flush()
        return (await self.get_by_id(record_id)).document

    async def update(self, document_id: int, changes: dict[str, object]) -> HoanThanhRead:
        record = await self.session.get(ChungTuHoanThanhSx, document_id)
        for name, value in changes.items():
            setattr(record, name, value)
        # The ledger's source trigger requires da_duyet to be visible before INSERT.
        await self.session.flush()
        return (await self.get_by_id(document_id)).document

    async def delete(self, document_id: int) -> None:
        await self.session.execute(
            delete(ChungTuHoanThanhSx).where(ChungTuHoanThanhSx.id == document_id)
        )

    async def postings(self, document_id: int) -> list[HoanThanhPosting]:
        rows = (
            await self.session.execute(
                text("""
            SELECT id, mat_hang_id, so_luong_bien_dong, loai_giao_dich, chung_tu_hoan_thanh_sx_id
            FROM "GiaoDichKho" WHERE chung_tu_hoan_thanh_sx_id = :id ORDER BY id
        """),
                {"id": document_id},
            )
        ).all()
        return [HoanThanhPosting(*row) for row in rows]

    async def approved_quantity(self, order_id: int) -> int:
        return int(
            await self.session.scalar(
                select(func.coalesce(func.sum(ChungTuHoanThanhSx.so_luong_hoan_thanh), 0)).where(
                    ChungTuHoanThanhSx.lenh_san_xuat_id == order_id,
                    ChungTuHoanThanhSx.trang_thai == "da_duyet",
                )
            )
        )

    async def material_quantities(self, order_id: int) -> tuple[dict[int, int], dict[int, int]]:
        demand = dict(
            (
                await self.session.execute(
                    select(ChiTietLenhSanXuat.mat_hang_id, ChiTietLenhSanXuat.so_luong_can).where(
                        ChiTietLenhSanXuat.lenh_san_xuat_id == order_id
                    )
                )
            ).all()
        )
        supplied = dict(
            (
                await self.session.execute(
                    text("""
            SELECT g.mat_hang_id, -sum(g.so_luong_bien_dong)
            FROM "GiaoDichKho" g
            JOIN "ChiTietPhieuXuat" c ON c.id = g.chi_tiet_phieu_xuat_id
            JOIN "PhieuXuat" p ON p.id = c.phieu_xuat_id
            WHERE p.lenh_san_xuat_id = :order_id
              AND p.loai_phieu = 'xuat_vat_tu' AND p.trang_thai = 'da_duyet'
              AND g.loai_giao_dich = 'xuat_vat_tu'
            GROUP BY g.mat_hang_id
        """),
                    {"order_id": order_id},
                )
            ).all()
        )
        return demand, {item_id: int(quantity) for item_id, quantity in supplied.items()}

    async def read_output(self, item_id: int) -> HoanThanhOutput | None:
        row = (
            await self.session.execute(
                text("""
            SELECT id, is_active, loai_mat_hang, so_luong_ton FROM "MatHang"
            WHERE id = :id FOR SHARE
        """),
                {"id": item_id},
            )
        ).one_or_none()
        return HoanThanhOutput(*row, ledger_total=0) if row else None

    async def lock_output(self, item_id: int) -> HoanThanhOutput | None:
        row = (
            await self.session.execute(
                text("""
            SELECT id, is_active, loai_mat_hang, so_luong_ton FROM "MatHang"
            WHERE id = :id FOR UPDATE
        """),
                {"id": item_id},
            )
        ).one_or_none()
        if row is None:
            return None
        total = await self.session.scalar(
            text("""
            SELECT coalesce(sum(so_luong_bien_dong), 0) FROM "GiaoDichKho" WHERE mat_hang_id = :id
        """),
            {"id": item_id},
        )
        return HoanThanhOutput(*row, ledger_total=int(total))

    async def post_output(self, document: HoanThanhRead, actor_id: int, posted_at: datetime) -> int:
        params = {
            "quantity": document.so_luong_hoan_thanh,
            "posted_at": posted_at,
            "item_id": document.mat_hang_id,
            "document_id": document.id,
            "actor_id": actor_id,
        }
        await self.session.execute(
            text("""
            UPDATE "MatHang" SET so_luong_ton = so_luong_ton + :quantity,
                ton_kho_updated_at = :posted_at WHERE id = :item_id
        """),
            params,
        )
        return await self.session.scalar(
            text("""
            INSERT INTO "GiaoDichKho" (mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                chung_tu_hoan_thanh_sx_id, nhan_vien_id, posted_at)
            VALUES (:item_id, 'nhap_san_pham_san_xuat', :quantity, :document_id, :actor_id, :posted_at)
            RETURNING id
        """),
            params,
        )

    async def complete_order(
        self, order_id: int, completed_at: datetime
    ) -> tuple[LenhRead, LenhRead]:
        request_id = await self.session.scalar(
            select(LenhSanXuat.yeu_cau_san_xuat_id).where(LenhSanXuat.id == order_id)
        )
        reader = SqlAlchemyYeuCauSanXuatRepository(self.session)
        before = next(
            order
            for order in await reader.lenh_cua_yeu_cau(request_id, lock=False)
            if order.id == order_id
        )
        order = await self.session.get(LenhSanXuat, order_id)
        order.trang_thai = "hoan_thanh"
        order.completed_at = completed_at
        await self.session.flush()
        after = next(
            order
            for order in await reader.lenh_cua_yeu_cau(request_id, lock=False)
            if order.id == order_id
        )
        return before, after
