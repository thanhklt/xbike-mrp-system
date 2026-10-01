from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.shared.enums import ItemType, PartCategory, UnitOfMeasure


class PartBase(BaseModel):
    part_number: str = Field(..., max_length=50, example="XB-FRM-ALU-01")
    name: str = Field(..., max_length=255, example="6061 Alloy Commuter Frame")
    description: Optional[str] = None
    item_type: ItemType = ItemType.RAW_MATERIAL
    category: PartCategory = PartCategory.FRAME
    unit: UnitOfMeasure = UnitOfMeasure.PCS
    lead_time_days: int = Field(default=7, ge=0)
    safety_stock: float = Field(default=10.0, ge=0.0)
    standard_cost: float = Field(default=0.0, ge=0.0)
    is_active: bool = True


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    item_type: Optional[ItemType] = None
    category: Optional[PartCategory] = None
    unit: Optional[UnitOfMeasure] = None
    lead_time_days: Optional[int] = None
    safety_stock: Optional[float] = None
    standard_cost: Optional[float] = None
    is_active: Optional[bool] = None


class PartResponse(PartBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
