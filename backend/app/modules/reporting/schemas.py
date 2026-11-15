"""Hợp đồng báo cáo nhập-xuất-tồn theo kỳ giờ Việt Nam."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
