"""SQLAlchemy production persistence; the service owns commit and rollback."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, false, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bom.models import Bom
from app.modules.san_xuat.models import (
    ChungTuHoanThanhSx,
    LenhSanXuat,
    YeuCauSanXuat,
)
from app.modules.san_xuat.schemas import (
    ChungTuRead,
    LenhRead,
    NhuCauRead,
    YeuCauCreate,
    YeuCauListQuery,
    YeuCauRead,
)
from app.shared.records import RecordPage


class SqlAlchemyYeuCauSanXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _requests(self, records: list[YeuCauSanXuat]) -> list[YeuCauRead]:
        return [YeuCauRead.model_validate(record) for record in records]

    # UC-25 Xem danh sách yêu cầu sản xuất — Main 2–3; A1, A3 (specs/use_cases/production/UC-25.md)
    async def list_entries(
        self, params: YeuCauListQuery, actor_id: int | None
    ) -> RecordPage[YeuCauRead]:
        query = select(YeuCauSanXuat)
        if actor_id is not None:
            query = query.where(
                YeuCauSanXuat.nhan_vien_duoc_giao_id == actor_id,
                YeuCauSanXuat.trang_thai != "nhap",
            )
        for name in ("mat_hang_id", "trang_thai", "nhan_vien_duoc_giao_id", "loai_yeu_cau"):
            value = getattr(params, name)
            if value is not None:
                query = query.where(
                    false()
                    if isinstance(value, int) and value > 2**31 - 1
                    else getattr(YeuCauSanXuat, name) == value
                )
        if params.q:
            query = query.where(
                YeuCauSanXuat.ma_yeu_cau_san_xuat.icontains(params.q, autoescape=True)
            )
        local_zone = ZoneInfo("Asia/Ho_Chi_Minh")
        if params.tu_ngay:
            start = datetime.combine(params.tu_ngay, time.min, local_zone).astimezone(timezone.utc)
            query = query.where(YeuCauSanXuat.created_at >= start)
        if params.den_ngay:
            end = datetime.combine(params.den_ngay, time.min, local_zone).astimezone(
                timezone.utc
            ) + timedelta(days=1)
            query = query.where(YeuCauSanXuat.created_at < end)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(YeuCauSanXuat, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        id_ordering = YeuCauSanXuat.id.desc() if params.sort.startswith("-") else YeuCauSanXuat.id.asc()
        records = (
            await self.session.scalars(
                query.order_by(ordering, id_ordering).offset(offset).limit(params.page_size)
            )
        ).all()
        return RecordPage(await self._requests(list(records)), total)

    async def get_by_id(self, request_id: int) -> YeuCauRead | None:
        record = await self.session.get(YeuCauSanXuat, request_id, populate_existing=True)
        return (await self._requests([record]))[0] if record else None

    async def get_for_update(self, request_id: int) -> YeuCauRead | None:
        record = await self.session.scalar(
            select(YeuCauSanXuat)
            .where(YeuCauSanXuat.id == request_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return (await self._requests([record]))[0] if record else None

    async def next_code(self, prefix: str) -> tuple[int, str]:
        table_name = {"YCSX": "YeuCauSanXuat"}[prefix]
        row = (
            await self.session.execute(
                text(
                    "SELECT nextval(pg_get_serial_sequence(:table_name, 'id')), "
                    "to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')"
                ),
                {"table_name": f'"{table_name}"'},
            )
        ).one()
        return row[0], f"{prefix}-{row[1]}-{row[0]:06d}"

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 5 (specs/use_cases/production/UC-23.md)
    async def add(self, payload: YeuCauCreate, actor_id: int) -> YeuCauRead:
        record_id, code = await self.next_code("YCSX")
        record = YeuCauSanXuat(
            id=record_id,
            ma_yeu_cau_san_xuat=code,
            nhan_vien_id=actor_id,
            **payload.model_dump(),
        )
        self.session.add(record)
        await self.session.flush()
        return (await self._requests([record]))[0]

    async def update(self, request_id: int, changes: dict[str, object]) -> YeuCauRead:
        record = await self.session.get(YeuCauSanXuat, request_id)
        for name, value in changes.items():
            setattr(record, name, value)
        record.phien_ban += 1
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return (await self._requests([record]))[0]

    async def delete(self, request_id: int) -> None:
        await self.session.execute(delete(YeuCauSanXuat).where(YeuCauSanXuat.id == request_id))

    # UC-23 Lập và gửi yêu cầu sản xuất — Main 8 (specs/use_cases/production/UC-23.md)
    async def bom_dang_dung(self, mat_hang_id: int) -> int:
        result = await self.session.execute(
            select(Bom.id)
            .where(Bom.mat_hang_id == mat_hang_id, Bom.is_active.is_(True))
            .with_for_update(read=True)
        )
        return result.scalar_one()

    async def so_luong_da_hoan_thanh(self, lenh_ids: list[int]) -> dict[int, int]:
        rows = await self.session.execute(
            select(
                ChungTuHoanThanhSx.lenh_san_xuat_id,
                func.sum(ChungTuHoanThanhSx.so_luong_hoan_thanh),
            )
            .where(
                ChungTuHoanThanhSx.lenh_san_xuat_id.in_(lenh_ids),
                ChungTuHoanThanhSx.trang_thai == "da_duyet",
            )
            .group_by(ChungTuHoanThanhSx.lenh_san_xuat_id)
        )
        return {order_id: int(quantity) for order_id, quantity in rows}

    async def lenh_cua_yeu_cau(self, request_id: int, *, lock: bool) -> list[LenhRead]:
        query = (
            select(LenhSanXuat)
            .where(LenhSanXuat.yeu_cau_san_xuat_id == request_id)
            .order_by(LenhSanXuat.id)
        )
        if lock:
            query = query.with_for_update()
        orders = (await self.session.scalars(query.execution_options(populate_existing=True))).all()
        totals = await self.so_luong_da_hoan_thanh([order.id for order in orders])
        children: dict[int, list[int]] = {}
        for order in orders:
            if order.lenh_san_xuat_cha_id is not None:
                children.setdefault(order.lenh_san_xuat_cha_id, []).append(order.id)
        return [
            LenhRead.model_validate(order).model_copy(
                update={
                    "nhu_cau_truc_tiep": [
                        NhuCauRead.model_validate(line) for line in order.chi_tiet
                    ],
                    "so_luong_da_hoan_thanh": totals.get(order.id, 0),
                    "so_luong_con_phai_hoan_thanh": max(
                        order.so_luong - totals.get(order.id, 0), 0
                    ),
                    "lenh_con_ids": children.get(order.id, []),
                }
            )
            for order in orders
        ]

    async def chung_tu_hoan_thanh_cua_lenh(
        self, lenh_ids: list[int], *, lock: bool
    ) -> list[ChungTuRead]:
        query = (
            select(ChungTuHoanThanhSx)
            .where(ChungTuHoanThanhSx.lenh_san_xuat_id.in_(lenh_ids))
            .order_by(ChungTuHoanThanhSx.id)
        )
        if lock:
            query = query.with_for_update()
        records = (
            await self.session.scalars(query.execution_options(populate_existing=True))
        ).all()
        return [ChungTuRead.model_validate(record) for record in records]

    async def xoa_chung_tu_nhap(self, document_id: int) -> None:
        await self.session.execute(
            delete(ChungTuHoanThanhSx).where(ChungTuHoanThanhSx.id == document_id)
        )

    async def tu_choi_chung_tu(self, document_id: int) -> ChungTuRead:
        record = await self.session.get(ChungTuHoanThanhSx, document_id)
        record.trang_thai = "tu_choi"
        await self.session.flush()
        return ChungTuRead.model_validate(record)

    async def huy_lenh(self, lenh_id: int) -> None:
        order = await self.session.get(LenhSanXuat, lenh_id)
        order.trang_thai = "da_huy"
        await self.session.flush()
