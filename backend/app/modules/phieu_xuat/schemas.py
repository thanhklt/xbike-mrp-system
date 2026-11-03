"""Contract v3 issue documents: quantities only on input, integer VND after posting."""

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
from pydantic.json_schema import SkipJsonSchema

from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta

INT_MAX = 2**31 - 1
MONEY_MAX = 2**63 - 1
IssueId = Annotated[int, Field(strict=True, gt=0, le=INT_MAX)]
IssueMoney = Annotated[int, Field(strict=True, ge=0, le=MONEY_MAX)]
IssueType = Literal["xuat_vat_tu", "xuat_thanh_pham"]
IssueState = Literal["nhap", "cho_duyet", "da_duyet", "tu_choi"]


class ChiTietPhieuXuatCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mat_hang_id: IssueId
    so_luong: IssueId


IssueLines = Annotated[list[ChiTietPhieuXuatCreate], Field(min_length=1)]


def unique_lines(lines: list[ChiTietPhieuXuatCreate]) -> list[ChiTietPhieuXuatCreate]:
    if len({line.mat_hang_id for line in lines}) != len(lines):
        raise ValueError("Duplicate mat_hang_id")
    return lines


class PhieuXuatCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loai_phieu: IssueType
    lenh_san_xuat_id: IssueId | None = None
    yeu_cau_san_xuat_id: IssueId | None = None
    chi_tiet: IssueLines

    @model_validator(mode="after")
    def validate_source(self) -> Self:
        material = self.loai_phieu == "xuat_vat_tu"
        if material != (self.lenh_san_xuat_id is not None) or material == (
            self.yeu_cau_san_xuat_id is not None
        ):
            raise ValueError("Exactly one source is required for loai_phieu")
        return self

    _unique = field_validator("chi_tiet")(unique_lines)


class PhieuXuatPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chi_tiet: IssueLines | SkipJsonSchema[None] = None

    @model_validator(mode="before")
    @classmethod
    def reject_null(cls, value):
        if isinstance(value, dict) and "chi_tiet" in value and value["chi_tiet"] is None:
            raise ValueError("chi_tiet cannot be null")
        return value

    @field_validator("chi_tiet")
    @classmethod
    def check_unique(cls, value):
        return unique_lines(value) if value is not None else value


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
    lenh_san_xuat_id: int | None
    yeu_cau_san_xuat_id: int | None
    tong_tien: IssueMoney | None
    trang_thai: IssueState
    created_at: datetime
    chi_tiet: list[ChiTietPhieuXuatRead]

    @field_validator("created_at")
    @classmethod
    def utc_time(cls, value):
        return value.astimezone(timezone.utc)


class PhieuXuatResponse(BaseModel):
    data: PhieuXuatRead
    meta: ResponseMeta


class PhieuXuatListResponse(BaseModel):
    data: list[PhieuXuatRead]
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
    lenh_san_xuat_id: int | None = Field(default=None, gt=0, le=INT_MAX)
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
