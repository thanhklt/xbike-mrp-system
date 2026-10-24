"""SQLAlchemy persistence for suppliers; no commit or business policy."""

from sqlalchemy import delete, exists, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException
from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.audit.models import AuditTrailLog
from app.modules.nha_cung_cap.errors import SupplierCodeConflict, SupplierReferenced
from app.modules.nha_cung_cap.models import Supplier
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapListQuery,
    SupplierCreate,
    SupplierResponse,
)
from app.modules.phieu_nhap.models import GoodsReceiptNote
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemySupplierRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_suppliers(self, params: NhaCungCapListQuery) -> RecordPage[SupplierResponse]:
        query = select(Supplier)
        if params.q:
            query = query.where(
                or_(
                    Supplier.ma_ncc.icontains(params.q, autoescape=True),
                    Supplier.ten_ncc.icontains(params.q, autoescape=True),
                )
            )
        if params.tinh is not None:
            query = query.where(Supplier.tinh == params.tinh)
        if params.phuong is not None:
            query = query.where(Supplier.phuong == params.phuong)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(Supplier, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, Supplier.id).offset(offset).limit(params.page_size)
            )
        ).all()
        return RecordPage([SupplierResponse.model_validate(record) for record in records], total)

    async def lock_by_id(self, record_id: int) -> SupplierResponse | None:
        record = await self.session.scalar(
            select(Supplier)
            .where(Supplier.id == record_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return SupplierResponse.model_validate(record) if record is not None else None

    async def has_references(self, record_id: int) -> bool:
        return bool(
            await self.session.scalar(select(exists().where(GoodsReceiptNote.ncc_id == record_id)))
        )

    async def update(self, record_id: int, changes: dict[str, str | None]) -> SupplierResponse:
        try:
            record = await self.session.scalar(
                update(Supplier)
                .where(Supplier.id == record_id)
                .values(**changes)
                .returning(Supplier)
                .execution_options(populate_existing=True)
            )
        except IntegrityError as exc:
            self._raise_supplier_conflict(exc)
            raise
        return SupplierResponse.model_validate(record)

    async def delete(self, record_id: int) -> None:
        try:
            await self.session.execute(delete(Supplier).where(Supplier.id == record_id))
        except IntegrityError as exc:
            self._raise_supplier_conflict(exc)
            raise

    @staticmethod
    def _raise_supplier_conflict(exc: IntegrityError) -> None:
        cause = exc.orig.__cause__
        if getattr(cause, "constraint_name", None) == "nha_cung_cap_ma_ncc_key":
            raise SupplierCodeConflict() from exc
        if getattr(exc.orig, "sqlstate", None) == "23503":
            raise SupplierReferenced() from exc

    async def _next_id(self) -> int:
        # Serialize both canonical and legacy creates until commit/rollback.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261020, 1)"))
        current = select(func.coalesce(func.max(Supplier.id), 0)).scalar_subquery()
        historical = (
            select(func.coalesce(func.max(AuditTrailLog.doi_tuong_id), 0))
            .where(AuditTrailLog.loai_doi_tuong == "nha_cung_cap")
            .scalar_subquery()
        )
        maximum = await self.session.scalar(select(func.greatest(current, historical)))
        if maximum >= 2**31 - 1:
            raise ConflictException(message="Supplier ID range exhausted")
        return maximum + 1

    async def list_entries(self, params: PageParams) -> RecordPage[SupplierResponse]:
        return await select_page(self.session, Supplier, SupplierResponse, params)

    async def get_by_id(self, record_id: int) -> SupplierResponse | None:
        return await select_by_id(self.session, Supplier, SupplierResponse, record_id)

    async def add(
        self, payload: SupplierCreate | NhaCungCapCreate
    ) -> CreatedRecord[SupplierResponse]:
        record = Supplier(id=await self._next_id(), **payload.model_dump())
        try:
            return await flush_created_record(self.session, record, SupplierResponse)
        except IntegrityError as exc:
            self._raise_supplier_conflict(exc)
            raise
