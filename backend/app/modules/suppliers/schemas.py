from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class SupplierBase(BaseModel):
    code: str = Field(..., max_length=50, example="SUP-SHIMANO-01")
    name: str = Field(..., max_length=255, example="Shimano Component Logistics")
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: int = 30
    lead_time_days: int = 14
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms_days: Optional[int] = None
    lead_time_days: Optional[int] = None
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
