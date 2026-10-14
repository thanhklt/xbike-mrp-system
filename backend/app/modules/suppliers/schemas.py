"""API schemas matching the PostgreSQL model; no generated sample values."""

from pydantic import BaseModel, ConfigDict


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_ncc: str
    ten_ncc: str | None
    so_dien_thoai: str | None
    dia_chi: str | None
    phuong: str | None
    tinh: str | None


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_ncc: str
    ten_ncc: str | None = None
    so_dien_thoai: str | None = None
    dia_chi: str | None = None
    phuong: str | None = None
    tinh: str | None = None
