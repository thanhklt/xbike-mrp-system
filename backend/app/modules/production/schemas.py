from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.shared.enums import WorkOrderStatus


class WorkOrderBase(BaseModel):
    work_order_number: str = Field(..., max_length=50, example="WO-2026-0012")
    product_part_id: int
    bom_id: int
    quantity_planned: float = Field(..., gt=0)
    status: WorkOrderStatus = WorkOrderStatus.PLANNED
    scheduled_start: Optional[datetime] = None
    scheduled_finish: Optional[datetime] = None
    notes: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdateStatus(BaseModel):
    status: WorkOrderStatus
    quantity_completed: Optional[float] = None
    quantity_scrapped: Optional[float] = None


class WorkOrderResponse(WorkOrderBase):
    id: int
    product_part_number: Optional[str] = None
    product_name: Optional[str] = None
    quantity_completed: float = 0.0
    quantity_scrapped: float = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
