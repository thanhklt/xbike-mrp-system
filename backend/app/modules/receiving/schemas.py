"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
