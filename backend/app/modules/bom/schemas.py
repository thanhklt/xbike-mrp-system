"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BOMItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bom_id: int
    mat_hang_id: int
    so_luong: int


class BOMItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int
    so_luong: int = Field(gt=0)


class BOMHeaderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mat_hang_id: int
    version: int
    start_time: datetime | None
    end_time: datetime | None
    is_active: bool | None
    items: list[BOMItemResponse] = Field(default_factory=list)


class BOMHeaderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_hang_id: int
    version: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool | None = None
    items: list[BOMItemCreate] = Field(default_factory=list)
