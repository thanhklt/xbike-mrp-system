from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.shared.enums import StockMovementType


class StockLevelResponse(BaseModel):
    id: int
    part_id: int
    part_number: str
    part_name: str
    warehouse_code: str
    bin_location: str
    quantity_on_hand: float
    quantity_allocated: float
    quantity_reserved: float
    quantity_available: float
    updated_at: datetime


class StockMovementCreate(BaseModel):
    part_id: int
    movement_type: StockMovementType
    quantity: float = Field(..., gt=0)
    reference_order_number: Optional[str] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: int
    part_id: int
    part_number: str
    movement_type: StockMovementType
    quantity: float
    reference_order_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
