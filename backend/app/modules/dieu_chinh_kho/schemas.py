"""HTTP contracts for receipt corrections."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DongDieuChinh(Input):
    giao_dich_goc_id: int = Field(gt=0, le=2147483647, strict=True)
    so_luong_dung: int = Field(ge=0, le=2147483647, strict=True)


class DieuChinhCreate(Input):
    phieu_nhap_id: int = Field(gt=0, le=2147483647, strict=True)
    ly_do: str = Field(min_length=1)
    chi_tiet: list[DongDieuChinh] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sources(self):
        if len({line.giao_dich_goc_id for line in self.chi_tiet}) != len(self.chi_tiet):
            raise ValueError("Giao dịch gốc không được trùng")
        return self


class DieuChinhPatch(Input):
    ly_do: str = Field(default=None, min_length=1)
    chi_tiet: list[DongDieuChinh] = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_patch(self):
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Trường được gửi không nhận null")
        if self.chi_tiet is not None and len({x.giao_dich_goc_id for x in self.chi_tiet}) != len(
            self.chi_tiet
        ):
            raise ValueError("Giao dịch gốc không được trùng")
        return self


class LyDoInput(Input):
    ly_do: str = Field(min_length=1)


class EmptyInput(Input):
    pass


class DieuChinhQuery(Input):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    q: str | None = None
    trang_thai: Literal["nhap", "cho_duyet", "da_duyet", "tu_choi", "loi"] | None = None
    nhan_vien_id: int | None = Field(None, gt=0)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_phieu", "-ma_phieu"] = "id"

    @model_validator(mode="after")
    def date_order(self):
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay phải trước hoặc bằng den_ngay")
        return self


class DongRead(BaseModel):
    id: int
    mat_hang_id: int
    giao_dich_goc_id: int
    so_luong_hieu_luc_truoc: int
    so_luong_dung: int
    so_luong_bien_dong: int


class DieuChinhRead(BaseModel):
    id: int
    ma_phieu: str
    phieu_nhap_id: int
    nhan_vien_id: int
    ly_do: str
    trang_thai: str
    created_at: datetime
    confirmed_at: datetime | None
    chi_tiet: list[DongRead]


class DieuChinhResponse(BaseModel):
    data: DieuChinhRead
    meta: dict
    giao_dich_kho_ids: list[int] | None = None
    da_ghi_so_truoc_do: bool | None = None


class DieuChinhListResponse(BaseModel):
    data: list[DieuChinhRead]
    meta: dict
