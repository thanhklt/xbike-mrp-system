"""Hợp đồng báo cáo nhập-xuất-tồn theo kỳ giờ Việt Nam."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

KyBaoCao = Literal["thang", "quy", "nam"]
LoaiMatHang = Literal["linh_kien", "thanh_pham"]


class NhapXuatTonQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ky: KyBaoCao
    nam: int = Field(ge=2, le=9998)
    thang: int | None = Field(default=None, ge=1, le=12)
    quy: int | None = Field(default=None, ge=1, le=4)
    mat_hang_id: int | None = Field(default=None, gt=0)
    loai_mat_hang: LoaiMatHang | None = None

    @model_validator(mode="after")
    def valid_period(self) -> "NhapXuatTonQuery":
        if (self.ky == "thang") != (self.thang is not None):
            raise ValueError("thang bắt buộc và chỉ được gửi khi ky=thang")
        if (self.ky == "quy") != (self.quy is not None):
            raise ValueError("quy bắt buộc và chỉ được gửi khi ky=quy")
        return self


@dataclass(frozen=True)
class NhapXuatTonRow:
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    loai_mat_hang: str
    don_vi_tinh: str
    ton_dau_ky: int
    nhap_trong_ky: int
    xuat_trong_ky: int
    ton_cuoi_ky: int


class NhapXuatTonDong(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    loai_mat_hang: LoaiMatHang
    don_vi_tinh: str
    ton_dau_ky: int
    nhap_trong_ky: int
    xuat_trong_ky: int
    ton_cuoi_ky: int


class NhapXuatTonData(BaseModel):
    ky: KyBaoCao
    nam: int
    thang: int | None
    quy: int | None
    tu_thoi_diem: datetime
    den_thoi_diem: datetime
    mat_hang: list[NhapXuatTonDong]


class NhapXuatTonResponse(BaseModel):
    success: Literal[True] = True
    data: NhapXuatTonData
    message: str = "Lấy báo cáo nhập-xuất-tồn thành công"


LoaiGiaoDich = Literal[
    "nhap_linh_kien", "xuat_linh_kien", "nhap_san_pham_san_xuat", "xuat_thanh_pham"
]
LoaiChungTu = Literal["phieu_nhap", "phieu_xuat", "chung_tu_hoan_thanh_sx"]


def _exact_date(value: object) -> object:
    if value is None or type(value) is date:
        return value
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("Expected YYYY-MM-DD")
    return value


class BienDongKhoQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int | None = Field(default=None, gt=0)
    loai_giao_dich: LoaiGiaoDich | None = None
    nhan_vien_id: int | None = Field(default=None, gt=0)
    tu_ngay: Annotated[date | None, BeforeValidator(_exact_date)] = None
    den_ngay: Annotated[date | None, BeforeValidator(_exact_date)] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def valid_date_range(self) -> "BienDongKhoQuery":
        if self.tu_ngay == date.min:
            raise ValueError("tu_ngay cannot be the minimum date: UTC conversion would overflow")
        if self.den_ngay == date.max:
            raise ValueError("den_ngay cannot be the maximum date")
        if self.tu_ngay is not None and self.den_ngay is not None and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay must not be after den_ngay")
        return self


@dataclass(frozen=True)
class BienDongKhoRow:
    id: int
    posted_at: datetime
    loai_giao_dich: LoaiGiaoDich
    so_luong_bien_dong: int
    so_luong_ton_sau: int
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    chung_tu_loai: LoaiChungTu
    chung_tu_id: int
    chung_tu_ma: str
    nhan_vien_id: int
    ma_nhan_vien: str
    ho_ten: str | None


class MatHangTomTat(BaseModel):
    id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str


class ChungTuGoc(BaseModel):
    loai: LoaiChungTu
    id: int
    ma: str


class NhanVienTomTat(BaseModel):
    id: int
    ma_nhan_vien: str
    ho_ten: str | None


class BienDongKhoDong(BaseModel):
    id: int
    posted_at: datetime
    loai_giao_dich: LoaiGiaoDich
    so_luong_bien_dong: int
    so_luong_ton_sau: int
    mat_hang: MatHangTomTat
    chung_tu: ChungTuGoc
    nhan_vien: NhanVienTomTat
