"""SQLAlchemy persistence for receiving; no commit or business policy."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, delete, func, literal, select, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.core.errors import ConflictException, NotFoundException
from app.modules.mat_hang.models import MatHang
from app.modules.nha_cung_cap.models import NhaCungCap
from app.modules.phieu_nhap.errors import ReceiptCodeConflict, ReceiptReferenced
from app.modules.phieu_nhap.models import ChiTietPhieuNhap, PhieuNhap
from app.modules.phieu_nhap.ports import ReceiptPart, ReceiptPosting
from app.modules.phieu_nhap.schemas import (
    GoodsReceiptNoteCreate,
    PhieuNhapListQuery,
    PhieuNhapRead,
    ReceiptItemCreate,
)
from app.shared.records import RecordPage


class SqlAlchemyPhieuNhapRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def begin_read_snapshot(self) -> None:
        # Authentication only reads in this request. Never call this from a mutation.
        if self.session.in_transaction():
            await self.session.rollback()
        await self.session.connection(
            execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True}
        )

    async def _flush(self) -> None:
        try:
            await self.session.flush()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "2200H":
                raise ConflictException(message="Receipt ID range exhausted") from exc
            raise

    async def list_receipts(self, params: PhieuNhapListQuery) -> RecordPage[PhieuNhapRead]:
        query = select(PhieuNhap)
        if params.q:
            query = query.where(PhieuNhap.ma_phieu_nhap.icontains(params.q, autoescape=True))
        for field in ("trang_thai", "ncc_id", "nhan_vien_id"):
            value = getattr(params, field)
            if value is not None:
                query = query.where(getattr(PhieuNhap, field) == value)
        if params.tu_ngay:
            start = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(datetime.combine(params.tu_ngay, time.min), type_=DateTime()),
            )
            query = query.where(PhieuNhap.created_at >= start)
        if params.den_ngay:
            end = func.timezone(
                "Asia/Ho_Chi_Minh",
                literal(
                    datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                    type_=DateTime(),
                ),
            )
            query = query.where(PhieuNhap.created_at < end)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(PhieuNhap, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, PhieuNhap.id)
                .offset(offset)
                .limit(params.page_size)
                .options(selectinload(PhieuNhap.items), selectinload(PhieuNhap.nha_cung_cap))
                .execution_options(populate_existing=True)
            )
        ).all()
        return RecordPage([PhieuNhapRead.model_validate(record) for record in records], total)

    async def get_receipt(self, record_id: int) -> PhieuNhapRead | None:
        record = await self.session.scalar(
            select(PhieuNhap)
            .where(PhieuNhap.id == record_id)
            .options(selectinload(PhieuNhap.items), selectinload(PhieuNhap.nha_cung_cap))
            .execution_options(populate_existing=True)
        )
        return PhieuNhapRead.model_validate(record) if record is not None else None

    async def lock_receipt(self, record_id: int) -> PhieuNhapRead | None:
        record = await self.session.scalar(
            select(PhieuNhap)
            .where(PhieuNhap.id == record_id)
            .options(lazyload(PhieuNhap.items), selectinload(PhieuNhap.nha_cung_cap))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            return None
        items = (
            await self.session.scalars(
                select(ChiTietPhieuNhap)
                .where(ChiTietPhieuNhap.phieu_nhap_id == record_id)
                .order_by(ChiTietPhieuNhap.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        return PhieuNhapRead.model_validate(
            {
                **{
                    column.name: getattr(record, column.name)
                    for column in PhieuNhap.__table__.columns
                },
                "items": items,
                "nha_cung_cap": record.nha_cung_cap,
            }
        )

    async def receipt_postings(self, record_id: int) -> list[ReceiptPosting]:
        rows = (
            await self.session.execute(
                text("""
                    SELECT g.id, g.chi_tiet_phieu_nhap_id, g.mat_hang_id,
                           g.so_luong_bien_dong, g.loai_giao_dich
                    FROM "GiaoDichKho" g
                    JOIN "ChiTietPhieuNhap" c ON c.id = g.chi_tiet_phieu_nhap_id
                    WHERE c.phieu_nhap_id = :record_id
                    ORDER BY g.id
                """),
                {"record_id": record_id},
            )
        ).all()
        return [ReceiptPosting(*row) for row in rows]

    async def _delete_items(self, record_id: int) -> None:
        try:
            await self.session.execute(
                delete(ChiTietPhieuNhap).where(ChiTietPhieuNhap.phieu_nhap_id == record_id)
            )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise ReceiptReferenced() from exc
            raise

    async def patch_draft(
        self, record_id: int, changes: dict, items: list[ReceiptItemCreate] | None
    ) -> PhieuNhapRead:
        if items is not None:
            await self._delete_items(record_id)
            self.session.add_all(
                [ChiTietPhieuNhap(phieu_nhap_id=record_id, **item.model_dump()) for item in items]
            )
        await self.session.execute(
            update(PhieuNhap)
            .where(PhieuNhap.id == record_id)
            .values(**changes, updated_at=func.clock_timestamp(), phien_ban=PhieuNhap.phien_ban + 1)
        )
        await self._flush()
        record = await self.get_receipt(record_id)
        if record is None:
            raise NotFoundException()
        return record

    async def delete_draft(self, record_id: int) -> None:
        await self._delete_items(record_id)
        await self.session.execute(delete(PhieuNhap).where(PhieuNhap.id == record_id))

    async def mark_completed(
        self, record_id: int, *, expected_version: int, actor_id: int, completed_at: datetime
    ) -> PhieuNhapRead | None:
        updated = await self.session.scalar(
            update(PhieuNhap)
            .where(
                PhieuNhap.id == record_id,
                PhieuNhap.trang_thai == "nhap",
                PhieuNhap.phien_ban == expected_version,
            )
            .values(
                trang_thai="hoan_thanh",
                hoan_thanh_at=completed_at,
                nguoi_hoan_thanh_id=actor_id,
                updated_at=completed_at,
                phien_ban=PhieuNhap.phien_ban + 1,
            )
            .returning(PhieuNhap.id)
        )
        return await self.get_receipt(record_id) if updated is not None else None

    async def lock_supplier(self, record_id: int) -> bool:
        return (
            await self.session.scalar(
                select(NhaCungCap.id)
                .where(NhaCungCap.id == record_id)
                .with_for_update(read=True, key_share=True)
            )
        ) is not None

    async def lock_parts(self, ids: list[int]) -> list[ReceiptPart]:
        rows = (
            await self.session.execute(
                select(MatHang.id, MatHang.loai_mat_hang, MatHang.is_active)
                .where(MatHang.id.in_(ids))
                .order_by(MatHang.id)
                .with_for_update()
            )
        ).all()
        return [ReceiptPart(*row) for row in rows]

    async def _next_code(self, prefix: str) -> str:
        # Only code generation needs an advisory lock; IDs belong to database sequences.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261022, 1)"))
        serial = await self.session.scalar(
            text("""
            WITH history AS (
                SELECT du_lieu_truoc AS snapshot FROM "LichSuThaoTac"
                WHERE loai_doi_tuong = 'phieu_nhap'
                UNION ALL SELECT du_lieu_sau FROM "LichSuThaoTac"
                WHERE loai_doi_tuong = 'phieu_nhap'
            ), codes AS (
                SELECT ma_phieu_nhap AS code FROM "PhieuNhap"
                UNION ALL SELECT snapshot->>'ma_phieu_nhap' FROM history
            )
            SELECT COALESCE(max(right(code, 6)::int), 0) FROM codes WHERE code ~ :pattern
        """),
            {"pattern": f"^{prefix}[0-9]{{6}}$"},
        )
        if serial >= 999999:
            raise ConflictException(message="Receipt monthly code range exhausted")
        return f"{prefix}{serial + 1:06d}"

    async def _insert(self, payload: GoodsReceiptNoteCreate, *, created_at: datetime) -> PhieuNhap:
        month = await self.session.scalar(
            select(
                func.to_char(
                    func.timezone(
                        "Asia/Ho_Chi_Minh",
                        literal(created_at, type_=DateTime(timezone=True)),
                    ),
                    "YYYYMM",
                )
            )
        )
        prefix = f"PN-{month}-"
        code = await self._next_code(prefix)
        fields = payload.model_dump(exclude={"items"})
        fields["ma_phieu_nhap"] = code
        record = PhieuNhap(**fields, created_at=created_at)
        record.items = [ChiTietPhieuNhap(**item.model_dump()) for item in payload.items]
        self.session.add(record)
        try:
            await self._flush()
        except IntegrityError as exc:
            if (
                getattr(getattr(exc.orig, "__cause__", None), "constraint_name", None)
                == "PhieuNhap_ma_phieu_nhap_key"
            ):
                raise ReceiptCodeConflict() from exc
            raise
        return record

    async def add_draft(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> PhieuNhapRead:
        record = await self._insert(payload, created_at=created_at)
        result = await self.get_receipt(record.id)
        assert result is not None
        return result
