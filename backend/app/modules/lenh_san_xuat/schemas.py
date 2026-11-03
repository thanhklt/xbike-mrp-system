"""Production-order contract supplied by the developer."""

from datetime import datetime, timezone
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TrangThai = Literal["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]


class LenhListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    yeu_cau_san_xuat_id: int | None = Field(default=None, gt=0)
    lenh_san_xuat_cha_id: int | None = Field(default=None, gt=0)
    nhan_vien_id: int | None = Field(default=None, gt=0)
    mat_hang_id: int | None = Field(default=None, gt=0)
    trang_thai: TrangThai | None = None
    tu_ngay: datetime | None = None
    den_ngay: datetime | None = None
    sort: Literal[
        "id", "-id", "created_at", "-created_at", "ma_lenh_san_xuat", "-ma_lenh_san_xuat"
    ] = "-created_at"

    @field_validator("tu_ngay", "den_ngay")
    @classmethod
    def normalize_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @model_validator(mode="after")
    def date_range(self):
        if self.tu_ngay and self.den_ngay:
            if (self.tu_ngay.tzinfo is None) != (self.den_ngay.tzinfo is None):
                raise ValueError("Hai mốc thời gian phải cùng định dạng múi giờ")
            if self.tu_ngay > self.den_ngay:
                raise ValueError("tu_ngay phải nhỏ hơn hoặc bằng den_ngay")
        return self


class NguoiThucHienInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nhan_vien_id: int = Field(gt=0, le=2147483647)


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ly_do: str = Field(min_length=3)


class NhuCauRead(BaseModel):
    id: int
    mat_hang_id: int
    so_luong_can: int


class LenhRead(BaseModel):
    id: int
    ma_lenh_san_xuat: str
    yeu_cau_san_xuat_id: int
    lenh_san_xuat_cha_id: int | None
    mat_hang_id: int
    bom_id: int
    so_luong: int
    nhan_vien_id: int | None
    trang_thai: TrangThai
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    nhu_cau_truc_tiep: list[NhuCauRead]
    so_luong_da_hoan_thanh: int
    so_luong_con_phai_hoan_thanh: int
    lenh_con_ids: list[int]


class VatTuRead(BaseModel):
    mat_hang_id: int
    so_luong_can: int
    so_luong_da_cap: int
    so_luong_con_phai_cap: int
    ton_hien_tai: int


class VatTuLenhRead(BaseModel):
    lenh_san_xuat_id: int
    du_dieu_kien_bat_dau: bool
    chi_tiet: list[VatTuRead]


class ResponseMeta(BaseModel):
    request_id: str


class ListMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


T = TypeVar("T")


class DetailResponse(BaseModel, Generic[T]):
    data: T
    meta: ResponseMeta


class LenhListResponse(BaseModel):
    data: list[LenhRead]
    meta: ListMeta


class LenhError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class LenhErrorResponse(BaseModel):
    error: LenhError
    meta: ResponseMeta
