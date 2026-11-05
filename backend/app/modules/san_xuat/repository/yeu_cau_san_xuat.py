"""SQLAlchemy production persistence; the service owns commit and rollback."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, false, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.san_xuat.models import (
    ChiTietLenhSanXuat,
    ChungTuHoanThanhSx,
    LenhSanXuat,
    YeuCauSanXuat,
)
from app.modules.san_xuat.schemas import (
    ChungTuRead,
    LenhDuKien,
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
        orders: dict[int, list[int]] = {}
        if records:
            rows = await self.session.execute(
                select(LenhSanXuat.yeu_cau_san_xuat_id, LenhSanXuat.id)
                .where(LenhSanXuat.yeu_cau_san_xuat_id.in_([record.id for record in records]))
                .order_by(LenhSanXuat.id)
            )
            for request_id, order_id in rows:
                orders.setdefault(request_id, []).append(order_id)
        return [
            YeuCauRead.model_validate(record).model_copy(
                update={
                    "lenh_san_xuat_ids": orders.get(record.id, []),
                }
            )
            for record in records
        ]

    async def list_entries(
        self, params: YeuCauListQuery, actor_id: int | None
    ) -> RecordPage[YeuCauRead]:
        query = select(YeuCauSanXuat)
        if actor_id is not None:
            query = query.where(YeuCauSanXuat.nhan_vien_duoc_giao_id == actor_id)
        for name in ("mat_hang_id", "trang_thai", "nhan_vien_duoc_giao_id"):
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
        records = (
            await self.session.scalars(
                query.order_by(ordering, YeuCauSanXuat.id).offset(offset).limit(params.page_size)
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
        table_name = {"YCSX": "YeuCauSanXuat", "LSX": "LenhSanXuat"}[prefix]
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
        await self.session.flush()
        return (await self._requests([record]))[0]

    async def has_dependencies(self, request_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    'SELECT EXISTS(SELECT 1 FROM "LenhSanXuat" WHERE yeu_cau_san_xuat_id = :id) '
                    'OR EXISTS(SELECT 1 FROM "PhieuXuat" WHERE yeu_cau_san_xuat_id = :id)'
                ),
                {"id": request_id},
            )
        )

    async def delete(self, request_id: int) -> None:
        await self.session.execute(delete(YeuCauSanXuat).where(YeuCauSanXuat.id == request_id))

    async def add_lenh_tree(self, request_id: int, planned: list[LenhDuKien]) -> list[LenhRead]:
        order_ids: dict[str, int] = {}
        for order in planned:
            order_id, code = await self.next_code("LSX")
            self.session.add(
                LenhSanXuat(
                    id=order_id,
                    ma_lenh_san_xuat=code,
                    yeu_cau_san_xuat_id=request_id,
                    lenh_san_xuat_cha_id=order_ids.get(order.ma_cha_tam),
                    mat_hang_id=order.mat_hang_id,
                    bom_id=order.bom_id,
                    so_luong=order.so_luong,
                    nhan_vien_id=None,
                )
            )
            # Parent snapshot must exist before the database validates a child order.
            await self.session.flush()
            self.session.add_all(
                [
                    ChiTietLenhSanXuat(lenh_san_xuat_id=order_id, **need.model_dump())
                    for need in order.nhu_cau_truc_tiep
                ]
            )
            await self.session.flush()
            order_ids[order.ma_tam] = order_id
        return await self.lenh_cua_yeu_cau(request_id, lock=False)

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
