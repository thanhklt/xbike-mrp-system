"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StockLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    so_luong: int
    updated_at: datetime | None


class StockMovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    loai_giao_dich: Literal[
        "nhap_vat_tu",
        "xuat_vat_tu",
        "nhap_san_pham_san_xuat",
        "xuat_thanh_pham",
        "dieu_chinh_ton_kho",
    ]
    so_luong_bien_dong: int
    chi_tiet_phieu_nhap_id: int | None
    chi_tiet_phieu_xuat_id: int | None
    chung_tu_hoan_thanh_sx_id: int | None
    chi_tiet_phieu_dieu_chinh_id: int | None
    nhan_vien_id: int
    posted_at: datetime


class StockAdjustmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phieu_dieu_chinh_kho_id: int
    mat_hang_id: int
    giao_dich_goc_id: int | None
    so_luong_bien_dong: int


class StockAdjustmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_phieu: str
    nhan_vien_id: int
    ly_do: str
    trang_thai: Literal["nhap", "cho_duyet", "da_duyet", "tu_choi", "loi"]
    created_at: datetime
    items: list[StockAdjustmentItemResponse] = Field(default_factory=list)


class AdjustmentErrorTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phieu_dieu_chinh_kho_id: int
    mo_ta_loi: str
    trang_thai: Literal["cho_xu_ly", "dang_xu_ly", "da_xu_ly"]
    nguoi_xu_ly_id: int | None
    ket_qua_xu_ly: str | None
    created_at: datetime
