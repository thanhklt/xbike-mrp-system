"""Order queries and transitions in the caller's shared SQLAlchemy transaction."""

from datetime import datetime, time, timedelta

from sqlalchemy import DateTime, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.modules.lenh_san_xuat.models import ChiTietLenhSanXuat, LenhSanXuat
from app.modules.lenh_san_xuat.ports import LenhContext
from app.modules.lenh_san_xuat.schemas import LenhQuery, LenhRead, NhuCauRead, VatTuLenhLine
from app.modules.san_xuat.models import ChungTuHoanThanhSx, YeuCauSanXuat
from app.modules.san_xuat.schemas import YeuCauRead
from app.shared.records import RecordPage


class SqlAlchemyLenhSanXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _snapshots(self, orders: list[LenhSanXuat]) -> list[LenhRead]:
        ids = [order.id for order in orders]
        if not ids:
            return []
        needs: dict[int, list[NhuCauRead]] = {key: [] for key in ids}
        for line in (
            await self.session.scalars(
                select(ChiTietLenhSanXuat)
                .where(ChiTietLenhSanXuat.lenh_san_xuat_id.in_(ids))
                .order_by(ChiTietLenhSanXuat.id)
                .execution_options(populate_existing=True)
            )
        ).all():
            needs[line.lenh_san_xuat_id].append(NhuCauRead.model_validate(line))
        children: dict[int, list[int]] = {}
        for parent_id, child_id in (
            await self.session.execute(
                select(LenhSanXuat.lenh_san_xuat_cha_id, LenhSanXuat.id)
                .where(LenhSanXuat.lenh_san_xuat_cha_id.in_(ids))
                .order_by(LenhSanXuat.id)
            )
        ).all():
            if parent_id is not None:
                children.setdefault(parent_id, []).append(child_id)
        completed = dict(
            (
                await self.session.execute(
                    select(
                        ChungTuHoanThanhSx.lenh_san_xuat_id,
                        func.sum(ChungTuHoanThanhSx.so_luong_hoan_thanh),
                    )
                    .where(
                        ChungTuHoanThanhSx.lenh_san_xuat_id.in_(ids),
                        ChungTuHoanThanhSx.trang_thai == "da_duyet",
                    )
                    .group_by(ChungTuHoanThanhSx.lenh_san_xuat_id)
                )
            ).all()
        )
        return [
            LenhRead.model_validate(
                {
                    **{
                        column.name: getattr(order, column.name)
                        for column in LenhSanXuat.__table__.columns
                    },
                    "nhu_cau_truc_tiep": needs[order.id],
                    "lenh_con_ids": children.get(order.id, []),
                    "so_luong_da_hoan_thanh": int(completed.get(order.id, 0)),
                    "so_luong_con_phai_hoan_thanh": max(
                        0, order.so_luong - int(completed.get(order.id, 0))
                    ),
                }
            )
            for order in orders
        ]

    async def list_orders(self, params: LenhQuery, employee_id: int | None) -> RecordPage[LenhRead]:
        query = select(LenhSanXuat).options(lazyload("*"))
        if employee_id is not None:
            query = query.where(LenhSanXuat.nhan_vien_id == employee_id)
        for name in (
            "yeu_cau_san_xuat_id",
            "lenh_san_xuat_cha_id",
            "nhan_vien_id",
            "mat_hang_id",
            "trang_thai",
        ):
            if (value := getattr(params, name)) is not None:
                query = query.where(getattr(LenhSanXuat, name) == value)
        if params.q:
            query = query.where(LenhSanXuat.ma_lenh_san_xuat.icontains(params.q, autoescape=True))
        if params.tu_ngay:
            query = query.where(
                LenhSanXuat.created_at
                >= func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(datetime.combine(params.tu_ngay, time.min), type_=DateTime()),
                )
            )
        if params.den_ngay:
            query = query.where(
                LenhSanXuat.created_at
                < func.timezone(
                    "Asia/Ho_Chi_Minh",
                    literal(
                        datetime.combine(params.den_ngay + timedelta(days=1), time.min),
                        type_=DateTime(),
                    ),
                )
            )
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        column = getattr(LenhSanXuat, params.sort.removeprefix("-"))
        ordering = column.desc() if params.sort.startswith("-") else column.asc()
        orders = list(
            (
                await self.session.scalars(
                    query.order_by(ordering, LenhSanXuat.id).offset(offset).limit(params.page_size)
                )
            ).all()
        )
        return RecordPage(await self._snapshots(orders), total)

    async def get_context(self, order_id: int, *, lock: bool) -> LenhContext | None:
        request_id = await self.session.scalar(
            select(LenhSanXuat.yeu_cau_san_xuat_id).where(LenhSanXuat.id == order_id)
        )
        if request_id is None:
            return None
        # Match request cancellation, issue approval and completion: request -> order.
        request = await self.session.scalar(
            select(YeuCauSanXuat)
            .where(YeuCauSanXuat.id == request_id)
            .with_for_update(read=not lock)
            .execution_options(populate_existing=True)
        )
        order = await self.session.scalar(
            select(LenhSanXuat)
            .where(LenhSanXuat.id == order_id)
            .options(lazyload("*"))
            .with_for_update(read=not lock)
            .execution_options(populate_existing=True)
        )
        if request is None or order is None:
            return None
        document = (await self._snapshots([order]))[0]
        rows = (
            await self.session.execute(
                text("""
            SELECT d.mat_hang_id, d.so_luong_can, COALESCE(s.quantity,0) AS supplied, m.so_luong_ton
            FROM "ChiTietLenhSanXuat" d JOIN "MatHang" m ON m.id=d.mat_hang_id
            LEFT JOIN (
                SELECT c.mat_hang_id, SUM(c.so_luong) AS quantity
                FROM "ChiTietPhieuXuat" c JOIN "PhieuXuat" p ON p.id=c.phieu_xuat_id
                WHERE p.lenh_san_xuat_id=:id AND p.loai_phieu='xuat_vat_tu' AND p.trang_thai='da_duyet'
                GROUP BY c.mat_hang_id
            ) s ON s.mat_hang_id=d.mat_hang_id
            WHERE d.lenh_san_xuat_id=:id ORDER BY d.id
        """),
                {"id": order_id},
            )
        ).all()
        materials = [
            VatTuLenhLine(
                mat_hang_id=item_id,
                so_luong_can=needed,
                so_luong_da_cap=int(supplied),
                so_luong_con_phai_cap=max(0, needed - int(supplied)),
                ton_hien_tai=stock,
            )
            for item_id, needed, supplied, stock in rows
        ]
        return LenhContext(document, request.trang_thai, materials)

    async def update_order(self, order_id: int, changes: dict[str, object]) -> None:
        order = await self.session.get(LenhSanXuat, order_id)
        for name, value in changes.items():
            setattr(order, name, value)
        await self.session.flush()

    async def start_request(self, request_id: int) -> tuple[YeuCauRead, YeuCauRead] | None:
        request = await self.session.get(YeuCauSanXuat, request_id)
        if request is None:
            raise RuntimeError("Locked production request disappeared")
        if request.trang_thai != "da_gui":
            return None
        order_ids = list(
            (
                await self.session.scalars(
                    select(LenhSanXuat.id)
                    .where(LenhSanXuat.yeu_cau_san_xuat_id == request_id)
                    .order_by(LenhSanXuat.id)
                )
            ).all()
        )
        supplied = int(
            await self.session.scalar(
                text(
                    """SELECT COALESCE(SUM(c.so_luong),0) FROM "ChiTietPhieuXuat" c JOIN "PhieuXuat" p ON p.id=c.phieu_xuat_id WHERE p.yeu_cau_san_xuat_id=:id AND p.loai_phieu='xuat_thanh_pham' AND p.trang_thai='da_duyet' """
                ),
                {"id": request_id},
            )
            or 0
        )
        before = YeuCauRead.model_validate(request).model_copy(
            update={
                "lenh_san_xuat_ids": order_ids,
                "so_luong_da_xuat": supplied,
                "so_luong_con_phai_xuat": max(0, request.so_luong - supplied),
            }
        )
        request.trang_thai = "dang_thuc_hien"
        await self.session.flush()
        return before, before.model_copy(update={"trang_thai": request.trang_thai})

    async def has_posted_dependency(self, order_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text("""
            SELECT EXISTS(SELECT 1 FROM "PhieuXuat" p WHERE p.lenh_san_xuat_id=:id AND p.trang_thai='da_duyet')
            OR EXISTS(SELECT 1 FROM "ChungTuHoanThanhSx" c WHERE c.lenh_san_xuat_id=:id AND c.trang_thai='da_duyet')
            OR EXISTS(SELECT 1 FROM "GiaoDichKho" g LEFT JOIN "ChiTietPhieuXuat" d ON d.id=g.chi_tiet_phieu_xuat_id
                LEFT JOIN "PhieuXuat" p ON p.id=d.phieu_xuat_id LEFT JOIN "ChungTuHoanThanhSx" c ON c.id=g.chung_tu_hoan_thanh_sx_id
                WHERE p.lenh_san_xuat_id=:id OR c.lenh_san_xuat_id=:id)
        """),
                {"id": order_id},
            )
        )

    async def has_active_children(self, order_id: int) -> bool:
        return bool(
            await self.session.scalar(
                select(LenhSanXuat.id)
                .where(
                    LenhSanXuat.lenh_san_xuat_cha_id == order_id,
                    LenhSanXuat.trang_thai.not_in(["hoan_thanh", "da_huy"]),
                )
                .limit(1)
            )
        )
