"""Database-backed listing, lookup and draft creation for domain routers."""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import String, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.modules.audit.models import AuditTrailLog
from app.shared.pagination import PageParams, create_paginated_response


async def list_records(db: AsyncSession, model, schema, params: PageParams, *filters):
    query = select(model).where(*filters)
    if params.search:
        columns = [c for c in model.__table__.columns if isinstance(c.type, String)]
        if columns:
            query = query.where(or_(*(c.ilike(f"%{params.search}%") for c in columns)))
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    sort_column = model.__table__.c.get(params.sort_by or "id")
    if sort_column is None:
        sort_column = model.id
    ordering = sort_column.desc() if params.sort_order == "desc" else sort_column.asc()
    records = (
        await db.scalars(
            query.order_by(ordering, model.id)
            .offset((params.page - 1) * params.page_size)
            .limit(params.page_size)
        )
    ).all()
    return create_paginated_response(
        items=[schema.model_validate(record) for record in records],
        total_items=count or 0,
        page=params.page,
        page_size=params.page_size,
    )


async def get_record(db: AsyncSession, model, record_id: int, *filters):
    record = await db.scalar(select(model).where(model.id == record_id, *filters))
    if record is None:
        raise NotFoundException(message=f"{model.__tablename__} {record_id} not found")
    return record


async def create_record(
    db: AsyncSession, model, payload, actor: dict, object_type: str, child=None
):
    values = payload.model_dump(exclude={"items", "password"})
    if "created_at" in model.__table__.c:
        values["created_at"] = datetime.utcnow()
    if model.__tablename__ in {"phieu_nhap", "phieu_xuat"}:
        values["nhan_vien_id"] = int(actor["sub"])
    if "password" in type(payload).model_fields:
        from app.core.security import get_password_hash

        values["mat_khau"] = get_password_hash(payload.password)
    record = model(**values)
    if child:
        child_model, _ = child
        record.items = [child_model(**item.model_dump()) for item in payload.items]
    try:
        db.add(record)
        await db.flush()
        # Password hashes must never be serialized into the audit trail.
        snapshot = {
            c.name: getattr(record, c.name) for c in model.__table__.columns if c.name != "mat_khau"
        }
        if child:
            snapshot["items"] = [
                {c.name: getattr(item, c.name) for c in child_model.__table__.columns}
                for item in record.items
            ]
        import json

        db.add(
            AuditTrailLog(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong=object_type,
                doi_tuong_id=record.id,
                thao_tac="tao",
                du_lieu_sau=json.loads(json.dumps(snapshot, default=str)),
            )
        )
        await db.commit()
        await db.refresh(record)
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictException(message="Document violates a database constraint") from exc
    return record


def workflow_not_implemented():
    raise HTTPException(
        status_code=501, detail="This workflow has not been implemented; no data was changed."
    )
