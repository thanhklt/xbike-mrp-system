"""API schemas matching the PostgreSQL model; no generated sample values."""

import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta

INT_MAX = 2**31 - 1
MONEY_MAX = Decimal("9999999999999999.99")
ReceiptId = Annotated[int, Field(strict=True, gt=0, le=INT_MAX)]


def exact_money(value: object) -> object:
    if isinstance(value, (bool, float)):
        raise ValueError("Money must be an exact decimal string or integer")
    return value


ReceiptMoney = Annotated[
    Decimal,
    BeforeValidator(exact_money, json_schema_input_type=int | str),
    Field(ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False),
    AfterValidator(lambda value: value.quantize(Decimal("0.01"))),
]


def receipt_date(value: object) -> object:
    if isinstance(value, datetime) or not isinstance(value, (date, str)):
        raise ValueError("ngay_nhap must use YYYY-MM-DD")
    if isinstance(value, str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("ngay_nhap must use YYYY-MM-DD")
    return value


ReceiptDate = Annotated[date, BeforeValidator(receipt_date)]


def validate_lines(items) -> None:
    if len({item.mat_hang_id for item in items}) != len(items):
        raise ValueError("Items must not contain duplicate mat_hang_id")
    if sum((item.so_luong * item.don_gia_thuc for item in items), Decimal(0)) > MONEY_MAX:
        raise ValueError("tong_tien exceeds numeric(18,2) range")


class ReceiptItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: ReceiptId
    so_luong: ReceiptId
    don_gia_thuc: ReceiptMoney
    tong_gia: ReceiptMoney | None = None


class GoodsReceiptNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phieu_nhap: str
    nhan_vien_id: int | None = None
    ncc_id: ReceiptId
    ngay_nhap: ReceiptDate
    ghi_chu: str | None = None
    tong_tien: ReceiptMoney | None = None
    trang_thai: Literal["nhap"] = "nhap"
    items: list[ReceiptItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        validate_lines(self.items)
        return self


class ChiTietPhieuNhapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: ReceiptId
    so_luong: ReceiptId
    don_gia_thuc: ReceiptMoney


class PhieuNhapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncc_id: ReceiptId
    ngay_nhap: ReceiptDate
    ghi_chu: str | None = None
    chi_tiet: list[ChiTietPhieuNhapCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        validate_lines(self.chi_tiet)
        return self


class PhieuNhapPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ncc_id: ReceiptId | SkipJsonSchema[None] = None
    ngay_nhap: ReceiptDate | SkipJsonSchema[None] = None
    ghi_chu: str | None = None
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
        validate_lines(value)
        return value

    @field_validator("ncc_id", "ngay_nhap")
    @classmethod
    def require_non_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class PhieuNhapCompleteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChiTietPhieuNhapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    so_luong: int
    don_gia_thuc: ReceiptMoney | None
    tong_gia: ReceiptMoney | None


class PhieuNhapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    ma_phieu_nhap: str
    nhan_vien_id: int
    ncc_id: int
    ngay_nhap: date
    ghi_chu: str | None
    tong_tien: ReceiptMoney | None
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
