"""Cổng đọc số liệu báo cáo; không có thao tác ghi."""

from datetime import datetime
from typing import Protocol

from app.modules.reporting.schemas import LoaiMatHang, NhapXuatTonRow


class BaoCaoRepository(Protocol):
    async def nhap_xuat_ton(
        self,
        tu_utc: datetime,
        den_utc: datetime,
        mat_hang_id: int | None,
        loai_mat_hang: LoaiMatHang | None,
    ) -> list[NhapXuatTonRow]: ...
