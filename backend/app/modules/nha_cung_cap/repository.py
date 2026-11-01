"""SQLAlchemy persistence for suppliers; no commit or business policy."""

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException, DuplicateCodeException
from app.core.persistence import flush_created_record, select_by_id
from app.modules.audit.models import LichSuThaoTac
from app.modules.nha_cung_cap.models import Supplier
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapListQuery,
    SupplierResponse,
)
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

    @staticmethod
    def _raise_supplier_conflict(exc: IntegrityError) -> None:
        cause = exc.orig.__cause__
        if getattr(cause, "constraint_name", None) == "NhaCungCap_ma_ncc_key":
            raise DuplicateCodeException(message="Mã nhà cung cấp đã tồn tại") from exc

    async def _next_id(self) -> int:
        # Serialize supplier creates until commit/rollback.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261020, 1)"))
        current = select(func.coalesce(func.max(Supplier.id), 0)).scalar_subquery()
        historical = (
            select(func.coalesce(func.max(LichSuThaoTac.doi_tuong_id), 0))
            .where(LichSuThaoTac.loai_doi_tuong == "nha_cung_cap")
            .scalar_subquery()
        )
        maximum = await self.session.scalar(select(func.greatest(current, historical)))
        if maximum >= 2**31 - 1:
            raise ConflictException(message="Supplier ID range exhausted")
        return maximum + 1

    async def get_by_id(self, record_id: int) -> SupplierResponse | None:
        return await select_by_id(self.session, Supplier, SupplierResponse, record_id)

    async def add(self, payload: NhaCungCapCreate) -> CreatedRecord[SupplierResponse]:
        record = Supplier(id=await self._next_id(), **payload.model_dump())
        try:
            return await flush_created_record(self.session, record, SupplierResponse)
        except IntegrityError as exc:
            self._raise_supplier_conflict(exc)
            raise
