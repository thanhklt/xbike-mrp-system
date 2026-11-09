"""Traffic statistics contract for GET /api/v1/luu_luong_truy_cap."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

KhoangThoiGian = Literal["hom_nay", "7_ngay", "30_ngay"]
Buoc = Literal["gio", "ngay"]


class DiemLuuLuong(BaseModel):
    bat_dau: datetime
    so_request: int | None
    trung_binh_7_ngay: float | None


class LuuLuongRead(BaseModel):
    khoang_thoi_gian: KhoangThoiGian
    buoc: Buoc
    timezone: str
    tu_thoi_diem: datetime
    den_thoi_diem_exclusive: datetime
    tong_request: int
    diem: list[DiemLuuLuong]


class ResponseMeta(BaseModel):
    request_id: str


class LuuLuongResponse(BaseModel):
    data: LuuLuongRead
    meta: ResponseMeta
