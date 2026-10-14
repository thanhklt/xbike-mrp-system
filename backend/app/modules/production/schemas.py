"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_yeu_cau_san_xuat: str
    mat_hang_id: int
    so_luong: int
    nhan_vien_id: int
    nhan_vien_duoc_giao_id: int | None
    trang_thai: Literal["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]
    created_at: datetime
    completed_at: datetime | None


class WorkOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lenh_san_xuat_id: int
    mat_hang_id: int
    so_luong_can: int


class WorkOrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int
    so_luong_can: int = Field(gt=0)


class WorkOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_lenh_san_xuat: str
    yeu_cau_san_xuat_id: int
    lenh_san_xuat_cha_id: int | None
    mat_hang_id: int
    bom_id: int
    so_luong: int
    nhan_vien_id: int | None
    trang_thai: Literal["nhap", "da_gui", "dang_thuc_hien", "hoan_thanh", "da_huy"]
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    items: list[WorkOrderItemResponse] = Field(default_factory=list)


class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_lenh_san_xuat: str
    yeu_cau_san_xuat_id: int
    lenh_san_xuat_cha_id: int | None = None
    mat_hang_id: int
    bom_id: int
    so_luong: int = Field(gt=0)
    nhan_vien_id: int | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    trang_thai: Literal["nhap"] = "nhap"
    items: list[WorkOrderItemCreate] = Field(default_factory=list)


class ProductionCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu: str
    lenh_san_xuat_id: int
    so_luong_hoan_thanh: int
    nhan_vien_id: int | None
    trang_thai: Literal["nhap", "cho_duyet", "da_duyet", "tu_choi"]
    finish_time: datetime | None
