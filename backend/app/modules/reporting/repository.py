"""Đọc bảng v4 trực tiếp, độc lập ORM inventory cũ."""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.schemas import LoaiMatHang, NhapXuatTonRow


class SqlAlchemyBaoCaoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # UC-41 Xem báo cáo nhập-xuất-tồn — Main 3–4; R1, R3, R5, A1, A2 (specs/use_cases/reporting/UC-41.md)
    async def nhap_xuat_ton(
        self,
        tu_utc: datetime,
        den_utc: datetime,
        mat_hang_id: int | None,
        loai_mat_hang: LoaiMatHang | None,
    ) -> list[NhapXuatTonRow]:
        result = await self.session.execute(
            text('''
                SELECT m.id AS mat_hang_id, m.ma_mat_hang, m.ten_mat_hang,
                       m.loai_mat_hang, m.don_vi_tinh,
                       COALESCE(dau.so_luong_ton_sau, 0) AS ton_dau_ky,
                       COALESCE(ps.nhap, 0) AS nhap_trong_ky,
                       COALESCE(ps.xuat, 0) AS xuat_trong_ky,
                       COALESCE(cuoi.so_luong_ton_sau, 0) AS ton_cuoi_ky
                FROM "MatHang" m
                LEFT JOIN LATERAL (
                    SELECT g.so_luong_ton_sau FROM "GiaoDichKho" g
                    WHERE g.mat_hang_id = m.id AND g.posted_at < :tu_utc
                    ORDER BY g.posted_at DESC, g.id DESC LIMIT 1
                ) dau ON true
                LEFT JOIN LATERAL (
                    SELECT SUM(g.so_luong_bien_dong::bigint)
                               FILTER (WHERE g.so_luong_bien_dong > 0) AS nhap,
                           SUM(-g.so_luong_bien_dong::bigint)
                               FILTER (WHERE g.so_luong_bien_dong < 0) AS xuat
                    FROM "GiaoDichKho" g
                    WHERE g.mat_hang_id = m.id
                      AND g.posted_at >= :tu_utc AND g.posted_at < :den_utc
                ) ps ON true
                LEFT JOIN LATERAL (
                    SELECT g.so_luong_ton_sau FROM "GiaoDichKho" g
                    WHERE g.mat_hang_id = m.id AND g.posted_at < :den_utc
                    ORDER BY g.posted_at DESC, g.id DESC LIMIT 1
                ) cuoi ON true
                WHERE (CAST(:mat_hang_id AS numeric) IS NULL
                       OR m.id = CAST(:mat_hang_id AS numeric))
                  AND (CAST(:loai_mat_hang AS text) IS NULL OR m.loai_mat_hang = :loai_mat_hang)
                ORDER BY m.loai_mat_hang, m.ma_mat_hang
            '''),
            {
                "tu_utc": tu_utc,
                "den_utc": den_utc,
                "mat_hang_id": mat_hang_id,
                "loai_mat_hang": loai_mat_hang,
            },
        )
        return [NhapXuatTonRow(**row) for row in result.mappings()]
