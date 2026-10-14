"""API schemas matching the PostgreSQL model; no generated sample values."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PartResponse(BaseModel):
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


class PartCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_mat_hang: str
    ten_mat_hang: str | None = None
    sku: str
    loai_mat_hang: Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]
    don_vi_tinh: str
    mau_sac: str | None = None
    mo_ta: str | None = None
    don_gia: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
