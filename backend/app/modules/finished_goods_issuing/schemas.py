from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class DispatchItemBase(BaseModel):
    product_part_id: int
    quantity_dispatched: float = Field(..., gt=0)
    serial_numbers: Optional[str] = Field(None, example="XB-SN-001, XB-SN-002")


class DispatchItemCreate(DispatchItemBase):
    pass


class DispatchItemResponse(DispatchItemBase):
    id: int
    product_part_number: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True


class FinishedGoodsDispatchBase(BaseModel):
    dispatch_number: str = Field(..., max_length=50, example="DSP-2026-0005")
    destination_dealer: str = Field(..., max_length=255, example="EuroBike Hub Berlin")
    carrier_tracking_number: Optional[str] = None
    status: str = "PREPARING"
    notes: Optional[str] = None


class FinishedGoodsDispatchCreate(FinishedGoodsDispatchBase):
    items: List[DispatchItemCreate] = []


class FinishedGoodsDispatchResponse(FinishedGoodsDispatchBase):
    id: int
    dispatched_by_user_id: int
    created_at: datetime
    dispatched_at: Optional[datetime] = None
    items: List[DispatchItemResponse] = []

    class Config:
        from_attributes = True
