"""UC-15–19 DTOs: immutable one-level formulas (specs/use_cases/bom)."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

BomSort = Literal[
    "id",
    "-id",
    "version",
    "-version",
    "created_at",
    "-created_at",
    "kich_hoat_gan_nhat_at",
    "-kich_hoat_gan_nhat_at",
]


class ChiTietBomInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int = Field(strict=True, gt=0, le=2**31 - 1)
    so_luong: int = Field(strict=True, gt=0, le=2**31 - 1)


class BomFormula(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chi_tiet: list[ChiTietBomInput] = Field(min_length=1)

    @field_validator("chi_tiet")
    @classmethod
    def validate_components(cls, components: list[ChiTietBomInput]) -> list[ChiTietBomInput]:
        seen: set[int] = set()
        for index, component in enumerate(components):
            if component.mat_hang_id in seen:
                raise ValueError(f"Dòng {index}: mat_hang_id trùng thành phần trước đó")
            seen.add(component.mat_hang_id)
        return components


class BomCreate(BomFormula):
    """Internal DTO retained for callers; no standalone HTTP create-v1 endpoint."""

    mat_hang_id: int = Field(strict=True, gt=0, le=2**31 - 1)


class KichHoatBomInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BomListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    mat_hang_id: int | None = Field(default=None, gt=0, le=2**31 - 1)
    version: int | None = Field(default=None, gt=0, le=2**31 - 1)
    is_active: bool | None = None
    sort: BomSort = "id"


class ChiTietBomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    so_luong: int


class BomRead(BaseModel):
    id: int
    mat_hang_id: int
    version: int
    created_at: AwareDatetime
    kich_hoat_gan_nhat_at: AwareDatetime
    is_active: bool
    da_duoc_su_dung: bool
    chi_tiet: list[ChiTietBomRead]

    @field_validator("created_at", "kich_hoat_gan_nhat_at")
    @classmethod
    def utc_time(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


class BomTreeNode(BaseModel):
    mat_hang_id: int
    so_luong_tren_mot_don_vi_cha: int
    bom_id: int | None
    children: list["BomTreeNode"]


class BomTreeRead(BaseModel):
    bom_id: int
    mat_hang_id: int
    version: int
    children: list[BomTreeNode]


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class BomDetailResponse(BaseModel):
    data: BomRead
    meta: ResponseMeta


class BomListResponse(BaseModel):
    data: list[BomRead]
    meta: ListResponseMeta


class BomTreeResponse(BaseModel):
    data: BomTreeRead
    meta: ResponseMeta


class BomError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class BomErrorResponse(BaseModel):
    error: BomError
    meta: ResponseMeta
