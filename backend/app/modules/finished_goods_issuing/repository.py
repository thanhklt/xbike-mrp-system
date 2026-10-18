"""SQLAlchemy persistence for finished_goods_issuing; no commit or business policy."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.persistence import flush_created_record, select_by_id, select_page
from app.modules.finished_goods_issuing.models import DispatchItem, FinishedGoodsDispatch
from app.modules.finished_goods_issuing.schemas import (
    FinishedGoodsDispatchCreate,
    FinishedGoodsDispatchResponse,
)
from app.shared.pagination import PageParams
from app.shared.records import CreatedRecord, RecordPage


class SqlAlchemyFinishedGoodsIssuingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_entries(self, params: PageParams) -> RecordPage[FinishedGoodsDispatchResponse]:
        return await select_page(
            self.session,
            FinishedGoodsDispatch,
            FinishedGoodsDispatchResponse,
            params,
            FinishedGoodsDispatch.loai_phieu == "xuat_thanh_pham",
        )

    async def get_by_id(self, record_id: int) -> FinishedGoodsDispatchResponse | None:
        return await select_by_id(
            self.session,
            FinishedGoodsDispatch,
            FinishedGoodsDispatchResponse,
            record_id,
            FinishedGoodsDispatch.loai_phieu == "xuat_thanh_pham",
        )

    async def add(
        self, payload: FinishedGoodsDispatchCreate, *, created_at: datetime
    ) -> CreatedRecord[FinishedGoodsDispatchResponse]:
        record = FinishedGoodsDispatch(
            **payload.model_dump(exclude={"items"}), created_at=created_at
        )
        record.items = [DispatchItem(**item.model_dump()) for item in payload.items]
        return await flush_created_record(
            self.session, record, FinishedGoodsDispatchResponse, children=record.items
        )
