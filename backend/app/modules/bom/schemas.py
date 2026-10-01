from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class BOMItemBase(BaseModel):
    component_part_id: int
    quantity_required: float = Field(..., gt=0)
    scrap_factor_percent: float = Field(default=0.0, ge=0.0)
    notes: Optional[str] = None


class BOMItemCreate(BOMItemBase):
    pass


class BOMItemResponse(BOMItemBase):
    id: int
    component_part_number: Optional[str] = None
    component_name: Optional[str] = None
    unit: Optional[str] = None

    class Config:
        from_attributes = True


class BOMHeaderBase(BaseModel):
    product_part_id: int
    bom_code: str = Field(..., max_length=50, example="BOM-XB-URBAN-01-V1")
    version: str = "1.0"
    description: Optional[str] = None
    is_active: bool = True


class BOMHeaderCreate(BOMHeaderBase):
    items: List[BOMItemCreate] = []


class BOMHeaderResponse(BOMHeaderBase):
    id: int
    product_name: Optional[str] = None
    product_part_number: Optional[str] = None
    items: List[BOMItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
