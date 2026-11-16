"""Cổng đọc số liệu báo cáo; không có thao tác ghi."""

from datetime import datetime
from typing import Protocol

from app.modules.reporting.schemas import BienDongKhoRow, LoaiGiaoDich, LoaiMatHang, NhapXuatTonRow
from app.shared.records import RecordPage


class BaoCaoRepository(Protocol):
    async def bien_dong_kho(
        self,
        tu_utc: datetime | None,
        den_utc: datetime | None,
        mat_hang_id: int | None,
        loai_giao_dich: LoaiGiaoDich | None,
        nhan_vien_id: int | None,
        offset: int,
        limit: int,
    ) -> RecordPage[BienDongKhoRow]: ...

    async def nhap_xuat_ton(
        self,
        tu_utc: datetime,
        den_utc: datetime,
        mat_hang_id: int | None,
        loai_mat_hang: LoaiMatHang | None,
    ) -> list[NhapXuatTonRow]: ...
