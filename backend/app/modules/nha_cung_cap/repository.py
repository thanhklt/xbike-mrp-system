"""SQLAlchemy persistence for suppliers; no commit or business policy."""

from unicodedata import normalize

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import ConflictException
from app.core.persistence import select_by_id
from app.modules.nha_cung_cap.models import NhaCungCap
from app.modules.nha_cung_cap.schemas import (
    NhaCungCapCreate,
    NhaCungCapListQuery,
    SupplierResponse,
)
from app.shared.records import CreatedRecord, RecordPage

_VIETNAMESE_MARKS = "\u0300\u0301\u0302\u0303\u0306\u0309\u031b\u0323"
_ADDRESS_TRANSLATION = str.maketrans("đ", "d", _VIETNAMESE_MARKS)


def _address_contains(column: InstrumentedAttribute[str], term: str) -> ColumnElement[bool]:
    """UC-13 AC-6: fold Vietnamese accents in predicates, preserving stored addresses."""
    folded_term = normalize("NFD", term.lower()).translate(_ADDRESS_TRANSLATION)
    # PostgreSQL 16 built-ins support composed/decomposed text without an unaccent extension.
    folded_column = func.translate(
        func.normalize(func.lower(column), literal_column("NFD")), "đ" + _VIETNAMESE_MARKS, "d"
    )
    return folded_column.contains(folded_term, autoescape=True)


class SqlAlchemySupplierRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_suppliers(self, params: NhaCungCapListQuery) -> RecordPage[SupplierResponse]:
        query = select(NhaCungCap)
        if params.q:
            query = query.where(
                or_(
                    NhaCungCap.ma_ncc.icontains(params.q, autoescape=True),
                    NhaCungCap.ten_ncc.icontains(params.q, autoescape=True),
                )
            )
        if params.tinh is not None:
            query = query.where(_address_contains(NhaCungCap.tinh, params.tinh))
        if params.phuong is not None:
            query = query.where(_address_contains(NhaCungCap.phuong, params.phuong))
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(NhaCungCap, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, NhaCungCap.id).offset(offset).limit(params.page_size)
            )
        ).all()
        return RecordPage([SupplierResponse.model_validate(record) for record in records], total)

    async def get_by_id(self, record_id: int) -> SupplierResponse | None:
        return await select_by_id(self.session, NhaCungCap, SupplierResponse, record_id)

    async def add(self, payload: NhaCungCapCreate) -> CreatedRecord[SupplierResponse]:
        record = NhaCungCap(**payload.model_dump())
        self.session.add(record)
        try:
            await self.session.flush()
        except DBAPIError as exc:
            if "NCC-NNNNNN" in str(exc.orig):
                raise ConflictException(message="Supplier code range exhausted") from exc
            raise
        await self.session.refresh(record)
        result = SupplierResponse.model_validate(record)
        return CreatedRecord(result, result.model_dump(mode="json"))

    async def get_for_update(self, record_id: int) -> SupplierResponse | None:
        record = await self.session.scalar(
            select(NhaCungCap)
            .where(NhaCungCap.id == record_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return SupplierResponse.model_validate(record) if record is not None else None

    async def update(self, record_id: int, values: dict) -> SupplierResponse:
        record = await self.session.get(NhaCungCap, record_id)
        if record is None:
            raise RuntimeError("Locked supplier disappeared")
        for key, value in values.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return SupplierResponse.model_validate(record)
