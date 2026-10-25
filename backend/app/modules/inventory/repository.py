"""Inventory and ledger queries; no stock mutation is implemented here."""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import select_page
from app.modules.inventory.models import (
    StockAdjustment,
    StockAdjustmentItem,
    StockLevel,
    StockMovement,
)
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


def _to_movement_response(movement: StockMovement, so_luong_hieu_luc: int) -> StockMovementResponse:
    return StockMovementResponse(
        id=movement.id,
        mat_hang_id=movement.mat_hang_id,
        loai_giao_dich=movement.loai_giao_dich,  # type: ignore[arg-type]
        so_luong_bien_dong=movement.so_luong_bien_dong,
        so_luong_hieu_luc=so_luong_hieu_luc,
        chi_tiet_phieu_nhap_id=movement.chi_tiet_phieu_nhap_id,
        chi_tiet_phieu_xuat_id=movement.chi_tiet_phieu_xuat_id,
        chung_tu_hoan_thanh_sx_id=movement.chung_tu_hoan_thanh_sx_id,
        chi_tiet_phieu_dieu_chinh_id=movement.chi_tiet_phieu_dieu_chinh_id,
        nhan_vien_id=movement.nhan_vien_id,
        posted_at=movement.posted_at,
    )


def _movement_adjustment_subquery():
    # shortcut: correlated subquery per row; upgrade to LATERAL join when movement volume exceeds 100k rows
    return (
        select(func.coalesce(func.sum(StockAdjustmentItem.so_luong_bien_dong), 0))
        .select_from(StockAdjustmentItem)
        .join(
            StockAdjustment,
            StockAdjustment.id == StockAdjustmentItem.phieu_dieu_chinh_kho_id,
        )
        .where(
            StockAdjustmentItem.giao_dich_goc_id == StockMovement.id,
            StockAdjustment.trang_thai == "da_duyet",
        )
        .scalar_subquery()
    )


class SqlAlchemyInventoryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_stock(
        self, params: PageParams, mat_hang_id: int | None = None
    ) -> RecordPage[StockLevelResponse]:
        filters = [StockLevel.mat_hang_id == mat_hang_id] if mat_hang_id is not None else []
        return await select_page(self.session, StockLevel, StockLevelResponse, params, *filters)

    async def get_stock_by_mat_hang(self, mat_hang_id: int) -> StockLevelResponse | None:
        record = await self.session.scalar(
            select(StockLevel).where(StockLevel.mat_hang_id == mat_hang_id)
        )
        return StockLevelResponse.model_validate(record) if record is not None else None

    async def list_movements(
        self,
        params: PageParams,
        mat_hang_id: int | None = None,
        loai_giao_dich: str | None = None,
    ) -> RecordPage[StockMovementResponse]:
        adj_subquery = _movement_adjustment_subquery()
        effective_qty = (StockMovement.so_luong_bien_dong + adj_subquery).label("so_luong_hieu_luc")
        query = select(StockMovement, effective_qty)

        filters = []
        if mat_hang_id is not None:
            filters.append(StockMovement.mat_hang_id == mat_hang_id)
        if loai_giao_dich is not None:
            filters.append(StockMovement.loai_giao_dich == loai_giao_dich)

        if filters:
            query = query.where(*filters)

        count_query = select(func.count(StockMovement.id))
        if filters:
            count_query = count_query.where(*filters)
        total = await self.session.scalar(count_query) or 0

        columns = StockMovement.__table__.c
        sort_column = (
            columns.get(params.sort_by)
            if params.sort_by and params.sort_by != "created_at"
            else columns.posted_at
        )
        if sort_column is None:
            sort_column = columns.posted_at
        ordering = sort_column.desc() if params.sort_order == "desc" else sort_column.asc()

        records = (
            await self.session.execute(
                query.order_by(ordering, columns.id)
                .offset((params.page - 1) * params.page_size)
                .limit(params.page_size)
            )
        ).all()

        items = [_to_movement_response(row[0], cast(int, row[1])) for row in records]
        return RecordPage(items, total)

    async def get_movement_by_id(self, movement_id: int) -> StockMovementResponse | None:
        adj_subquery = _movement_adjustment_subquery()
        effective_qty = (StockMovement.so_luong_bien_dong + adj_subquery).label("so_luong_hieu_luc")
        query = select(StockMovement, effective_qty).where(StockMovement.id == movement_id)
        row = (await self.session.execute(query)).first()
        if row is None:
            return None
        return _to_movement_response(row[0], cast(int, row[1]))
