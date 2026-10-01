from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.shared.enums import MaterialIssueStatus


class MaterialIssueItemBase(BaseModel):
    part_id: int
    quantity_requested: float = Field(..., gt=0)
    quantity_issued: float = Field(default=0.0, ge=0)
    source_bin_location: Optional[str] = None


class MaterialIssueItemCreate(MaterialIssueItemBase):
    pass


class MaterialIssueItemResponse(MaterialIssueItemBase):
    id: int
    part_number: Optional[str] = None
    part_name: Optional[str] = None

    class Config:
        from_attributes = True


class MaterialIssueRequestBase(BaseModel):
    request_number: str = Field(..., max_length=50, example="MIR-2026-0034")
    work_order_id: int
    status: MaterialIssueStatus = MaterialIssueStatus.REQUESTED
    notes: Optional[str] = None


class MaterialIssueRequestCreate(MaterialIssueRequestBase):
    items: List[MaterialIssueItemCreate] = []


class MaterialIssueRequestResponse(MaterialIssueRequestBase):
    id: int
    requested_by_user_id: int
    issued_by_user_id: Optional[int] = None
    created_at: datetime
    issued_at: Optional[datetime] = None
    items: List[MaterialIssueItemResponse] = []

    class Config:
        from_attributes = True
