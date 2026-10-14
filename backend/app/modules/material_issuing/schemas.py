"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MaterialIssueItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phieu_xuat_id: int
    mat_hang_id: int
    so_luong: int
    don_gia_thuc: int | None
    tong_gia: int | None


class MaterialIssueItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int
    so_luong: int = Field(gt=0)
    don_gia_thuc: int | None = Field(default=None, ge=0)
    tong_gia: int | None = Field(default=None, ge=0)


class MaterialIssueRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu_xuat: str
    nhan_vien_id: int | None
    loai_phieu: Literal["xuat_vat_tu", "xuat_thanh_pham"]
    yeu_cau_san_xuat_id: int | None
    lenh_san_xuat_id: int | None
    tong_tien: int | None
    trang_thai: Literal["nhap", "cho_duyet", "da_duyet", "tu_choi"]
    created_at: datetime | None
    items: list[MaterialIssueItemResponse] = Field(default_factory=list)


class MaterialIssueRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_phieu_xuat: str
    nhan_vien_id: int | None = None
    loai_phieu: Literal["xuat_vat_tu", "xuat_thanh_pham"]
    yeu_cau_san_xuat_id: int | None = None
    lenh_san_xuat_id: int | None = None
    tong_tien: int | None = Field(default=None, ge=0)
    trang_thai: Literal["nhap"] = "nhap"
    items: list[MaterialIssueItemCreate] = Field(default_factory=list)
