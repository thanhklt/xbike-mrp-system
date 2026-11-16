"""Completion persistence; transaction boundaries belong to the service."""

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.schemas import ChungTuRead


class SqlAlchemyChungTuHoanThanhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def next_code(self) -> tuple[int, str]:
        row = (await self.session.execute(
            text(
                "SELECT nextval(pg_get_serial_sequence(:table_name, 'id')), "
                "to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')"
            ),
            {"table_name": '"ChungTuHoanThanhSx"'},
        )).one()
        return row[0], f"HTSX-{row[1]}-{row[0]:06d}"

    async def get_by_id(self, resource_id: int) -> ChungTuRead | None:
        record = await self.session.get(ChungTuHoanThanhSx, resource_id, populate_existing=True)
        return ChungTuRead.model_validate(record) if record else None

    async def get_by_request(self, request_id: int) -> ChungTuRead | None:
        record = await self.session.scalar(
            select(ChungTuHoanThanhSx).where(ChungTuHoanThanhSx.yeu_cau_san_xuat_id == request_id)
            .execution_options(populate_existing=True)
        )
        return ChungTuRead.model_validate(record) if record else None

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 9 khóa sau yêu cầu (specs/use_cases/production/UC-30.md)
    async def get_for_update(self, resource_id: int) -> ChungTuRead | None:
        record = await self.session.scalar(
            select(ChungTuHoanThanhSx).where(ChungTuHoanThanhSx.id == resource_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        return ChungTuRead.model_validate(record) if record else None

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 5 lưu Nháp, mã từ id (specs/use_cases/production/UC-30.md)
    async def add(self, request_id: int, quantity: int, actor_id: int) -> ChungTuRead:
        resource_id, code = await self.next_code()
        record = ChungTuHoanThanhSx(
            id=resource_id, ma_phieu=code, yeu_cau_san_xuat_id=request_id,
            so_luong_hoan_thanh=quantity, nhan_vien_id=actor_id,
        )
        self.session.add(record)
        await self.session.flush()
        return ChungTuRead.model_validate(record)

    # UC-30 Lập và gửi chứng từ hoàn thành sản xuất — Main 9; A3 tăng phiên bản (specs/use_cases/production/UC-30.md)
    async def update(self, resource_id: int, changes: dict[str, object]) -> ChungTuRead:
        record = await self.session.get(ChungTuHoanThanhSx, resource_id)
        for name, value in changes.items():
            setattr(record, name, value)
        record.phien_ban += 1
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return ChungTuRead.model_validate(record)
