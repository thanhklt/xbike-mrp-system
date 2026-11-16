"""Đọc bảng v4 trực tiếp, độc lập ORM inventory cũ."""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.schemas import BienDongKhoRow, LoaiGiaoDich, LoaiMatHang, NhapXuatTonRow
from app.shared.records import RecordPage


class SqlAlchemyBaoCaoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # UC-42 Tra cứu lịch sử biến động kho — Main 2–4; R1–R3, A1 (specs/use_cases/reporting/UC-42.md)
    async def bien_dong_kho(
        self,
        tu_utc: datetime | None,
        den_utc: datetime | None,
        mat_hang_id: int | None,
        loai_giao_dich: LoaiGiaoDich | None,
        nhan_vien_id: int | None,
        offset: int,
        limit: int,
    ) -> RecordPage[BienDongKhoRow]:
        params = {
            "tu_utc": tu_utc, "den_utc": den_utc, "mat_hang_id": mat_hang_id,
            "loai_giao_dich": loai_giao_dich, "nhan_vien_id": nhan_vien_id,
        }
        result = await self.session.execute(text('''
            SELECT g.id, g.posted_at, g.loai_giao_dich,
                   g.so_luong_bien_dong, g.so_luong_ton_sau, g.mat_hang_id,
                   m.ma_mat_hang, m.ten_mat_hang, m.don_vi_tinh,
                   CASE WHEN g.chi_tiet_phieu_nhap_id IS NOT NULL THEN 'phieu_nhap'
                        WHEN g.chi_tiet_phieu_xuat_id IS NOT NULL THEN 'phieu_xuat'
                        ELSE 'chung_tu_hoan_thanh_sx' END AS chung_tu_loai,
                   COALESCE(pn.id, px.id, ht.id) AS chung_tu_id,
                   COALESCE(pn.ma_phieu_nhap, px.ma_phieu_xuat, ht.ma_phieu) AS chung_tu_ma,
                   g.nhan_vien_id, nv.ma_nhan_vien, nv.ho_ten
            FROM "GiaoDichKho" g
            LEFT JOIN "MatHang" m ON m.id = g.mat_hang_id
            LEFT JOIN "NhanVien" nv ON nv.id = g.nhan_vien_id
            LEFT JOIN "ChiTietPhieuNhap" cn ON cn.id = g.chi_tiet_phieu_nhap_id
            LEFT JOIN "PhieuNhap" pn ON pn.id = cn.phieu_nhap_id
            LEFT JOIN "ChiTietPhieuXuat" cx ON cx.id = g.chi_tiet_phieu_xuat_id
            LEFT JOIN "PhieuXuat" px ON px.id = cx.phieu_xuat_id
            LEFT JOIN "ChungTuHoanThanhSx" ht ON ht.id = g.chung_tu_hoan_thanh_sx_id
            WHERE (CAST(:tu_utc AS timestamptz) IS NULL OR g.posted_at >= :tu_utc)
              AND (CAST(:den_utc AS timestamptz) IS NULL OR g.posted_at < :den_utc)
              AND (CAST(:mat_hang_id AS numeric) IS NULL OR g.mat_hang_id = :mat_hang_id)
              AND (CAST(:loai_giao_dich AS text) IS NULL OR g.loai_giao_dich = :loai_giao_dich)
              AND (CAST(:nhan_vien_id AS numeric) IS NULL OR g.nhan_vien_id = :nhan_vien_id)
            ORDER BY g.posted_at DESC, g.id DESC LIMIT :limit OFFSET :offset
        '''), {**params, "offset": offset, "limit": limit})
        rows = [BienDongKhoRow(**row) for row in result.mappings()]
        count = await self.session.execute(text('''
            SELECT COUNT(*) FROM "GiaoDichKho" g
            WHERE (CAST(:tu_utc AS timestamptz) IS NULL OR g.posted_at >= :tu_utc)
              AND (CAST(:den_utc AS timestamptz) IS NULL OR g.posted_at < :den_utc)
              AND (CAST(:mat_hang_id AS numeric) IS NULL OR g.mat_hang_id = :mat_hang_id)
              AND (CAST(:loai_giao_dich AS text) IS NULL OR g.loai_giao_dich = :loai_giao_dich)
              AND (CAST(:nhan_vien_id AS numeric) IS NULL OR g.nhan_vien_id = :nhan_vien_id)
        '''), params)
        return RecordPage(rows, count.scalar_one())

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
