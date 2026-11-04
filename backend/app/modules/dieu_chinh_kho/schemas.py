"""Contract v3 adjustment and ticket payloads, resources and filtering."""

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


class PhieuDieuChinhError(TicketError):
    phieu_dieu_chinh_kho_id: int | None = None
    trang_thai_phieu: Literal["loi"] | None = None
    ticket_id: int | None = None
    ticket_da_luu: Literal[True] | None = None


class ErrorResponse(BaseModel):
    error: PhieuDieuChinhError
    meta: ResponseMeta


class DongDieuChinhCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    giao_dich_goc_id: int = Field(strict=True, gt=0, le=INT_MAX)
    so_luong_dung: int = Field(strict=True, ge=0, le=INT_MAX)


Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PhieuDieuChinhCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phieu_nhap_id: int = Field(strict=True, gt=0, le=INT_MAX)
    ly_do: Reason
    chi_tiet: list[DongDieuChinhCreate] = Field(min_length=1)

    @field_validator("chi_tiet")
    @classmethod
    def unique_sources(cls, value: list[DongDieuChinhCreate]) -> list[DongDieuChinhCreate]:
        if len({line.giao_dich_goc_id for line in value}) != len(value):
            raise ValueError("Không được trùng giao_dich_goc_id")
        return value


class PhieuDieuChinhPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ly_do: Reason | None = None
    chi_tiet: list[DongDieuChinhCreate] | None = Field(default=None, min_length=1)

    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if isinstance(value, dict) and any(v is None for v in value.values()):
            raise ValueError("Trường bắt buộc không nhận null")
        return value

    @field_validator("chi_tiet")
    @classmethod
    def unique_sources(
        cls, value: list[DongDieuChinhCreate] | None
    ) -> list[DongDieuChinhCreate] | None:
        return PhieuDieuChinhCreate.unique_sources(value) if value is not None else None


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DongDieuChinhRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    giao_dich_goc_id: int
    so_luong_hieu_luc_truoc: int
    so_luong_dung: int
    so_luong_bien_dong: int


class PhieuDieuChinhRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu: str
    phieu_nhap_id: int
    nhan_vien_id: int
    ly_do: str
    trang_thai: Literal["nhap", "da_xac_nhan", "loi"]
    created_at: datetime
    confirmed_at: datetime | None
    chi_tiet: list[DongDieuChinhRead]

    @field_validator("created_at", "confirmed_at")
    @classmethod
    def utc_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class PhieuDieuChinhActionRead(PhieuDieuChinhRead):
    giao_dich_kho_ids: list[int]
    da_ghi_so_truoc_do: bool


class PhieuDieuChinhResponse(BaseModel):
    data: PhieuDieuChinhRead
    meta: ResponseMeta


class PhieuDieuChinhActionResponse(BaseModel):
    data: PhieuDieuChinhActionRead
    meta: ResponseMeta


class PhieuDieuChinhListResponse(BaseModel):
    data: list[PhieuDieuChinhRead]
    meta: ListResponseMeta


class PhieuDieuChinhQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    trang_thai: Literal["nhap", "da_xac_nhan", "loi"] | None = None
    phieu_nhap_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    nhan_vien_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_phieu", "-ma_phieu"] = "-created_at"

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def date_only(cls, value: object) -> object:
        return TicketListQuery.date_only(value)

    @model_validator(mode="after")
    def valid_dates(self) -> Self:
        TicketListQuery.valid_dates(self)
        return self
