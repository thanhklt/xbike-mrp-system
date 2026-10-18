"""SQLAlchemy query and serialization mechanics shared by repository adapters."""

import json
from collections.abc import Sequence
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage

M = TypeVar("M", bound=Base)
T = TypeVar("T", bound=BaseModel)


async def select_page(
    session: AsyncSession,
    model: type[M],
    schema: type[T],
    params: PageParams,
    *filters: ColumnElement[bool],
) -> RecordPage[T]:
    query = select(model).where(*filters)
    columns = model.__table__.c
    if params.search:
        searchable = [column for column in columns if isinstance(column.type, String)]
        if searchable:
            query = query.where(or_(*(column.ilike(f"%{params.search}%") for column in searchable)))
    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    sort_column = columns.get(params.sort_by or "id")
    if sort_column is None:
        sort_column = columns.id
    ordering = sort_column.desc() if params.sort_order == "desc" else sort_column.asc()
    records = (
        await session.scalars(
            query.order_by(ordering, columns.id)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
    ).all()
    return RecordPage([schema.model_validate(record) for record in records], total)


async def select_by_id(
    session: AsyncSession,
    model: type[M],
    schema: type[T],
    record_id: int,
    *filters: ColumnElement[bool],
) -> T | None:
    record = await session.scalar(select(model).where(model.__table__.c.id == record_id, *filters))
    return schema.model_validate(record) if record is not None else None


async def flush_created_record(
    session: AsyncSession,
    record: M,
    schema: type[T],
    *,
    children: Sequence[Base] | None = None,
) -> CreatedRecord[T]:
    session.add(record)
    await session.flush()
    snapshot = {
        column.name: getattr(record, column.name)
        for column in record.__table__.columns
        if column.name != "mat_khau"
    }
    if children is not None:
        snapshot["items"] = [
            {column.name: getattr(child, column.name) for column in child.__table__.columns}
            for child in children
        ]
    # Preserve the existing audit JSON representation, including timestamp formatting.
    snapshot = json.loads(json.dumps(snapshot, default=str))
    return CreatedRecord(schema.model_validate(record), snapshot)
