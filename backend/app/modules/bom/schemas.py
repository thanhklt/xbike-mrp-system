"""BOM contract v2 with the SCD2 decisions recorded in docs/DECISION.md."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

BomSort = Literal["id", "-id", "version", "-version", "start_time", "-start_time"]


class ChiTietBomInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int = Field(gt=0)
    so_luong: int = Field(gt=0)


class BomCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int = Field(gt=0)
    chi_tiet: list[ChiTietBomInput] = Field(min_length=1)

    @field_validator("chi_tiet")
    @classmethod
    def validate_components(
        cls, components: list[ChiTietBomInput], info: ValidationInfo
    ) -> list[ChiTietBomInput]:
        seen: set[int] = set()
        for index, component in enumerate(components):
            if component.mat_hang_id in seen:
                raise ValueError(f"Dòng {index}: mat_hang_id trùng thành phần trước đó")
            if component.mat_hang_id == info.data.get("mat_hang_id"):
                raise ValueError(f"Dòng {index}: thành phần không được trùng mặt hàng đầu ra")
            seen.add(component.mat_hang_id)
        return components


class KichHoatBomInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BomListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    mat_hang_id: int | None = Field(default=None, gt=0)
    version: int | None = Field(default=None, gt=0)
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
    start_time: datetime | None
    end_time: datetime | None
    is_active: bool
    da_duoc_su_dung: bool
    chi_tiet: list[ChiTietBomRead]


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
