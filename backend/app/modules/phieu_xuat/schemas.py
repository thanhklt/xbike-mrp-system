"""Goods issue v4: source-only input and integer VND after posting."""

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
MONEY_MAX = 2**63 - 1
IssueId = Annotated[int, Field(strict=True, gt=0, le=INT_MAX)]
IssueMoney = Annotated[int, Field(strict=True, ge=0, le=MONEY_MAX)]
IssueType = Literal["xuat_linh_kien", "xuat_thanh_pham"]
IssueState = Literal["nhap", "cho_duyet", "da_duyet", "tu_choi"]


class ChiTietPhieuXuatCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mat_hang_id: IssueId
    so_luong: IssueId


class PhieuXuatCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loai_phieu: IssueType
    yeu_cau_san_xuat_id: IssueId


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ly_do: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ChiTietPhieuXuatRead(ChiTietPhieuXuatCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    don_gia_thuc: IssueMoney | None
    tong_gia: IssueMoney | None


class PhieuXuatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ma_phieu_xuat: str
    nhan_vien_id: int
    loai_phieu: IssueType
    yeu_cau_san_xuat_id: int
    tong_tien: IssueMoney | None
    trang_thai: IssueState
    created_at: datetime
    updated_at: datetime
    gui_at: datetime | None
    nguoi_xu_ly_id: int | None
    xu_ly_at: datetime | None
    ly_do_tu_choi: str | None
    phien_ban: int
    chi_tiet: list[ChiTietPhieuXuatRead]

    @field_validator("created_at", "updated_at", "gui_at", "xu_ly_at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(timezone.utc) if value is not None else None


class PhieuXuatResponse(BaseModel):
    data: PhieuXuatRead
    meta: ResponseMeta


class PhieuXuatReference(BaseModel):
    id: int
    ma_phieu_xuat: str
    loai_phieu: IssueType
    trang_thai: IssueState


class PhieuXuatSourceResponse(BaseModel):
    data: list[PhieuXuatReference]
    meta: ResponseMeta


class PhieuXuatPreviewQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loai_phieu: IssueType


class PhieuXuatPreviewRead(BaseModel):
    yeu_cau_san_xuat_id: int
    loai_phieu: IssueType
    chi_tiet: list[ChiTietPhieuXuatCreate]


class PhieuXuatPreviewResponse(BaseModel):
    data: PhieuXuatPreviewRead
    meta: ResponseMeta


class PhieuXuatListResponse(BaseModel):
    data: list[PhieuXuatRead]
    meta: ListResponseMeta


class PhieuXuatCuaToiRead(PhieuXuatRead):
    ma_yeu_cau_san_xuat: str | None


class PhieuXuatCuaToiListResponse(BaseModel):
    data: list[PhieuXuatCuaToiRead]
    meta: ListResponseMeta


class PhieuXuatActionRead(PhieuXuatRead):
    giao_dich_kho_ids: list[int]
    da_ghi_so_truoc_do: bool


class PhieuXuatActionResponse(BaseModel):
    data: PhieuXuatActionRead
    meta: ResponseMeta


class PhieuXuatQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_phieu_xuat", "-ma_phieu_xuat"] = (
        "-created_at"
    )
    loai_phieu: IssueType | None = None
    trang_thai: IssueState | None = None
    nhan_vien_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    yeu_cau_san_xuat_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    tu_ngay: date | None = None
    den_ngay: date | None = None

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def date_only(cls, value):
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


class PhieuXuatCuaToiQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_phieu_xuat", "-ma_phieu_xuat"] = (
        "-created_at"
    )
    loai_phieu: IssueType | None = None
    trang_thai: IssueState | None = None
    yeu_cau_san_xuat_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    tu_ngay: date | None = None
    den_ngay: date | None = None

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def date_only(cls, value):
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


class IssueError(BaseModel):
    code: str
    message: str
    details: list


class PhieuXuatErrorResponse(BaseModel):
    error: IssueError
    meta: ResponseMeta
