from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.shared.enums import GoodsReceiptStatus


class ReceiptItemBase(BaseModel):
    part_id: int
    quantity_shipped: float = Field(..., gt=0)
    quantity_accepted: float = Field(default=0.0, ge=0)
    quantity_rejected: float = Field(default=0.0, ge=0)
    lot_number: Optional[str] = None


class ReceiptItemCreate(ReceiptItemBase):
    pass


class ReceiptItemResponse(ReceiptItemBase):
    id: int
    part_number: Optional[str] = None
    part_name: Optional[str] = None

    class Config:
        from_attributes = True


class GoodsReceiptNoteBase(BaseModel):
    grn_number: str = Field(..., max_length=50, example="GRN-2026-0089")
    purchase_order_number: str = Field(..., max_length=50, example="PO-2026-004")
    supplier_id: int
    status: GoodsReceiptStatus = GoodsReceiptStatus.PENDING_INSPECTION
    notes: Optional[str] = None


class GoodsReceiptNoteCreate(GoodsReceiptNoteBase):
    items: List[ReceiptItemCreate] = []


class GoodsReceiptNoteResponse(GoodsReceiptNoteBase):
    id: int
    supplier_name: Optional[str] = None
    received_by_user_id: int
    received_at: datetime
    items: List[ReceiptItemResponse] = []

    class Config:
        from_attributes = True
