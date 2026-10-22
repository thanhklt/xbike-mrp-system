"""Contract v2 employee/role requests and responses, including approved policy changes."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

EmployeeStatus = Literal["hoat_dong", "bi_khoa"]
RoleCode = Literal["nhan_vien", "quan_ly", "quan_tri_vien"]
EmployeeSort = Literal[
    "id",
    "-id",
    "ma_nhan_vien",
    "-ma_nhan_vien",
    "ho_ten",
    "-ho_ten",
    "ten_dang_nhap",
    "-ten_dang_nhap",
]


# Meta model
class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


# DanhSachNhanVien model
class DanhSachNhanVienRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    sort: EmployeeSort = "id"
    vai_tro_id: int | None = Field(default=None, gt=0)
    trang_thai: EmployeeStatus | None = None


class DanhSachNhanVienResponse(BaseModel):
    data: list[ChiTietNhanVien]
    meta: ListResponseMeta


# ChiTietNhanVien model
class ChiTietNhanVien(BaseModel):
    """Employee response; the service selects fields according to the caller's permissions."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    ma_nhan_vien: str
    ho_ten: str | None
    vai_tro_id: int | None
    ma_vai_tro: RoleCode | None
    trang_thai: EmployeeStatus
    ten_dang_nhap: str | None = None
    ngay_sinh: date | None = None
    so_dien_thoai: str | None = None
    email: str | None = None
    ngay_vao_lam: date | None = None
    he_so_luong: Decimal | None = Field(default=None, ge=0)


class ChiTietNhanVienResponse(BaseModel):
    data: ChiTietNhanVien
    meta: ResponseMeta


PositiveId = Annotated[int, Field(strict=True, gt=0, le=2**31 - 1)]
RequiredText = Annotated[str, Field(strict=True, min_length=1)]


class NhanVienPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ho_ten: str | None = None
    ngay_sinh: date | None = None
    so_dien_thoai: str | None = None
    email: str | None = None
    ngay_vao_lam: date | None = None
    he_so_luong: Decimal | None = Field(default=None, ge=0, max_digits=5, decimal_places=2)

    @field_validator("ngay_sinh", "ngay_vao_lam", mode="before")
    @classmethod
    def date_uses_contract_format(cls, value: object) -> object:
        if value is not None and (
            not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        ):
            raise ValueError("Date must use YYYY-MM-DD")
        return value

    @field_validator("he_so_luong", mode="before")
    @classmethod
    def salary_is_json_string(cls, value: object) -> object:
        if value is not None and not isinstance(value, str):
            raise ValueError("he_so_luong must be a decimal JSON string")
        return value


class NhanVienCreate(NhanVienPatch):
    ten_dang_nhap: RequiredText
    mat_khau: SecretStr = Field(min_length=8)
    ma_nhan_vien: RequiredText
    vai_tro_id: PositiveId


class DoiVaiTroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vai_tro_id: PositiveId


class VoHieuHoaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ly_do: RequiredText


class DanhSachVaiTroRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class VaiTroRead(BaseModel):
    id: int
    ma_vai_tro: RoleCode | None
    ten_vai_tro: str | None


class DanhSachVaiTroResponse(BaseModel):
    data: list[VaiTroRead]
    meta: ListResponseMeta
