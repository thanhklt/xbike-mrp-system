"""API schemas matching the PostgreSQL model; no generated sample values."""

import re
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

from app.modules.users.schemas import ListResponseMeta, ResponseMeta


class ReceiptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phieu_nhap_id: int
    mat_hang_id: int
    so_luong: int
    don_gia_thuc: int | None
    tong_gia: int | None


class ReceiptItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int
    so_luong: int = Field(gt=0)
    don_gia_thuc: int | None = Field(default=None, ge=0)
    tong_gia: int | None = Field(default=None, ge=0)


class GoodsReceiptNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu_nhap: str
    nhan_vien_id: int | None
    ncc_id: int | None
    tong_tien: int | None
    trang_thai: Literal["nhap", "hoan_thanh"]
    created_at: datetime | None
    items: list[ReceiptItemResponse] = Field(default_factory=list)


class GoodsReceiptNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phieu_nhap: str
    nhan_vien_id: int | None = None
    ncc_id: int | None = None
    tong_tien: int | None = Field(default=None, ge=0)
    trang_thai: Literal["nhap"] = "nhap"
    items: list[ReceiptItemCreate] = Field(default_factory=list)


INT_MAX = 2**31 - 1
ReceiptId = Annotated[int, Field(strict=True, gt=0, le=INT_MAX)]
ReceiptMoney = Annotated[int, Field(strict=True, ge=0, le=INT_MAX)]


class ChiTietPhieuNhapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: ReceiptId
    so_luong: ReceiptId
    don_gia_thuc: ReceiptMoney


class PhieuNhapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncc_id: ReceiptId | None = None
    chi_tiet: list[ChiTietPhieuNhapCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        ids = [item.mat_hang_id for item in self.chi_tiet]
        if len(ids) != len(set(ids)):
            raise ValueError("chi_tiet must not contain duplicate mat_hang_id")
        if sum(item.so_luong * item.don_gia_thuc for item in self.chi_tiet) > INT_MAX:
            raise ValueError("tong_tien exceeds PostgreSQL INTEGER range")
        return self


class PhieuNhapPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncc_id: ReceiptId | None = None
    chi_tiet: (
        Annotated[list[ChiTietPhieuNhapCreate], Field(min_length=1)] | SkipJsonSchema[None]
    ) = None

    @field_validator("chi_tiet")
    @classmethod
    def validate_replacement(
        cls, value: list[ChiTietPhieuNhapCreate] | None
    ) -> list[ChiTietPhieuNhapCreate]:
        if value is None:
            raise ValueError("chi_tiet cannot be null")
        return PhieuNhapCreate(chi_tiet=value).chi_tiet


class PhieuNhapCompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChiTietPhieuNhapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    so_luong: int
    don_gia_thuc: int | None
    tong_gia: int | None


class PhieuNhapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    ma_phieu_nhap: str
    nhan_vien_id: int | None
    ncc_id: int | None
    tong_tien: int | None
    trang_thai: Literal["nhap", "hoan_thanh"]
    created_at: datetime | None
    chi_tiet: list[ChiTietPhieuNhapRead] = Field(validation_alias="items")

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )

    @field_validator("chi_tiet")
    @classmethod
    def stable_item_order(cls, value: list[ChiTietPhieuNhapRead]) -> list[ChiTietPhieuNhapRead]:
        return sorted(value, key=lambda item: item.id)


class PhieuNhapListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    trang_thai: Literal["nhap", "hoan_thanh"] | None = None
    ncc_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    nhan_vien_id: int | None = Field(default=None, gt=0, le=INT_MAX)
    tu_ngay: date | None = None
    den_ngay: date | None = None
    sort: Literal["id", "-id", "created_at", "-created_at", "ma_phieu_nhap", "-ma_phieu_nhap"] = (
        "id"
    )

    @field_validator("tu_ngay", "den_ngay", mode="before")
    @classmethod
    def require_iso_date(cls, value: object) -> object:
        if isinstance(value, str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Date must use YYYY-MM-DD format")
        return value

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.tu_ngay and self.den_ngay and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay must not be after den_ngay")
        if self.tu_ngay == date.min or self.den_ngay in (date.min, date.max):
            raise ValueError("Date boundary outside supported UTC range")
        return self


class PhieuNhapDetailResponse(BaseModel):
    data: PhieuNhapRead
    meta: ResponseMeta


class PhieuNhapActionRead(PhieuNhapRead):
    giao_dich_kho_ids: list[int]
    da_ghi_so_truoc_do: bool


class PhieuNhapActionResponse(BaseModel):
    data: PhieuNhapActionRead
    meta: ResponseMeta


class PhieuNhapListResponse(BaseModel):
    data: list[PhieuNhapRead]
    meta: ListResponseMeta


class PhieuNhapError(BaseModel):
    code: str
    message: str
    details: list[dict] = Field(default_factory=list)


class PhieuNhapErrorResponse(BaseModel):
    error: PhieuNhapError
    meta: ResponseMeta
