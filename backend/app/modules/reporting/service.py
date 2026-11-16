"""Tính biên kỳ địa phương và tổng hợp dữ liệu qua cổng chỉ đọc."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.modules.reporting.ports import BaoCaoRepository
from app.modules.reporting.schemas import (
    BienDongKhoDong,
    BienDongKhoQuery,
    ChungTuGoc,
    KyBaoCao,
    MatHangTomTat,
    NhanVienTomTat,
    NhapXuatTonData,
    NhapXuatTonDong,
    NhapXuatTonQuery,
    NhapXuatTonResponse,
)
from app.shared.pagination import PaginatedResponse, create_paginated_response

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


# UC-41 Xem báo cáo nhập-xuất-tồn — Main 3; R1, R4 (specs/use_cases/reporting/UC-41.md)
def bien_ky(
    ky: KyBaoCao, nam: int, thang: int | None = None, quy: int | None = None
) -> tuple[datetime, datetime]:
    params = NhapXuatTonQuery(ky=ky, nam=nam, thang=thang, quy=quy)
    month = params.thang if ky == "thang" else (3 * params.quy - 2 if ky == "quy" else 1)
    months = 1 if ky == "thang" else (3 if ky == "quy" else 12)
    end_year, end_month = divmod(nam * 12 + month - 1 + months, 12)
    return (
        datetime(nam, month, 1, tzinfo=LOCAL_TZ),
        datetime(end_year, end_month + 1, 1, tzinfo=LOCAL_TZ),
    )


# UC-42 Tra cứu lịch sử biến động kho — Main 3–4; R3 (specs/use_cases/reporting/UC-42.md)
def bien_ngay(tu_ngay: date | None, den_ngay: date | None) -> tuple[datetime | None, datetime | None]:
    params = BienDongKhoQuery(tu_ngay=tu_ngay, den_ngay=den_ngay)
    return (
        datetime.combine(params.tu_ngay, time.min, LOCAL_TZ).astimezone(timezone.utc)
        if params.tu_ngay is not None else None,
        datetime.combine(params.den_ngay + timedelta(days=1), time.min, LOCAL_TZ).astimezone(timezone.utc)
        if params.den_ngay is not None else None,
    )


class BaoCaoService:
    def __init__(self, repository: BaoCaoRepository):
        self.repository = repository

    # UC-42 Tra cứu lịch sử biến động kho — Main 2–4; R1–R3, A1 (specs/use_cases/reporting/UC-42.md)
    async def bien_dong_kho(self, query: BienDongKhoQuery) -> PaginatedResponse[BienDongKhoDong]:
        tu, den = bien_ngay(query.tu_ngay, query.den_ngay)
        result = await self.repository.bien_dong_kho(
            tu, den, query.mat_hang_id, query.loai_giao_dich, query.nhan_vien_id,
            (query.page - 1) * query.page_size, query.page_size,
        )
        rows = [BienDongKhoDong(
            id=row.id, posted_at=row.posted_at, loai_giao_dich=row.loai_giao_dich,
            so_luong_bien_dong=row.so_luong_bien_dong, so_luong_ton_sau=row.so_luong_ton_sau,
            mat_hang=MatHangTomTat(
                id=row.mat_hang_id, ma_mat_hang=row.ma_mat_hang,
                ten_mat_hang=row.ten_mat_hang, don_vi_tinh=row.don_vi_tinh,
            ),
            chung_tu=ChungTuGoc(loai=row.chung_tu_loai, id=row.chung_tu_id, ma=row.chung_tu_ma),
            nhan_vien=NhanVienTomTat(
                id=row.nhan_vien_id, ma_nhan_vien=row.ma_nhan_vien, ho_ten=row.ho_ten,
            ),
        ) for row in result.items]
        return create_paginated_response(rows, result.total, query.page, query.page_size)

    # UC-41 Xem báo cáo nhập-xuất-tồn — Main 2–4; R1–R5, A1, A2 (specs/use_cases/reporting/UC-41.md)
    async def nhap_xuat_ton(self, query: NhapXuatTonQuery) -> NhapXuatTonResponse:
        tu, den = bien_ky(query.ky, query.nam, query.thang, query.quy)
        rows = await self.repository.nhap_xuat_ton(
            tu.astimezone(timezone.utc),
            den.astimezone(timezone.utc),
            query.mat_hang_id,
            query.loai_mat_hang,
        )
        return NhapXuatTonResponse(
            data=NhapXuatTonData(
                ky=query.ky,
                nam=query.nam,
                thang=query.thang,
                quy=query.quy,
                tu_thoi_diem=tu,
                den_thoi_diem=den,
                mat_hang=[NhapXuatTonDong.model_validate(row) for row in rows],
            )
        )
