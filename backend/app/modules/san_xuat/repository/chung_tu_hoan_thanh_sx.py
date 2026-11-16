"""Completion persistence; transaction boundaries belong to the service."""

from datetime import datetime, timezone

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictException, InvalidWorkflowState
from app.modules.san_xuat.models import ChungTuHoanThanhSx
from app.modules.san_xuat.schemas import ChungTuRead


class SqlAlchemyChungTuHoanThanhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock_product(self, item_id: int) -> None:
        item = await self.session.scalar(
            text('SELECT id FROM "MatHang" WHERE id=:id FOR UPDATE'), {"id": item_id},
        )
        if item is None:
            raise ConflictException(message="Thành phẩm không còn tồn tại")

    # UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 5 chốt duyệt trước khi ghi sổ (specs/use_cases/production/UC-31.md)
    async def approve(
        self, resource_id: int, version: int, actor_id: int, at: datetime,
    ) -> ChungTuRead:
        record = await self.session.scalar(
            update(ChungTuHoanThanhSx).where(
                ChungTuHoanThanhSx.id == resource_id,
                ChungTuHoanThanhSx.trang_thai == "cho_duyet",
                ChungTuHoanThanhSx.phien_ban == version,
            ).values(
                trang_thai="da_duyet", nguoi_xu_ly_id=actor_id, xu_ly_at=at,
                phien_ban=ChungTuHoanThanhSx.phien_ban + 1, updated_at=at,
            ).returning(ChungTuHoanThanhSx).execution_options(populate_existing=True)
        )
        if record is None:
            raise InvalidWorkflowState(message="Chứng từ đã thay đổi")
        await self.session.flush()
        return ChungTuRead.model_validate(record)

    # UC-31 Duyệt chứng từ hoàn thành sản xuất — Main 5 giữ thành phẩm cho yêu cầu xuất giao (specs/use_cases/production/UC-31.md)
    async def hold_production(
        self, request_id: int, item_id: int, quantity: int, completion_id: int, at: datetime,
    ) -> None:
        await self.session.execute(
            text('''INSERT INTO "GiuHang" (yeu_cau_san_xuat_id,mat_hang_id,loai_giu,
                so_luong,trang_thai,chung_tu_hoan_thanh_sx_id,created_at)
                VALUES (:request,:item,'thanh_pham_san_xuat',:quantity,'dang_giu',:source,:at)'''),
            {"request": request_id, "item": item_id, "quantity": quantity,
             "source": completion_id, "at": at},
        )
        await self.session.flush()

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
