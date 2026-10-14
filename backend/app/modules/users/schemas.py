"""Request parameters and response bodies for the two employee GET endpoints."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class NhanVienListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    sort: EmployeeSort = "id"
    vai_tro_id: int | None = Field(default=None, gt=0)
    trang_thai: EmployeeStatus | None = None


class NhanVienAssignmentRead(BaseModel):
    """Limited projection for managers assigning work."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    ma_nhan_vien: str
    ho_ten: str | None
    vai_tro_id: int | None
    ma_vai_tro: RoleCode | None
    trang_thai: EmployeeStatus


class NhanVienRead(NhanVienAssignmentRead):
    ten_dang_nhap: str
    ngay_sinh: date | None
    so_dien_thoai: str | None
    email: str | None
    ngay_vao_lam: date | None
    he_so_luong: Decimal | None = Field(ge=0)


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class NhanVienDetailResponse(BaseModel):
    data: NhanVienRead | NhanVienAssignmentRead
    meta: ResponseMeta


class NhanVienListResponse(BaseModel):
    data: list[NhanVienRead | NhanVienAssignmentRead]
    meta: ListResponseMeta
