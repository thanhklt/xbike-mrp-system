"""SQLAlchemy persistence adapter for mat_hang module."""

from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditTrailLog
from app.modules.catalog.models import Part as MatHang
from app.modules.inventory.models import StockLevel


class SqlAlchemyMatHangRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_items(
        self,
        *,
        q: str | None = None,
        loai_mat_hang: str | None = None,
        is_active: bool | None = None,
        don_vi_tinh: str | None = None,
        mau_sac: str | None = None,
        don_gia_min: int | None = None,
        don_gia_max: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_field: str = "id",
        is_desc: bool = False,
    ) -> tuple[Sequence[MatHang], int]:
        stmt = select(MatHang)
        if q and q.strip():
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    MatHang.ma_mat_hang.ilike(term),
                    MatHang.ten_mat_hang.ilike(term),
                    MatHang.sku.ilike(term),
                )
            )
        if loai_mat_hang:
            stmt = stmt.where(MatHang.loai_mat_hang == loai_mat_hang)
        if is_active is not None:
            stmt = stmt.where(MatHang.is_active == is_active)
        if don_vi_tinh:
            stmt = stmt.where(MatHang.don_vi_tinh == don_vi_tinh)
        if mau_sac:
            stmt = stmt.where(MatHang.mau_sac == mau_sac)
        if don_gia_min is not None:
            stmt = stmt.where(MatHang.don_gia >= don_gia_min)
        if don_gia_max is not None:
            stmt = stmt.where(MatHang.don_gia <= don_gia_max)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.scalar(count_stmt)) or 0

        col = getattr(MatHang, sort_field, MatHang.id)
        order_expr = col.desc() if is_desc else col.asc()
        stmt = stmt.order_by(order_expr, MatHang.id.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        records = (await self.session.scalars(stmt)).all()
        return records, total

    async def get_by_id(self, item_id: int) -> MatHang | None:
        return await self.session.scalar(select(MatHang).where(MatHang.id == item_id))

    async def find_duplicate(
        self,
        *,
        ma_mat_hang: str | None = None,
        sku: str | None = None,
        exclude_id: int | None = None,
    ) -> MatHang | None:
        conditions = []
        if ma_mat_hang:
            conditions.append(MatHang.ma_mat_hang == ma_mat_hang)
        if sku:
            conditions.append(MatHang.sku == sku)
        if not conditions:
            return None

        stmt = select(MatHang).where(or_(*conditions))
        if exclude_id is not None:
            stmt = stmt.where(MatHang.id != exclude_id)
        return await self.session.scalar(stmt)

    async def get_reference_info(self, item_id: int) -> dict:
        ton_kho_qty = 0
        try:
            stock = await self.session.scalar(
                select(StockLevel).where(StockLevel.mat_hang_id == item_id)
            )
            if stock is not None:
                ton_kho_qty = stock.so_luong or 0
        except Exception:
            pass

        has_bom = False
        try:
            row = await self.session.scalar(
                text("""
                    SELECT 1 FROM (
                        SELECT mat_hang_id FROM bom WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM chi_tiet_bom WHERE mat_hang_id = :id
                    ) b LIMIT 1
                """),
                {"id": item_id},
            )
            has_bom = row is not None
        except Exception:
            pass

        has_docs = False
        try:
            row = await self.session.scalar(
                text("""
                    SELECT 1 FROM (
                        SELECT mat_hang_id FROM chi_tiet_phieu_nhap WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM chi_tiet_phieu_xuat WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM chi_tiet_phieu_dieu_chinh_kho WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM chi_tiet_lenh_san_xuat WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM giao_dich_kho WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM yeu_cau_san_xuat WHERE mat_hang_id = :id
                        UNION ALL
                        SELECT mat_hang_id FROM lenh_san_xuat WHERE mat_hang_id = :id
                    ) d LIMIT 1
                """),
                {"id": item_id},
            )
            has_docs = row is not None
        except Exception:
            pass

        return {
            "ton_kho_qty": ton_kho_qty,
            "has_bom": has_bom,
            "has_docs": has_docs,
            "has_any_ref": (ton_kho_qty > 0) or has_bom or has_docs,
        }

    async def add(self, item: MatHang) -> MatHang:
        self.session.add(item)
        await self.session.flush()
        return item

    async def init_stock(self, item_id: int) -> StockLevel:
        stock = StockLevel(
            mat_hang_id=item_id,
            so_luong=0,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.session.add(stock)
        await self.session.flush()
        return stock

    async def update(self, item: MatHang) -> MatHang:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def delete(self, item: MatHang) -> None:
        stock_record = await self.session.scalar(
            select(StockLevel).where(StockLevel.mat_hang_id == item.id)
        )
        if stock_record is not None and (stock_record.so_luong or 0) == 0:
            await self.session.delete(stock_record)
            await self.session.flush()

        await self.session.delete(item)
        await self.session.flush()

    async def log_audit(
        self,
        actor_id: int | None,
        thao_tac: str,
        record_id: int,
        before: dict | None,
        after: dict | None,
    ) -> None:
        if actor_id is None:
            return
        try:
            self.session.add(
                AuditTrailLog(
                    nhan_vien_id=actor_id,
                    loai_doi_tuong="mat_hang",
                    doi_tuong_id=record_id,
                    thao_tac=thao_tac,
                    du_lieu_truoc=before,
                    du_lieu_sau=after,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
            )
            await self.session.flush()
        except Exception:
            pass
