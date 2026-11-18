"""SQLAlchemy production persistence; the service owns commit and rollback."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, delete, false, func, literal_column, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bom.models import Bom, ChiTietBom
from app.modules.mat_hang.models import MatHang
from app.modules.nhan_vien.models import NhanVien
from app.modules.phieu_xuat.models import PhieuXuat
from app.modules.san_xuat.models import (
    ChungTuHoanThanhSx,
    GiuHang,
    NhuCauLinhKien,
    YeuCauSanXuat,
)
from app.modules.san_xuat.ports import HangKhaDung
from app.modules.san_xuat.schemas import (
    HangTraLine,
    YeuCauCreate,
    YeuCauListQuery,
    YeuCauRead,
)
from app.shared.records import RecordPage


def _search_text(value):
    # PostgreSQL UTF-8 normalization avoids adding an unaccent extension/schema change.
    return func.translate(
        func.normalize(func.lower(value), literal_column("NFD")),
        "đ\u0300\u0301\u0303\u0309\u0323\u0302\u0306\u031b",
        "d",
    )


def _work_status_expression():
    request = YeuCauSanXuat
    component = select(PhieuXuat.trang_thai).where(
        PhieuXuat.yeu_cau_san_xuat_id == request.id,
        PhieuXuat.loai_phieu == "xuat_linh_kien",
    ).scalar_subquery()
    finished = select(PhieuXuat.trang_thai).where(
        PhieuXuat.yeu_cau_san_xuat_id == request.id,
        PhieuXuat.loai_phieu == "xuat_thanh_pham",
    ).scalar_subquery()
    completion = select(ChungTuHoanThanhSx.trang_thai).where(
        ChungTuHoanThanhSx.yeu_cau_san_xuat_id == request.id,
    ).scalar_subquery()
    active = request.trang_thai == "dang_thuc_hien"
    needs_production = request.so_luong_can_san_xuat > 0
    export_ready = and_(active, request.loai_yeu_cau == "xuat_giao",
                        request.kiem_tra_lan_dau_at.is_not(None),
                        or_(request.so_luong_can_san_xuat == 0,
                            and_(needs_production, completion == "da_duyet")))
    return case(
        (request.trang_thai == "hoan_thanh", "hoan_thanh"),
        (request.trang_thai == "da_huy", "da_huy"),
        (or_(component == "tu_choi", finished == "tu_choi", completion == "tu_choi"), None),
        (and_(export_ready, finished == "cho_duyet"), "cho_duyet_phieu_xuat"),
        (and_(export_ready, or_(finished.is_(None), finished == "nhap")), "cho_lap_phieu_xuat"),
        (and_(active, request.started_at.is_not(None), completion == "cho_duyet"), "cho_duyet_hoan_thanh"),
        (and_(active, request.started_at.is_not(None),
              or_(completion.is_(None), completion == "nhap")), "dang_san_xuat"),
        (and_(active, needs_production, request.started_at.is_(None), component == "da_duyet"), "san_sang_san_xuat"),
        (and_(request.trang_thai.in_(["dang_thuc_hien", "cho_bo_sung_linh_kien"]),
              needs_production, request.started_at.is_(None), component == "cho_duyet"), "cho_duyet_xuat_linh_kien"),
        (and_(request.trang_thai.in_(["da_gui", "dang_thuc_hien", "cho_bo_sung_linh_kien"]),
              request.started_at.is_(None), completion.is_(None),
              or_(component.is_(None), component == "nhap")), "da_giao"),
        else_=None,
    )


class SqlAlchemyYeuCauSanXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def begin_read_snapshot(self) -> None:
        # Match the document reads: count, page and work labels share one read-only snapshot.
        if self.session.in_transaction():
            await self.session.rollback()
        await self.session.connection(
            execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True},
        )

    async def work_statuses(self, request_ids: list[int]) -> dict[int, str | None]:
        if not request_ids:
            return {}
        rows = await self.session.execute(
            select(YeuCauSanXuat.id, _work_status_expression()).where(YeuCauSanXuat.id.in_(request_ids)),
        )
        return dict(rows.all())

    async def creator_identity(self, employee_id: int) -> tuple[str | None, str | None]:
        result = await self.session.execute(
            select(NhanVien.ho_ten, NhanVien.ma_nhan_vien).where(NhanVien.id == employee_id),
        )
        row = result.one_or_none()
        return (row.ho_ten, row.ma_nhan_vien) if row else (None, None)

    async def giu_hang_dang_giu(self, yeu_cau_id: int, *, lock: bool) -> list[HangTraLine]:
        query = (
            select(
                GiuHang.id, GiuHang.mat_hang_id, MatHang.ma_mat_hang, MatHang.ten_mat_hang,
                MatHang.don_vi_tinh, GiuHang.loai_giu, GiuHang.so_luong,
            )
            .join(MatHang, MatHang.id == GiuHang.mat_hang_id)
            .where(GiuHang.yeu_cau_san_xuat_id == yeu_cau_id, GiuHang.trang_thai == "dang_giu")
            .order_by(GiuHang.mat_hang_id, GiuHang.id)
        )
        if lock:
            query = query.with_for_update(of=GiuHang)
        rows = await self.session.execute(query)
        return [HangTraLine.model_validate(dict(row)) for row in rows.mappings()]

    # UC-28 Hủy yêu cầu sản xuất — R3, R5 khóa mặt hàng theo id rồi trả giữ hàng (specs/use_cases/production/UC-28.md)
    async def tra_giu_hang(self, yeu_cau_id: int) -> list[HangTraLine]:
        item_ids = select(GiuHang.mat_hang_id).where(
            GiuHang.yeu_cau_san_xuat_id == yeu_cau_id, GiuHang.trang_thai == "dang_giu",
        )
        await self.session.execute(
            select(MatHang.id).where(MatHang.id.in_(item_ids))
            .order_by(MatHang.id).with_for_update()
        )
        reservations = await self.giu_hang_dang_giu(yeu_cau_id, lock=True)
        quantities: dict[int, int] = {}
        for row in reservations:
            quantities[row.mat_hang_id] = quantities.get(row.mat_hang_id, 0) + row.so_luong
        for item_id, quantity in sorted(quantities.items()):
            await self.session.execute(
                update(MatHang).where(MatHang.id == item_id)
                .values(so_luong_dang_giu=MatHang.so_luong_dang_giu - quantity)
            )
        if reservations:
            await self.session.execute(
                update(GiuHang).where(GiuHang.id.in_([row.id for row in reservations]))
                .values(trang_thai="da_tra", ket_thuc_at=datetime.now(timezone.utc))
            )
        await self.session.flush()
        return reservations

    # UC-27 Xem nhu cầu bổ sung linh kiện — Main 2 đọc yêu cầu chờ theo D1 (specs/use_cases/production/UC-27.md)
    async def yeu_cau_cho_bo_sung(self) -> list[YeuCauRead]:
        records = (await self.session.scalars(
            select(YeuCauSanXuat)
            .where(YeuCauSanXuat.trang_thai == "cho_bo_sung_linh_kien")
            .order_by(YeuCauSanXuat.kiem_tra_lan_dau_at.asc(), YeuCauSanXuat.id.asc())
        )).all()
        return await self._requests(list(records))

    # UC-27 Xem nhu cầu bổ sung linh kiện — Main 2–3 đọc nhu cầu đã chốt theo lô (specs/use_cases/production/UC-27.md)
    async def nhu_cau_cua_cac_yeu_cau(self, ids: list[int]) -> dict[int, dict[int, int]]:
        rows = await self.session.execute(
            select(
                NhuCauLinhKien.yeu_cau_san_xuat_id,
                NhuCauLinhKien.mat_hang_id,
                NhuCauLinhKien.so_luong_can,
            )
            .where(NhuCauLinhKien.yeu_cau_san_xuat_id.in_(ids))
            .order_by(NhuCauLinhKien.yeu_cau_san_xuat_id, NhuCauLinhKien.mat_hang_id)
        )
        result: dict[int, dict[int, int]] = {}
        for request_id, item_id, quantity in rows:
            result.setdefault(request_id, {})[item_id] = quantity
        return result

    async def dinh_muc(self, bom_id: int) -> dict[int, int]:
        rows = await self.session.execute(
            select(ChiTietBom.mat_hang_id, ChiTietBom.so_luong)
            .where(ChiTietBom.bom_id == bom_id)
            .order_by(ChiTietBom.mat_hang_id)
        )
        return dict(rows.all())

    async def nhu_cau(self, yeu_cau_id: int) -> dict[int, int]:
        rows = await self.session.execute(
            select(NhuCauLinhKien.mat_hang_id, NhuCauLinhKien.so_luong_can)
            .where(NhuCauLinhKien.yeu_cau_san_xuat_id == yeu_cau_id)
            .order_by(NhuCauLinhKien.mat_hang_id)
        )
        return dict(rows.all())

    # UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 3, 6; A4 khóa trước khi đọc (specs/use_cases/production/UC-26.md)
    # UC-27 Xem nhu cầu bổ sung linh kiện — Main 2–3 đọc còn dùng được với lock=False (specs/use_cases/production/UC-27.md)
    async def kha_dung(self, mat_hang_ids: list[int], *, lock: bool) -> dict[int, HangKhaDung]:
        query = select(
            MatHang.id, MatHang.ma_mat_hang, MatHang.ten_mat_hang,
            MatHang.don_vi_tinh, MatHang.so_luong_con_dung,
        ).where(MatHang.id.in_(mat_hang_ids)).order_by(MatHang.id)
        if lock:
            query = query.with_for_update()
        rows = await self.session.execute(query)
        return {
            row.id: HangKhaDung(
                row.ma_mat_hang, row.ten_mat_hang, row.don_vi_tinh, row.so_luong_con_dung,
            )
            for row in rows
        }

    # UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 6 chốt nhu cầu lần đầu (specs/use_cases/production/UC-26.md)
    async def ghi_nhu_cau(self, yeu_cau_id: int, quantities: dict[int, int]) -> None:
        self.session.add_all([
            NhuCauLinhKien(yeu_cau_san_xuat_id=yeu_cau_id, mat_hang_id=item_id, so_luong_can=quantity)
            for item_id, quantity in quantities.items()
        ])
        await self.session.flush()

    # UC-26 Kiểm tra yêu cầu sản xuất và giữ hàng — Main 7; A1–A3 giữ hàng cùng transaction (specs/use_cases/production/UC-26.md)
    async def giu_hang(self, yeu_cau_id: int, reservations: list[dict]) -> None:
        for reservation in reservations:
            self.session.add(GiuHang(yeu_cau_san_xuat_id=yeu_cau_id, **reservation))
            await self.session.execute(
                update(MatHang)
                .where(MatHang.id == reservation["mat_hang_id"])
                .values(so_luong_dang_giu=MatHang.so_luong_dang_giu + reservation["so_luong"])
            )
        await self.session.flush()

    async def _requests(self, records: list[YeuCauSanXuat]) -> list[YeuCauRead]:
        return [YeuCauRead.model_validate(record) for record in records]

    # UC-25 Xem danh sách yêu cầu sản xuất — Main 2–3; A1, A3 (specs/use_cases/production/UC-25.md)
    async def list_entries(
        self, params: YeuCauListQuery, actor_id: int | None
    ) -> RecordPage[YeuCauRead]:
        query = select(YeuCauSanXuat)
        if params.trang_thai_cong_viec is not None:
            query = query.where(_work_status_expression() == params.trang_thai_cong_viec)
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
        if params.q and params.q.strip():
            needle = params.q.strip().replace("/", "//").replace("%", "/%").replace("_", "/_")
            query = query.join(MatHang, MatHang.id == YeuCauSanXuat.mat_hang_id)
            query = query.where(
                or_(
                    _search_text(YeuCauSanXuat.ma_yeu_cau_san_xuat).contains(_search_text(needle), escape="/"),
                    _search_text(MatHang.ten_mat_hang).contains(_search_text(needle), escape="/"),
                )
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
