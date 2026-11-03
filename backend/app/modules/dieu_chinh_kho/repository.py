"""Parameterized PostgreSQL queries against the v3.1 tables.

Use explicit SQL here so receipt corrections do not depend on legacy inventory ORM.
The caller owns all transactions, including audit writes.
"""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dieu_chinh_kho.schemas import DieuChinhQuery


class SqlAlchemyDieuChinhRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def rows(self, sql: str, **params) -> list[dict]:
        result = await self.session.execute(text(sql), params)
        return [dict(row) for row in result.mappings()]

    async def execute(self, sql: str, **params):
        return await self.session.execute(text(sql), params)

    async def get(self, id: int) -> dict | None:
        rows = await self.rows('SELECT * FROM "PhieuDieuChinhKho" WHERE id=:id', id=id)
        if not rows:
            return None
        record = rows[0]
        record["chi_tiet"] = await self.rows(
            "SELECT id,mat_hang_id,giao_dich_goc_id,so_luong_hieu_luc_truoc,so_luong_dung,so_luong_bien_dong "
            'FROM "ChiTietPhieuDieuChinhKho" WHERE phieu_dieu_chinh_kho_id=:id ORDER BY id',
            id=id,
        )
        return record

    async def lock(self, id: int) -> dict | None:
        # Serialize every correction mutation. Shared source is locked before the document.
        # The advisory lock also covers a concurrent PATCH replacing its lines.
        await self.execute("SELECT pg_advisory_xact_lock(73421)")
        records = await self.rows(
            'SELECT phieu_nhap_id FROM "PhieuDieuChinhKho" WHERE id=:id', id=id
        )
        if records:
            await self.lock_receipt(records[0]["phieu_nhap_id"])
            await self.execute('SELECT id FROM "PhieuDieuChinhKho" WHERE id=:id FOR UPDATE', id=id)
        return await self.get(id)

    async def lock_receipt(self, id: int) -> dict | None:
        records = await self.rows('SELECT * FROM "PhieuNhap" WHERE id=:id FOR UPDATE', id=id)
        return records[0] if records else None

    async def list(self, query: DieuChinhQuery) -> tuple[list[dict], int]:
        conditions, params = [], {}
        for name in ("trang_thai", "nhan_vien_id"):
            value = getattr(query, name)
            if value is not None:
                conditions.append(f'"{name}"=:{name}')
                params[name] = value
        if query.q:
            conditions.append("ma_phieu ILIKE :q")
            params["q"] = f"%{query.q}%"
        for name, operator, extra in (("tu_ngay", ">=", 0), ("den_ngay", "<", 1)):
            value = getattr(query, name)
            if value:
                conditions.append(f"created_at {operator} :{name}")
                params[name] = datetime.combine(
                    value + timedelta(days=extra), time.min, ZoneInfo("Asia/Ho_Chi_Minh")
                ).astimezone(timezone.utc)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        total = (
            await self.rows('SELECT count(*) AS total FROM "PhieuDieuChinhKho"' + where, **params)
        )[0]["total"]
        column = query.sort.lstrip("-")
        direction = "DESC" if query.sort.startswith("-") else "ASC"
        records = await self.rows(
            'SELECT id FROM "PhieuDieuChinhKho"'
            + where
            + f' ORDER BY "{column}" {direction}, id {direction} LIMIT :limit OFFSET :offset',
            **params,
            limit=query.page_size,
            offset=(query.page - 1) * query.page_size,
        )
        return [await self.get(row["id"]) for row in records], total

    async def source(self, source_id: int, receipt_id: int) -> dict | None:
        rows = await self.rows(
            "SELECT g.id AS giao_dich_goc_id,g.mat_hang_id,n.id AS chi_tiet_phieu_nhap_id, "
            "g.so_luong_bien_dong + COALESCE((SELECT sum(c.so_luong_bien_dong) "
            'FROM "ChiTietPhieuDieuChinhKho" c JOIN "GiaoDichKho" a ON a.chi_tiet_phieu_dieu_chinh_id=c.id '
            "WHERE c.giao_dich_goc_id=g.id),0) AS so_luong_hieu_luc_truoc "
            'FROM "GiaoDichKho" g JOIN "ChiTietPhieuNhap" n ON n.id=g.chi_tiet_phieu_nhap_id '
            'JOIN "MatHang" m ON m.id=g.mat_hang_id '
            "WHERE g.id=:id AND n.phieu_nhap_id=:receipt AND g.loai_giao_dich='nhap_vat_tu' "
            "AND m.loai_mat_hang IN ('nguyen_vat_lieu','linh_kien') AND n.mat_hang_id=g.mat_hang_id",
            id=source_id,
            receipt=receipt_id,
        )
        return rows[0] if rows else None

    async def stock(self, ids: list[int]) -> dict[int, int]:
        stocks = {}
        for id in sorted(set(ids)):
            rows = await self.rows(
                'SELECT so_luong_ton FROM "MatHang" WHERE id=:id FOR UPDATE', id=id
            )
            if rows:
                stocks[id] = rows[0]["so_luong_ton"]
        return stocks

    async def next_code(self, table: str, column: str, prefix: str) -> str:
        if (table, column, prefix) not in {
            ("PhieuDieuChinhKho", "ma_phieu", "DCK"),
            ("TicketLoiDieuChinh", "ma_ticket", "TKDC"),
        }:
            raise ValueError("Unsupported document sequence")
        month = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m")
        rows = await self.rows(
            "SELECT nextval(pg_get_serial_sequence(:table,'id')) AS number", table='"' + table + '"'
        )
        number = rows[0]["number"]
        if number > 999999:
            raise ValueError("Đã hết dải mã chứng từ")
        return f"{prefix}-{month}-{number:06d}"

    async def replace_lines(self, id: int, lines: list[dict]) -> None:
        await self.execute(
            'DELETE FROM "ChiTietPhieuDieuChinhKho" WHERE phieu_dieu_chinh_kho_id=:id', id=id
        )
        for line in lines:
            await self.execute(
                'INSERT INTO "ChiTietPhieuDieuChinhKho" (phieu_dieu_chinh_kho_id,mat_hang_id,giao_dich_goc_id,so_luong_hieu_luc_truoc,so_luong_dung,so_luong_bien_dong) '
                "VALUES (:id,:mat_hang_id,:giao_dich_goc_id,:so_luong_hieu_luc_truoc,:so_luong_dung,:so_luong_bien_dong)",
                id=id,
                **{
                    key: line[key]
                    for key in (
                        "mat_hang_id",
                        "giao_dich_goc_id",
                        "so_luong_hieu_luc_truoc",
                        "so_luong_dung",
                        "so_luong_bien_dong",
                    )
                },
            )

    async def ledger_ids(self, id: int) -> list[int]:
        return [
            row["id"]
            for row in await self.rows(
                'SELECT g.id FROM "GiaoDichKho" g JOIN "ChiTietPhieuDieuChinhKho" c ON c.id=g.chi_tiet_phieu_dieu_chinh_id WHERE c.phieu_dieu_chinh_kho_id=:id ORDER BY g.id',
                id=id,
            )
        ]

    async def serialize(self, **params):
        return await self.execute("SELECT pg_advisory_xact_lock(73421)", **params)

    async def create_header(self, **params):
        return await self.rows(
            'INSERT INTO "PhieuDieuChinhKho" (ma_phieu,phieu_nhap_id,nhan_vien_id,ly_do) VALUES (:code,:receipt,:actor,:reason) RETURNING id',
            **params,
        )

    async def mark_approved(self, **params):
        return await self.execute(
            "UPDATE \"PhieuDieuChinhKho\" SET trang_thai='da_duyet', confirmed_at=now() WHERE id=:id",
            **params,
        )

    async def create_ticket(self, **params):
        return await self.rows(
            'INSERT INTO "TicketLoiDieuChinh" (ma_ticket,phieu_nhap_id,nguoi_tao_id,mo_ta_loi) VALUES (:code,:receipt,:actor,:message) RETURNING id',
            **params,
        )

    async def mark_failed(self, **params):
        return await self.execute(
            "UPDATE \"PhieuDieuChinhKho\" SET trang_thai='loi' WHERE id=:id", **params
        )

    async def update_stock(self, **params):
        return await self.execute(
            'UPDATE "MatHang" SET so_luong_ton=so_luong_ton+:delta,ton_kho_updated_at=now() WHERE id=:id',
            **params,
        )

    async def insert_movement(self, **params):
        return await self.execute(
            "INSERT INTO \"GiaoDichKho\" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chi_tiet_phieu_dieu_chinh_id,nhan_vien_id) VALUES (:item,'dieu_chinh_ton_kho',:delta,:line,:actor)",
            **params,
        )

    async def create_ticket_line(self, **params):
        return await self.execute(
            'INSERT INTO "ChiTietTicketLoiDieuChinh" (ticket_id,chi_tiet_phieu_nhap_id,mat_hang_id,so_luong_hieu_luc_truoc,so_luong_de_nghi,so_luong_bien_dong,ton_kho_tai_thoi_diem) VALUES (:ticket,:receipt_line,:item,:previous,:desired,:delta,:stock)',
            **params,
        )

    async def update_reason(self, **params):
        return await self.execute(
            'UPDATE "PhieuDieuChinhKho" SET ly_do=:reason WHERE id=:id', **params
        )

    async def delete_lines(self, **params):
        return await self.execute(
            'DELETE FROM "ChiTietPhieuDieuChinhKho" WHERE phieu_dieu_chinh_kho_id=:id', **params
        )

    async def delete_header(self, **params):
        return await self.execute('DELETE FROM "PhieuDieuChinhKho" WHERE id=:id', **params)

    async def update_state(self, **params):
        return await self.execute(
            'UPDATE "PhieuDieuChinhKho" SET trang_thai=:state WHERE id=:id', **params
        )

    async def actor(self, id: int) -> dict | None:
        records = await self.rows(
            'SELECT n.trang_thai,v.ma_vai_tro FROM "NhanVien" n JOIN "VaiTro" v ON v.id=n.vai_tro_id WHERE n.id=:id FOR SHARE OF n,v',
            id=id,
        )
        return records[0] if records else None
