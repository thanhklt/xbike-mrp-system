"""Pydantic schemas for mat_hang following API Contract v2."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatHangRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_mat_hang: str
    ten_mat_hang: str | None
    sku: str
    loai_mat_hang: Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]
    don_vi_tinh: str
    mau_sac: str | None
    mo_ta: str | None
    don_gia: int | None
    is_active: bool | None


class MatHangCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_mat_hang: str = Field(
        ..., pattern=r"^MH-[0-9]{6}$", description="Mã mặt hàng dạng MH-xxxxxx"
    )
    sku: str = Field(..., min_length=1, description="SKU duy nhất")
    ten_mat_hang: str | None = Field(default=None, min_length=1)
    loai_mat_hang: Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]
    don_vi_tinh: str = Field(
        ..., pattern=r"^[a-z]+(_[a-z]+)*$", description="Đơn vị tính snake_case không dấu"
    )
    mau_sac: str | None = Field(
        default=None, pattern=r"^[a-z]+(_[a-z]+)*$", description="Màu sắc snake_case không dấu"
    )
    mo_ta: str | None = None
    don_gia: int | None = Field(default=None, ge=0, description="Đơn giá nguyên dương")
    is_active: bool = True

    @field_validator("ma_mat_hang")
    @classmethod
    def validate_ma(cls, v: str) -> str:
        if v.endswith("000000"):
            raise ValueError("Mã mặt hàng không được kết thúc bằng 000000")
        return v


class MatHangPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_mat_hang: str | None = Field(default=None, pattern=r"^MH-[0-9]{6}$")
    sku: str | None = Field(default=None, min_length=1)
    ten_mat_hang: str | None = None
    loai_mat_hang: (
        Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"] | None
    ) = None
    don_vi_tinh: str | None = Field(default=None, pattern=r"^[a-z]+(_[a-z]+)*$")
    mau_sac: str | None = Field(default=None, pattern=r"^[a-z]+(_[a-z]+)*$")
    mo_ta: str | None = None
    don_gia: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("ma_mat_hang")
    @classmethod
    def validate_ma(cls, v: str | None) -> str | None:
        if v is not None and v.endswith("000000"):
            raise ValueError("Mã mặt hàng không được kết thúc bằng 000000")
        return v


class SingleMeta(BaseModel):
    request_id: str | None = None


class MatHangSingleResponse(BaseModel):
    data: MatHangRead
    meta: SingleMeta = Field(default_factory=SingleMeta)


class ListMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    request_id: str | None = None


class MatHangListResponse(BaseModel):
    data: list[MatHangRead]
    meta: ListMeta
