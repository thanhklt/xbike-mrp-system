"""Validated snapshots supplied by the calling service, never ORM objects."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

PositiveInt = Annotated[int, Field(strict=True, gt=0)]
StockQuantity = Annotated[int, Field(strict=True, ge=0)]


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Item(Snapshot):
    id: PositiveInt
    ma_mat_hang: str = Field(min_length=1)
    ten_mat_hang: str = Field(min_length=1)
    don_vi_tinh: str = Field(min_length=1)
    loai_mat_hang: Literal["nguyen_vat_lieu", "linh_kien", "ban_thanh_pham", "thanh_pham"]


class BOMLine(Snapshot):
    mat_hang_id: PositiveInt
    so_luong: PositiveInt


class BOM(Snapshot):
    id: PositiveInt
    mat_hang_id: PositiveInt
    version: PositiveInt
    chi_tiet: tuple[BOMLine, ...] = Field(min_length=1)


class PlanningFacts(Snapshot):
    mat_hang_id: PositiveInt
    so_luong: PositiveInt
    mat_hang: tuple[Item, ...]
    bom: tuple[BOM, ...] = ()
    ton_kho: dict[PositiveInt, StockQuantity] = Field(default_factory=dict)


class MaterialFacts(Snapshot):
    # Entire direct requirements and effective posted quantities, including adjustments.
    nhu_cau: dict[PositiveInt, PositiveInt] = Field(min_length=1)
    da_cap: dict[PositiveInt, StockQuantity]


class IssueFacts(MaterialFacts):
    trang_thai: str
    trang_thai_nguon: str
    chi_tiet: tuple[BOMLine, ...] = Field(min_length=1)
    ton_kho: dict[PositiveInt, StockQuantity]


class StartFacts(MaterialFacts):
    trang_thai: str


class CompletionFacts(MaterialFacts):
    trang_thai: str
    trang_thai_lenh: str
    so_luong_lenh: PositiveInt
    so_luong_da_hoan_thanh: StockQuantity
    so_luong_hoan_thanh: PositiveInt
