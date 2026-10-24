"""SQLAlchemy persistence for receiving; no commit or business policy."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, delete, func, literal, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.core.errors import ConflictException
from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.catalog.models import Part
from app.modules.inventory.models import StockMovement
from app.modules.nha_cung_cap.models import Supplier
from app.modules.phieu_nhap.errors import ReceiptCodeConflict, ReceiptReferenced
from app.modules.phieu_nhap.models import GoodsReceiptNote, ReceiptItem
from app.modules.phieu_nhap.ports import ReceiptPart, ReceiptPosting
from app.modules.phieu_nhap.schemas import (
    INT_MAX,
    GoodsReceiptNoteCreate,
    GoodsReceiptNoteResponse,
    PhieuNhapListQuery,
    PhieuNhapRead,
    ReceiptItemCreate,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyReceivingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_receipts(self, params: PhieuNhapListQuery) -> RecordPage[PhieuNhapRead]:
        query = select(GoodsReceiptNote)
        if params.q:
            query = query.where(GoodsReceiptNote.ma_phieu_nhap.icontains(params.q, autoescape=True))
        for field in ("trang_thai", "ncc_id", "nhan_vien_id"):
            value = getattr(params, field)
            if value is not None:
                query = query.where(getattr(GoodsReceiptNote, field) == value)
        if params.tu_ngay:
            start = func.timezone(
                "UTC",
                func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(datetime.combine(params.tu_ngay, time.min), type_=DateTime()),
                ),
            )
            query = query.where(GoodsReceiptNote.created_at >= start)
        if params.den_ngay:
            end = func.timezone(
                "UTC",
                func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(
                        datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                        type_=DateTime(),
                    ),
                ),
            )
            query = query.where(GoodsReceiptNote.created_at < end)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(GoodsReceiptNote, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, GoodsReceiptNote.id)
                .offset(offset)
                .limit(params.page_size)
                .with_for_update(read=True)
            )
        ).all()
        return RecordPage([PhieuNhapRead.model_validate(record) for record in records], total)

    async def get_receipt(self, record_id: int) -> PhieuNhapRead | None:
        record = await self.session.scalar(
            select(GoodsReceiptNote)
            .where(GoodsReceiptNote.id == record_id)
            .options(selectinload(GoodsReceiptNote.items))
            # Keep the header and select-in loaded items at the same version during PATCH.
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        return PhieuNhapRead.model_validate(record) if record is not None else None

    async def lock_receipt(self, record_id: int) -> PhieuNhapRead | None:
        record = await self.session.scalar(
            select(GoodsReceiptNote)
            .where(GoodsReceiptNote.id == record_id)
            .options(lazyload(GoodsReceiptNote.items))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if record is None:
            return None
        items = (
            await self.session.scalars(
                select(ReceiptItem)
                .where(ReceiptItem.phieu_nhap_id == record_id)
                .order_by(ReceiptItem.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        return PhieuNhapRead.model_validate(
            {
                **{
                    column.name: getattr(record, column.name)
                    for column in GoodsReceiptNote.__table__.columns
                },
                "items": items,
            }
        )

    async def receipt_postings(self, record_id: int) -> list[ReceiptPosting]:
        rows = (
            await self.session.execute(
                select(
                    StockMovement.id,
                    StockMovement.chi_tiet_phieu_nhap_id,
                    StockMovement.mat_hang_id,
                    StockMovement.so_luong_bien_dong,
                    StockMovement.loai_giao_dich,
                )
                .join(ReceiptItem, ReceiptItem.id == StockMovement.chi_tiet_phieu_nhap_id)
                .where(ReceiptItem.phieu_nhap_id == record_id)
                .order_by(StockMovement.id)
            )
        ).all()
        return [ReceiptPosting(*row) for row in rows]

    async def _delete_items(self, record_id: int) -> None:
        try:
            await self.session.execute(
                delete(ReceiptItem).where(ReceiptItem.phieu_nhap_id == record_id)
            )
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23503":
                raise ReceiptReferenced() from exc
            raise

    async def patch_draft(
        self, record_id: int, changes: dict, items: list[ReceiptItemCreate] | None
    ) -> PhieuNhapRead:
        if items is not None:
            state = await self._allocation_state("")
            if state.item_id + len(items) > INT_MAX:
                raise ConflictException(message="Receipt item ID range exhausted")
            await self._delete_items(record_id)
            self.session.add_all(
                [
                    ReceiptItem(
                        id=state.item_id + index + 1, phieu_nhap_id=record_id, **item.model_dump()
                    )
                    for index, item in enumerate(items)
                ]
            )
        if changes:
            await self.session.execute(
                update(GoodsReceiptNote).where(GoodsReceiptNote.id == record_id).values(**changes)
            )
        await self.session.flush()
        return await self.get_receipt(record_id)

    async def delete_draft(self, record_id: int) -> None:
        await self._delete_items(record_id)
        await self.session.execute(delete(GoodsReceiptNote).where(GoodsReceiptNote.id == record_id))

    async def mark_completed(self, record_id: int) -> PhieuNhapRead:
        await self.session.execute(
            update(GoodsReceiptNote)
            .where(GoodsReceiptNote.id == record_id)
            .values(trang_thai="hoan_thanh")
        )
        return await self.get_receipt(record_id)

    async def lock_supplier(self, record_id: int) -> bool:
        return (
            await self.session.scalar(
                select(Supplier.id)
                .where(Supplier.id == record_id)
                .with_for_update(read=True, key_share=True)
            )
        ) is not None

    async def lock_parts(self, ids: list[int]) -> list[ReceiptPart]:
        rows = (
            await self.session.execute(
                select(Part.id, Part.loai_mat_hang, Part.is_active)
                .where(Part.id.in_(ids))
                .order_by(Part.id)
                .with_for_update(read=True)
            )
        ).all()
        return [ReceiptPart(*row) for row in rows]

    async def _allocation_state(self, prefix: str):
        # All receipt writers, including the legacy route, share this transaction lock.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261022, 1)"))
        result = (
            await self.session.execute(
                text("""
            WITH history AS (
                SELECT doi_tuong_id, du_lieu_truoc AS snapshot FROM lich_su_thao_tac
                WHERE loai_doi_tuong = 'phieu_nhap'
                UNION ALL
                SELECT doi_tuong_id, du_lieu_sau FROM lich_su_thao_tac
                WHERE loai_doi_tuong = 'phieu_nhap'
            ), historical_items AS (
                SELECT item FROM history,
                LATERAL jsonb_array_elements(COALESCE(NULLIF(snapshot->'chi_tiet', 'null'::jsonb), NULLIF(snapshot->'items', 'null'::jsonb), '[]'::jsonb)) AS item
            ), codes AS (
                SELECT ma_phieu_nhap AS code FROM phieu_nhap
                UNION ALL SELECT snapshot->>'ma_phieu_nhap' FROM history
            )
            SELECT
                GREATEST(COALESCE((SELECT max(id) FROM phieu_nhap), 0), COALESCE((SELECT max(doi_tuong_id) FROM history), 0)) AS parent_id,
                GREATEST(COALESCE((SELECT max(id) FROM chi_tiet_phieu_nhap), 0), COALESCE((SELECT max((item->>'id')::bigint) FROM historical_items WHERE item->>'id' ~ '^[0-9]{1,10}$'), 0)) AS item_id,
                COALESCE((SELECT max(right(code, 6)::int) FROM codes WHERE code ~ :pattern), 0) AS serial
        """),
                {"pattern": f"^{prefix}[0-9]{{6}}$"},
            )
        ).one()
        return result

    async def _allocate(self, item_count: int, prefix: str) -> tuple[int, int, str]:
        result = await self._allocation_state(prefix)
        if (
            result.parent_id >= INT_MAX
            or result.item_id + item_count > INT_MAX
            or result.serial >= 999999
        ):
            raise ConflictException(message="Receipt ID or monthly code range exhausted")
        return result.parent_id + 1, result.item_id + 1, f"{prefix}{result.serial + 1:06d}"

    async def _insert(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> GoodsReceiptNote:
        month = await self.session.scalar(
            select(
                func.to_char(
                    func.timezone(
                        "Asia/Ho_Chi_Minh",
                        func.timezone("UTC", literal(created_at, type_=DateTime())),
                    ),
                    "YYYYMM",
                )
            )
        )
        prefix = f"PN-{month}-"
        parent_id, item_id, code = await self._allocate(len(payload.items), prefix)
        fields = payload.model_dump(exclude={"items"})
        fields["ma_phieu_nhap"] = payload.ma_phieu_nhap or code
        record = GoodsReceiptNote(id=parent_id, **fields, created_at=created_at)
        record.items = [
            ReceiptItem(id=item_id + index, **item.model_dump())
            for index, item in enumerate(payload.items)
        ]
        self.session.add(record)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            if (
                getattr(exc.orig.__cause__, "constraint_name", None)
                == "phieu_nhap_ma_phieu_nhap_key"
            ):
                raise ReceiptCodeConflict() from exc
            raise
        return record

    async def add_draft(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> PhieuNhapRead:
        return PhieuNhapRead.model_validate(await self._insert(payload, created_at=created_at))

    async def list_entries(self, params: PageParams) -> RecordPage[GoodsReceiptNoteResponse]:
        return await select_page(self.session, GoodsReceiptNote, GoodsReceiptNoteResponse, params)

    async def get_by_id(self, record_id: int) -> GoodsReceiptNoteResponse | None:
        return await select_by_id(
            self.session, GoodsReceiptNote, GoodsReceiptNoteResponse, record_id
        )

    async def add(
        self, payload: GoodsReceiptNoteCreate, *, created_at: datetime
    ) -> CreatedRecord[GoodsReceiptNoteResponse]:
        record = await self._insert(payload, created_at=created_at)
        return await flush_created_record(
            self.session, record, GoodsReceiptNoteResponse, children=record.items
        )
