"""Contract v3 ticket read, filtering and action payloads."""

import re
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta

INT_MAX = 2**31 - 1
TicketState = Literal["cho_xu_ly", "dang_xu_ly", "da_xu_ly"]


class TicketDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chi_tiet_phieu_nhap_id: int
    mat_hang_id: int
    so_luong_hieu_luc_truoc: int
    so_luong_de_nghi: int
    so_luong_bien_dong: int
    ton_kho_tai_thoi_diem: int


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_ticket: str
    phieu_nhap_id: int
    nguoi_tao_id: int
    mo_ta_loi: str
    trang_thai: TicketState
    nguoi_xu_ly_id: int | None
    ket_qua_xu_ly: str | None
    created_at: datetime
    closed_at: datetime | None
    chi_tiet: list[TicketDetailRead]

    @field_validator("created_at", "closed_at")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class TicketListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    trang_thai: TicketState | None = None
    phieu_nhap_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    nguoi_tao_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    nguoi_xu_ly_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_ticket", "-ma_ticket"] = (
        "-created_at"
    )

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def date_only(cls, value: object) -> object:
        if value is not None and not (isinstance(value, date) and not isinstance(value, datetime)):
            if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("Date must use YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def valid_dates(self) -> Self:
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay must not exceed den_ngay")
        if self.den_ngay == date.max:
            raise ValueError("den_ngay is outside supported range")
        return self


class TicketClaimInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TicketResolveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ket_qua_xu_ly: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class TicketResponse(BaseModel):
    data: TicketRead
    meta: ResponseMeta


class TicketListResponse(BaseModel):
    data: list[TicketRead]
    meta: ListResponseMeta


class TicketError(BaseModel):
    code: str
    message: str
    details: list


class TicketErrorResponse(BaseModel):
    error: TicketError
    meta: ResponseMeta
