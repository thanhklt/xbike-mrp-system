"""Tính biên kỳ địa phương và tổng hợp dữ liệu qua cổng chỉ đọc."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.modules.reporting.ports import BaoCaoRepository
from app.modules.reporting.schemas import (
    KyBaoCao,
    NhapXuatTonData,
    NhapXuatTonDong,
    NhapXuatTonQuery,
    NhapXuatTonResponse,
)

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


class BaoCaoService:
    def __init__(self, repository: BaoCaoRepository):
        self.repository = repository

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
