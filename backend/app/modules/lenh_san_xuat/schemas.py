"""Contract v3 §9 order inputs, frozen demand and response envelopes."""

from datetime import date, datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

LenhStatus = Literal["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]


class LenhPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nhan_vien_id: int | None = Field(..., gt=0, le=2**31 - 1, strict=True)


class LenhEmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ly_do: str = Field(min_length=1)


class LenhQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    yeu_cau_san_xuat_id: int | None = Field(default=None, gt=0, le=2**31 - 1)
    lenh_san_xuat_cha_id: int | None = Field(default=None, gt=0, le=2**31 - 1)
    nhan_vien_id: int | None = Field(default=None, gt=0, le=2**31 - 1)
    mat_hang_id: int | None = Field(default=None, gt=0, le=2**31 - 1)
    trang_thai: LenhStatus | None = None
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: Literal[
        "id", "-id", "created_at", "-created_at", "ma_lenh_san_xuat", "-ma_lenh_san_xuat"
    ] = "-created_at"

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def exact_date(cls, value: object) -> date | None:
        if value is None:
            return None
        if type(value) is date:
            return value
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        raise ValueError("Ngày phải có dạng YYYY-MM-DD")

    @model_validator(mode="after")
    def date_range(self) -> Self:
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay phải nhỏ hơn hoặc bằng den_ngay")
        if self.den_ngay == date.max:
            raise ValueError("den_ngay vượt giới hạn hỗ trợ")
        return self


class NhuCauRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mat_hang_id: int
    so_luong_can: int
    id: int


class LenhRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_lenh_san_xuat: str
    yeu_cau_san_xuat_id: int
    lenh_san_xuat_cha_id: int | None
    mat_hang_id: int
    bom_id: int
    so_luong: int
    nhan_vien_id: int | None
    trang_thai: LenhStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    nhu_cau_truc_tiep: list[NhuCauRead] = Field(default_factory=list)
    so_luong_da_hoan_thanh: int = 0
    so_luong_con_phai_hoan_thanh: int = 0
    lenh_con_ids: list[int] = Field(default_factory=list)


class VatTuLenhLine(BaseModel):
    mat_hang_id: int
    so_luong_can: int
    so_luong_da_cap: int
    so_luong_con_phai_cap: int
    ton_hien_tai: int


class VatTuLenhRead(BaseModel):
    lenh_san_xuat_id: int
    du_dieu_kien_bat_dau: bool
    chi_tiet: list[VatTuLenhLine]


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class LenhResponse(BaseModel):
    data: LenhRead
    meta: ResponseMeta


class LenhListResponse(BaseModel):
    data: list[LenhRead]
    meta: ListResponseMeta


class VatTuLenhResponse(BaseModel):
    data: VatTuLenhRead
    meta: ResponseMeta


class LenhError(BaseModel):
    code: str
    message: str
    details: list[dict[str, object]]


class LenhErrorResponse(BaseModel):
    error: LenhError
    meta: ResponseMeta
