"""Inventory persistence; stock and ledger writes share the caller's transaction."""

from datetime import datetime, timezone

from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException, InsufficientStock
from app.core.persistence import select_page
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.inventory.ports import StockIssueLine, StockReceiptLine
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.modules.mat_hang.models import MatHang
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def issue_stock(
        self, lines: list[StockIssueLine], kind: str, actor_id: int, posted_at: datetime
    ) -> list[int]:
        ids = sorted(line.mat_hang_id for line in lines)
        stocks = {
            item.id: item
            for item in (
                await self.session.scalars(
                    select(MatHang)
                    .where(MatHang.id.in_(ids))
                    .order_by(MatHang.id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            ).all()
        }
        balances = dict(
            (
                await self.session.execute(
                    text(
                        'SELECT mat_hang_id, sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id IN :ids GROUP BY mat_hang_id'
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": ids},
                )
            ).all()
        )
        movements = []
        for line in sorted(lines, key=lambda item: item.mat_hang_id):
            stock = stocks.get(line.mat_hang_id)
            if stock is None or stock.so_luong_ton != balances.get(line.mat_hang_id, 0):
                raise ConflictException(message="Stock balance differs from ledger")
            if stock.so_luong_ton < line.so_luong:
                raise InsufficientStock(line.mat_hang_id, line.so_luong, stock.so_luong_ton)
            stock.so_luong_ton -= line.so_luong
            stock.ton_kho_updated_at = posted_at
            movement_id = await self.session.scalar(
                text("""INSERT INTO "GiaoDichKho"
                (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chi_tiet_phieu_xuat_id,nhan_vien_id,posted_at)
                VALUES (:item,:kind,:quantity,:source,:actor,:time) RETURNING id"""),
                {
                    "item": line.mat_hang_id,
                    "kind": kind,
                    "quantity": -line.so_luong,
                    "source": line.chi_tiet_phieu_xuat_id,
                    "actor": actor_id,
                    "time": posted_at,
                },
            )
            movements.append(movement_id)
        await self.session.flush()
        return movements

    async def receive_receipt(
        self, lines: list[StockReceiptLine], actor_id: int, posted_at: datetime
    ) -> list[int]:
        part_ids = sorted(line.mat_hang_id for line in lines)
        stocks = (
            await self.session.scalars(
                select(MatHang)
                .where(MatHang.id.in_(part_ids))
                .order_by(MatHang.id)
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
                    text("""
                        SELECT mat_hang_id, sum(so_luong_bien_dong)
                        FROM "GiaoDichKho"
                        WHERE mat_hang_id IN :part_ids
                        GROUP BY mat_hang_id
                    """).bindparams(bindparam("part_ids", expanding=True)),
                    {"part_ids": part_ids},
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
        movement_ids = []
        for line in lines:
            movement_id = await self.session.scalar(
                text("""
                    INSERT INTO "GiaoDichKho" (
                        mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                        chi_tiet_phieu_nhap_id, nhan_vien_id, posted_at
                    ) VALUES (
                        :part_id, 'nhap_vat_tu', :quantity, :detail_id, :actor_id, :posted_at
                    ) RETURNING id
                """),
                {
                    "part_id": line.mat_hang_id,
                    "quantity": line.so_luong,
                    "detail_id": line.chi_tiet_phieu_nhap_id,
                    "actor_id": actor_id,
                    "posted_at": posted_at.replace(tzinfo=timezone.utc)
                    if posted_at.tzinfo is None
                    else posted_at,
                },
            )
            movement_ids.append(movement_id)
        return sorted(movement_ids)

    async def list_stock(self, params: PageParams) -> RecordPage[StockLevelResponse]:
        return await select_page(self.session, StockLevel, StockLevelResponse, params)

    async def list_movements(self, params: PageParams) -> RecordPage[StockMovementResponse]:
        return await select_page(self.session, StockMovement, StockMovementResponse, params)
