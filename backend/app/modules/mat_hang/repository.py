"""SQLAlchemy adapter for the authoritative MatHang table."""

from collections.abc import Iterable
from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mat_hang.models import MatHang
from app.modules.mat_hang.ports import ItemReferences
from app.modules.mat_hang.schemas import MatHangCreate, MatHangRead


class SqlAlchemyMatHangRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_all(self) -> list[MatHangRead]:
        records = await self.session.scalars(select(MatHang).order_by(MatHang.id))
        return [MatHangRead.model_validate(record) for record in records]

    async def get_for_update(self, item_id: int) -> MatHangRead | None:
        record = await self.session.scalar(
            select(MatHang)
            .where(MatHang.id == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return MatHangRead.model_validate(record) if record is not None else None

    async def find_duplicate(
        self,
        *,
        ma_mat_hang: str | None = None,
        sku: str | None = None,
        exclude_id: int | None = None,
    ) -> bool:
        conditions = []
        if ma_mat_hang is not None:
            conditions.append(MatHang.ma_mat_hang == ma_mat_hang)
        if sku is not None:
            conditions.append(MatHang.sku == sku)
        if not conditions:
            return False
        query = select(MatHang.id).where(or_(*conditions))
        if exclude_id is not None:
            query = query.where(MatHang.id != exclude_id)
        return await self.session.scalar(query.limit(1)) is not None

    async def get_references(self, item_id: int) -> ItemReferences:
        row = (
            await self.session.execute(
                text("""
            SELECT
                EXISTS (SELECT 1 FROM "Bom" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "ChiTietBom" WHERE mat_hang_id=:id) AS has_bom,
                EXISTS (SELECT 1 FROM "ChiTietPhieuNhap" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "ChiTietPhieuXuat" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "ChiTietPhieuDieuChinhKho" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "ChiTietLenhSanXuat" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "GiaoDichKho" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "YeuCauSanXuat" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "LenhSanXuat" WHERE mat_hang_id=:id
                        UNION ALL SELECT 1 FROM "ChiTietTicketLoiDieuChinh" WHERE mat_hang_id=:id) AS has_docs,
                EXISTS (SELECT 1 FROM "MatHang" WHERE id=:id AND so_luong_ton > 0) AS has_stock
        """),
                {"id": item_id},
            )
        ).one()
        return ItemReferences(row.has_bom, row.has_docs, row.has_stock)

    async def add(self, payload: MatHangCreate) -> MatHangRead:
        record = MatHang(**payload.model_dump())
        self.session.add(record)
        await self.session.flush()
        return MatHangRead.model_validate(record)

    async def update(self, item_id: int, changes: dict[str, Any]) -> MatHangRead:
        record = await self.session.get(MatHang, item_id)
        if record is None:
            raise LookupError("Locked item disappeared")
        for name, value in changes.items():
            setattr(record, name, value)
        await self.session.flush()
        return MatHangRead.model_validate(record)

    async def lock_items(self, item_ids: Iterable[int]) -> list[MatHangRead]:
        records = await self.session.scalars(
            select(MatHang)
            .where(MatHang.id.in_(sorted(set(item_ids))))
            .order_by(MatHang.id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        return [MatHangRead.model_validate(record) for record in records]
