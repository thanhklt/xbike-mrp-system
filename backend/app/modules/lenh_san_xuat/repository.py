"""PostgreSQL adapter; table casing follows project decisions, columns follow model v2.

The v2 source-adjustment relation is required. Never fall back to stock balances
or silently ignore adjustments on an older database.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lenh_san_xuat.schemas import LenhListQuery, LenhRead, VatTuLenhRead, VatTuRead
from app.shared.records import RecordPage

# A source is counted once; only posted adjustments linked to that source change it.
_EFFECTIVE = """
WITH effective AS (
 SELECT g.*, g.so_luong_bien_dong + COALESCE((
   SELECT SUM(a.so_luong_bien_dong)
   FROM "ChiTietPhieuDieuChinhKho" d
   JOIN "PhieuDieuChinhKho" p ON p.id = d.phieu_dieu_chinh_kho_id
   JOIN "GiaoDichKho" a ON a.chi_tiet_phieu_dieu_chinh_id = d.id
   WHERE d.giao_dich_goc_id = g.id AND p.trang_thai = 'da_duyet'
     AND a.loai_giao_dich = 'dieu_chinh_ton_kho' AND a.mat_hang_id = g.mat_hang_id
 ), 0) AS quantity
 FROM "GiaoDichKho" g WHERE g.loai_giao_dich <> 'dieu_chinh_ton_kho'
)
"""


class SqlAlchemyLenhSanXuatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _rows(self, sql: str, params: dict | None = None):
        return (await self.session.execute(text(sql), params or {})).mappings().all()

    async def list_orders(self, query: LenhListQuery) -> RecordPage[LenhRead]:
        predicates, params = [], {}
        for name in (
            "yeu_cau_san_xuat_id",
            "lenh_san_xuat_cha_id",
            "nhan_vien_id",
            "mat_hang_id",
            "trang_thai",
        ):
            value = getattr(query, name)
            if value is not None:
                predicates.append(f"{name} = :{name}")
                params[name] = value
        if query.q is not None:
            predicates.append("strpos(lower(ma_lenh_san_xuat), lower(:q)) > 0")
            params["q"] = query.q
        for name, operator in (("tu_ngay", ">="), ("den_ngay", "<=")):
            value = getattr(query, name)
            if value is not None:
                predicates.append(f"created_at {operator} :{name}")
                params[name] = value
        where = " WHERE " + " AND ".join(predicates) if predicates else ""
        total = await self.session.scalar(
            text('SELECT COUNT(*) FROM "LenhSanXuat"' + where), params
        )
        column = query.sort.removeprefix("-")
        direction = "DESC" if query.sort.startswith("-") else "ASC"
        rows = await self._rows(
            'SELECT id FROM "LenhSanXuat"'
            + where
            + f" ORDER BY {column} {direction}, id ASC LIMIT :limit OFFSET :offset",
            params | {"limit": query.page_size, "offset": (query.page - 1) * query.page_size},
        )
        orders = [await self.get_order(row["id"]) for row in rows]
        return RecordPage([order for order in orders if order is not None], total or 0)

    async def get_order(self, order_id: int) -> LenhRead | None:
        rows = await self._rows('SELECT * FROM "LenhSanXuat" WHERE id = :id', {"id": order_id})
        if not rows:
            return None
        order = dict(rows[0])
        order["nhu_cau_truc_tiep"] = await self._rows(
            'SELECT id, mat_hang_id, so_luong_can FROM "ChiTietLenhSanXuat" WHERE lenh_san_xuat_id = :id ORDER BY id',
            {"id": order_id},
        )
        children = await self._rows(
            'SELECT id FROM "LenhSanXuat" WHERE lenh_san_xuat_cha_id = :id ORDER BY id',
            {"id": order_id},
        )
        order["lenh_con_ids"] = [child["id"] for child in children]
        finished = await self.session.scalar(
            text(
                _EFFECTIVE
                + """
          SELECT COALESCE(SUM(g.quantity), 0) FROM effective g
          JOIN "ChungTuHoanThanhSx" c ON c.id = g.chung_tu_hoan_thanh_sx_id
          WHERE c.lenh_san_xuat_id = :id AND c.trang_thai = 'da_duyet'
            AND g.loai_giao_dich = 'nhap_san_pham_san_xuat'
        """
            ),
            {"id": order_id},
        )
        order["so_luong_da_hoan_thanh"] = int(finished or 0)
        order["so_luong_con_phai_hoan_thanh"] = max(order["so_luong"] - int(finished or 0), 0)
        return LenhRead.model_validate(order)

    async def lock_bom_graph(self) -> None:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(20261020, 2)"))

    async def lock_order(self, order_id: int) -> LenhRead | None:
        # Serialize parent/child changes within the same production request.
        await self.session.execute(
            text(
                'SELECT id FROM "YeuCauSanXuat" WHERE id = (SELECT yeu_cau_san_xuat_id FROM "LenhSanXuat" WHERE id = :id) FOR UPDATE'
            ),
            {"id": order_id},
        )
        await self.session.execute(
            text('SELECT id FROM "LenhSanXuat" WHERE id = :id FOR UPDATE'), {"id": order_id}
        )
        return await self.get_order(order_id)

    async def employee_active(self, employee_id: int) -> bool:
        rows = await self._rows(
            """SELECT id FROM "NhanVien" WHERE id = :id AND trang_thai = 'hoat_dong' FOR SHARE""",
            {"id": employee_id},
        )
        return bool(rows)

    async def request_active(self, request_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    """SELECT EXISTS(SELECT 1 FROM "YeuCauSanXuat" WHERE id = :id AND trang_thai NOT IN ('nhap', 'hoan_thanh', 'da_huy'))"""
                ),
                {"id": request_id},
            )
        )

    async def formula_matches(self, order: LenhRead) -> bool:
        active = await self.session.scalar(
            text(
                'SELECT EXISTS(SELECT 1 FROM "Bom" WHERE id = :id AND mat_hang_id = :item AND is_active)'
            ),
            {"id": order.bom_id, "item": order.mat_hang_id},
        )
        lines = await self._rows(
            'SELECT mat_hang_id, so_luong FROM "ChiTietBom" WHERE bom_id = :id',
            {"id": order.bom_id},
        )
        expected = {line["mat_hang_id"]: line["so_luong"] * order.so_luong for line in lines}
        actual = {line.mat_hang_id: line.so_luong_can for line in order.nhu_cau_truc_tiep}
        return bool(active and expected and expected == actual)

    async def materials(self, order: LenhRead) -> VatTuLenhRead:
        rows = await self._rows(
            _EFFECTIVE
            + """
          SELECT d.mat_hang_id, d.so_luong_can, m.so_luong_ton AS ton_hien_tai,
            COALESCE(issued.quantity, 0) AS so_luong_da_cap
          FROM "ChiTietLenhSanXuat" d JOIN "MatHang" m ON m.id = d.mat_hang_id
          LEFT JOIN (
            SELECT c.mat_hang_id, -SUM(g.quantity) AS quantity
            FROM effective g JOIN "ChiTietPhieuXuat" c ON c.id = g.chi_tiet_phieu_xuat_id
            JOIN "PhieuXuat" p ON p.id = c.phieu_xuat_id
            WHERE p.lenh_san_xuat_id = :id AND p.loai_phieu = 'xuat_vat_tu'
              AND p.trang_thai = 'da_duyet' AND g.loai_giao_dich = 'xuat_vat_tu'
            GROUP BY c.mat_hang_id
          ) issued ON issued.mat_hang_id = d.mat_hang_id
          WHERE d.lenh_san_xuat_id = :id ORDER BY d.id
        """,
            {"id": order.id},
        )
        lines = [
            VatTuRead(
                **dict(row),
                so_luong_con_phai_cap=max(row["so_luong_can"] - row["so_luong_da_cap"], 0),
            )
            for row in rows
        ]
        return VatTuLenhRead(
            lenh_san_xuat_id=order.id,
            chi_tiet=lines,
            du_dieu_kien_bat_dau=bool(lines)
            and all(line.so_luong_con_phai_cap == 0 for line in lines),
        )

    async def has_postings(self, order_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text("""
          SELECT EXISTS(SELECT 1 FROM "PhieuXuat" WHERE lenh_san_xuat_id = :id AND trang_thai = 'da_duyet')
          OR EXISTS(SELECT 1 FROM "ChungTuHoanThanhSx" WHERE lenh_san_xuat_id = :id AND trang_thai = 'da_duyet')
          OR EXISTS(SELECT 1 FROM "GiaoDichKho" g
            LEFT JOIN "ChiTietPhieuXuat" c ON c.id = g.chi_tiet_phieu_xuat_id
            LEFT JOIN "PhieuXuat" p ON p.id = c.phieu_xuat_id
            LEFT JOIN "ChungTuHoanThanhSx" h ON h.id = g.chung_tu_hoan_thanh_sx_id
            WHERE p.lenh_san_xuat_id = :id OR h.lenh_san_xuat_id = :id)
        """),
                {"id": order_id},
            )
        )

    async def has_active_children(self, order_id: int) -> bool:
        return bool(
            await self.session.scalar(
                text(
                    """SELECT EXISTS(SELECT 1 FROM "LenhSanXuat" WHERE lenh_san_xuat_cha_id = :id AND trang_thai <> 'da_huy')"""
                ),
                {"id": order_id},
            )
        )

    async def assign(self, order_id: int, employee_id: int) -> None:
        await self.session.execute(
            text('UPDATE "LenhSanXuat" SET nhan_vien_id = :employee WHERE id = :id'),
            {"employee": employee_id, "id": order_id},
        )

    async def transition(self, order_id: int, state: str) -> None:
        await self.session.execute(
            text("""UPDATE "LenhSanXuat" SET trang_thai = :state,
          started_at = CASE WHEN :state = 'dang_thuc_hien' THEN now() ELSE started_at END
          WHERE id = :id"""),
            {"id": order_id, "state": state},
        )
