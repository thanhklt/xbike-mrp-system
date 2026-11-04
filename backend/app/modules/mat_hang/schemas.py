"""HTTP and detached snapshot values for the MatHang SQL contract."""

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

ItemType = Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]
ItemName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Money = Annotated[int, Field(strict=True, ge=0, le=2**63 - 1)]
SnakeCode = Annotated[str, StringConstraints(pattern=r"^[a-z]+(_[a-z]+)*$")]
ItemCode = Annotated[str, StringConstraints(pattern=r"^MH-[0-9]{6}$")]


class MatHangRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: int
    ma_mat_hang: str
    ten_mat_hang: str
    sku: str
    loai_mat_hang: ItemType
    don_vi_tinh: str
    mau_sac: str | None
    mo_ta: str | None
    don_gia: Money
    is_active: bool
    so_luong_ton: int = Field(ge=0)
    ton_kho_updated_at: datetime | None

    @field_validator("ton_kho_updated_at")
    @classmethod
    def normalize_stock_time(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value is not None else None


class MatHangCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_mat_hang: ItemCode
    sku: str = Field(min_length=1)
    ten_mat_hang: ItemName
    loai_mat_hang: ItemType
    don_vi_tinh: SnakeCode
    mau_sac: SnakeCode | None = None
    mo_ta: str | None = None
    don_gia: Money
    is_active: bool = True

    @field_validator("ma_mat_hang")
    @classmethod
    def validate_ma(cls, value: str) -> str:
        if value == "MH-000000":
            raise ValueError("Mã mặt hàng không được kết thúc bằng 000000")
        return value


class MatHangPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_mat_hang: ItemCode | None = None
    sku: str | None = Field(default=None, min_length=1)
    ten_mat_hang: ItemName | None = None
    loai_mat_hang: ItemType | None = None
    don_vi_tinh: SnakeCode | None = None
    mau_sac: SnakeCode | None = None
    mo_ta: str | None = None
    don_gia: Money | SkipJsonSchema[None] = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_required_nulls(cls, values: Any) -> Any:
        if isinstance(values, dict):
            required = {
                "ma_mat_hang",
                "sku",
                "ten_mat_hang",
                "loai_mat_hang",
                "don_vi_tinh",
                "is_active",
                "don_gia",
            }
            for name in required & values.keys():
                if values[name] is None:
                    raise ValueError(f"{name} không được null")
        return values

    @field_validator("ma_mat_hang")
    @classmethod
    def validate_ma(cls, value: str | None) -> str | None:
        if value == "MH-000000":
            raise ValueError("Mã mặt hàng không được kết thúc bằng 000000")
        return value


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


class CatalogMeta(BaseModel):
    total: int
    request_id: str | None = None


class DanhMucMatHangResponse(BaseModel):
    data: list[MatHangRead]
    meta: CatalogMeta
