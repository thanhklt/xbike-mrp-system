"""Inventory persistence; stock and ledger writes share the caller's transaction."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException
from app.core.persistence import select_page
from app.modules.catalog.models import Part
from app.modules.inventory.models import StockMovement
from app.modules.inventory.ports import StockReceiptLine
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def receive_receipt(
        self, lines: list[StockReceiptLine], actor_id: int, posted_at: datetime
    ) -> list[int]:
        part_ids = sorted(line.mat_hang_id for line in lines)
        stocks = (
            await self.session.scalars(
                select(Part)
                .where(Part.id.in_(part_ids))
                .order_by(Part.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        by_part = {stock.id: stock for stock in stocks}
        if len(by_part) != len(set(part_ids)):
            raise ConflictException(message="Receipt item no longer exists")
        ledger = dict(
            (
                await self.session.execute(
                    select(StockMovement.mat_hang_id, func.sum(StockMovement.so_luong_bien_dong))
                    .where(StockMovement.mat_hang_id.in_(part_ids))
                    .group_by(StockMovement.mat_hang_id)
                )
            ).all()
        )
        for line in sorted(lines, key=lambda line: line.mat_hang_id):
            stock = by_part[line.mat_hang_id]
            balance = stock.so_luong_ton
            if balance != ledger.get(line.mat_hang_id, 0):
                raise ConflictException(message="Stock balance does not match its ledger")
            quantity = balance + line.so_luong
            if quantity > 2**31 - 1:
                raise ConflictException(message="Stock quantity exceeds PostgreSQL INTEGER range")
            stock.so_luong_ton = quantity
            stock.ton_kho_updated_at = (
                posted_at.replace(tzinfo=timezone.utc) if posted_at.tzinfo is None else posted_at
            )
        await self.session.flush()
        movements = [
            StockMovement(
                mat_hang_id=line.mat_hang_id,
                loai_giao_dich="nhap_vat_tu",
                so_luong_bien_dong=line.so_luong,
                chi_tiet_phieu_nhap_id=line.chi_tiet_phieu_nhap_id,
                nhan_vien_id=actor_id,
                posted_at=posted_at,
            )
            for line in lines
        ]
        self.session.add_all(movements)
        await self.session.flush()
        return sorted(movement.id for movement in movements)

    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]:
        stock = select(
            Part.id,
            Part.id.label("mat_hang_id"),
            Part.so_luong_ton.label("so_luong"),
            Part.ton_kho_updated_at.label("updated_at"),
        ).subquery()
        total = await self.session.scalar(select(func.count()).select_from(stock)) or 0
        column = stock.c.get(params.sort_by or "id")
        if column is None:
            column = stock.c.id
        ordering = column.desc() if params.sort_order == "desc" else column.asc()
        rows = (
            (
                await self.session.execute(
                    select(stock)
                    .order_by(ordering, stock.c.id)
                    .offset((params.page - 1) * params.page_size)
                    .limit(params.page_size)
                )
            )
            .mappings()
            .all()
        )
        return RecordPage([StockLevelResponse.model_validate(row) for row in rows], total)

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]:
        return await select_page(self.session, StockMovement, StockMovementResponse, params)
