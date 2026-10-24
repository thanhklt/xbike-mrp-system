"""Inventory persistence; stock and ledger writes share the caller's transaction."""

from datetime import datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException
from app.core.persistence import select_page
from app.modules.inventory.models import StockLevel, StockMovement
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
        # Serializes ID allocation and missing balance rows across receipt posting requests.
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261022, 2)"))
        part_ids = sorted(line.mat_hang_id for line in lines)
        stocks = (
            await self.session.scalars(
                select(StockLevel)
                .where(StockLevel.mat_hang_id.in_(part_ids))
                .order_by(StockLevel.mat_hang_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        by_part = {stock.mat_hang_id: stock for stock in stocks}
        ledger = dict(
            (
                await self.session.execute(
                    select(StockMovement.mat_hang_id, func.sum(StockMovement.so_luong_bien_dong))
                    .where(StockMovement.mat_hang_id.in_(part_ids))
                    .group_by(StockMovement.mat_hang_id)
                )
            ).all()
        )
        maximum = await self.session.scalar(select(func.coalesce(func.max(StockLevel.id), 0)))
        if maximum + len(set(part_ids) - by_part.keys()) > 2**31 - 1:
            raise ConflictException(message="Stock ID range exhausted")
        for line in sorted(lines, key=lambda line: line.mat_hang_id):
            stock = by_part.get(line.mat_hang_id)
            balance = stock.so_luong if stock is not None else 0
            if balance != ledger.get(line.mat_hang_id, 0):
                raise ConflictException(message="Stock balance does not match its ledger")
            quantity = balance + line.so_luong
            if quantity > 2**31 - 1:
                raise ConflictException(message="Stock quantity exceeds PostgreSQL INTEGER range")
            if stock is None:
                maximum += 1
                self.session.add(
                    StockLevel(
                        id=maximum,
                        mat_hang_id=line.mat_hang_id,
                        so_luong=quantity,
                        updated_at=posted_at,
                    )
                )
            else:
                await self.session.execute(
                    update(StockLevel)
                    .where(StockLevel.id == stock.id)
                    .values(so_luong=quantity, updated_at=posted_at)
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
        return await select_page(self.session, StockLevel, StockLevelResponse, params)

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]:
        return await select_page(self.session, StockMovement, StockMovementResponse, params)
