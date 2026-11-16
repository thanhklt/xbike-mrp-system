"""Inventory persistence; stock and ledger writes share the caller's transaction."""

from datetime import datetime, timezone

from sqlalchemy import bindparam, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException
from app.core.persistence import select_page
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.inventory.ports import (
    IssueReservation,
    IssueStockContext,
    StockAdjustmentLine,
    StockIssueLine,
    StockReceiptLine,
    StockShortage,
)
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.modules.mat_hang.models import MatHang
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 5 cộng thành phẩm và ghi sổ sau duyệt (specs/use_cases/production/UC-31.md)
    async def receive_production(
        self, item_id: int, quantity: int, completion_id: int, actor_id: int,
        posted_at: datetime, *, hold: bool,
    ) -> tuple[int, int]:
        stock_after = await self.session.scalar(
            text('''UPDATE "MatHang" SET so_luong_ton=so_luong_ton+:quantity,
                so_luong_dang_giu=so_luong_dang_giu+:held,
                ton_kho_updated_at=:at WHERE id=:id RETURNING so_luong_ton'''),
            {"id": item_id, "quantity": quantity, "held": quantity if hold else 0, "at": posted_at},
        )
        movement_id = await self.session.scalar(
            text('''INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,
                so_luong_bien_dong,so_luong_ton_sau,chung_tu_hoan_thanh_sx_id,
                nhan_vien_id,posted_at) VALUES (:item,'nhap_san_pham_san_xuat',
                :quantity,:stock,:source,:actor,:time) RETURNING id'''),
            {"item": item_id, "quantity": quantity, "stock": stock_after,
             "source": completion_id, "actor": actor_id, "time": posted_at},
        )
        await self.session.flush()
        return movement_id, stock_after

    async def lock_issue_stock(
        self, request_id: int, item_ids: list[int]
    ) -> list[IssueStockContext]:
        if not item_ids:
            return []
        items = (
            (
                await self.session.execute(
                    text(
                        """SELECT id, loai_mat_hang, don_gia, so_luong_ton, so_luong_dang_giu FROM "MatHang" WHERE id IN :ids ORDER BY id FOR UPDATE"""
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": sorted(set(item_ids))},
                )
            )
            .mappings()
            .all()
        )
        reservations = (
            (
                await self.session.execute(
                    text(
                        """SELECT id, yeu_cau_san_xuat_id, mat_hang_id, loai_giu, so_luong, chung_tu_hoan_thanh_sx_id FROM "GiuHang" WHERE mat_hang_id IN :ids AND trang_thai='dang_giu' ORDER BY mat_hang_id, id FOR UPDATE"""
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": sorted(set(item_ids))},
                )
            )
            .mappings()
            .all()
        )
        balances: dict[int, int] = dict(
            (
                await self.session.execute(
                    text(
                        'SELECT mat_hang_id, sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id IN :ids GROUP BY mat_hang_id'
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": item_ids},
                )
            ).all()
        )
        return [
            IssueStockContext(
                item["id"],
                item["loai_mat_hang"],
                item["don_gia"],
                item["so_luong_ton"],
                item["so_luong_dang_giu"],
                int(balances.get(item["id"], 0)),
                tuple(
                    IssueReservation(
                        row["id"],
                        row["yeu_cau_san_xuat_id"],
                        row["mat_hang_id"],
                        row["loai_giu"],
                        row["so_luong"],
                        row["chung_tu_hoan_thanh_sx_id"],
                    )
                    for row in reservations
                    if row["mat_hang_id"] == item["id"]
                ),
            )
            for item in items
        ]

    async def issue_stock(
        self,
        lines: list[StockIssueLine],
        kind: str,
        actor_id: int,
        posted_at: datetime,
        *,
        issue_id: int,
        reservations: list[IssueReservation],
    ) -> list[int]:
        # Policy and ordered locks belong to the use case; persist only validated changes.
        movements = []
        for line in sorted(lines, key=lambda item: item.mat_hang_id):
            stock_after = await self.session.scalar(
                text(
                    """UPDATE "MatHang" SET so_luong_ton=so_luong_ton-:quantity, so_luong_dang_giu=so_luong_dang_giu-:quantity, ton_kho_updated_at=:at WHERE id=:id RETURNING so_luong_ton"""
                ),
                {"quantity": line.so_luong, "at": posted_at, "id": line.mat_hang_id},
            )
            for reservation in reservations:
                if reservation.item_id == line.mat_hang_id:
                    await self.session.execute(
                        text(
                            """UPDATE "GiuHang" SET trang_thai='da_xuat', phieu_xuat_id=:issue, ket_thuc_at=:at WHERE id=:id"""
                        ),
                        {"id": reservation.id, "issue": issue_id, "at": posted_at},
                    )
            movements.append(
                await self.session.scalar(
                    text(
                        """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chi_tiet_phieu_xuat_id,nhan_vien_id,posted_at) VALUES (:item,:kind,:quantity,:stock,:source,:actor,:time) RETURNING id"""
                    ),
                    {
                        "item": line.mat_hang_id,
                        "kind": kind,
                        "quantity": -line.so_luong,
                        "stock": stock_after,
                        "source": line.chi_tiet_phieu_xuat_id,
                        "actor": actor_id,
                        "time": posted_at,
                    },
                )
            )
        await self.session.flush()
        return sorted(movements)

    async def lock_balances(self, item_ids: list[int]) -> dict[int, int]:
        stocks = (
            await self.session.scalars(
                select(MatHang)
                .where(MatHang.id.in_(item_ids))
                .order_by(MatHang.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).all()
        balances = {stock.id: stock.so_luong_ton for stock in stocks}
        if len(balances) != len(set(item_ids)):
            raise ConflictException(message="Adjustment item no longer exists")
        ledger = dict(
            (
                await self.session.execute(
                    text(
                        'SELECT mat_hang_id, sum(so_luong_bien_dong) FROM "GiaoDichKho" '
                        "WHERE mat_hang_id IN :ids GROUP BY mat_hang_id"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {"ids": item_ids},
                )
            ).all()
        )
        if any(balance != ledger.get(item_id, 0) for item_id, balance in balances.items()):
            raise ConflictException(message="Stock balance does not match its ledger")
        return balances

    async def adjust_stock(
        self, lines: list[StockAdjustmentLine], actor_id: int, posted_at: datetime
    ) -> list[int]:
        balances = await self.lock_balances([line.mat_hang_id for line in lines])
        # Aggregate per item before writing, including when several sources share an item.
        deltas: dict[int, int] = {}
        for line in lines:
            deltas[line.mat_hang_id] = deltas.get(line.mat_hang_id, 0) + line.so_luong_bien_dong
        if any(balances[item_id] + delta > 2**31 - 1 for item_id, delta in deltas.items()):
            raise ConflictException(message="Stock quantity exceeds PostgreSQL INTEGER range")
        shortages = [
            {"mat_hang_id": item_id, "so_luong_bien_dong": delta, "ton_hien_tai": balances[item_id]}
            for item_id, delta in sorted(deltas.items())
            if balances[item_id] + delta < 0
        ]
        if shortages:
            raise StockShortage(lines=shortages, balances=balances)
        timestamp = (
            posted_at.replace(tzinfo=timezone.utc) if posted_at.tzinfo is None else posted_at
        )
        for item_id, delta in sorted(deltas.items()):
            stock = await self.session.get(MatHang, item_id)
            stock.so_luong_ton = balances[item_id] + delta
            stock.ton_kho_updated_at = timestamp
        await self.session.flush()
        movement_ids = []
        for line in lines:
            movement_ids.append(
                await self.session.scalar(
                    text("""INSERT INTO "GiaoDichKho" (
                    mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                    chi_tiet_phieu_dieu_chinh_id, nhan_vien_id, posted_at
                ) VALUES (:item, 'dieu_chinh_ton_kho', :delta, :detail, :actor, :posted)
                RETURNING id"""),
                    {
                        "item": line.mat_hang_id,
                        "delta": line.so_luong_bien_dong,
                        "detail": line.chi_tiet_phieu_dieu_chinh_id,
                        "actor": actor_id,
                        "posted": timestamp,
                    },
                )
            )
        return sorted(movement_ids)

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
