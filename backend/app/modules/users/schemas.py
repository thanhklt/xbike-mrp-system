from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from app.shared.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    roles: List[UserRole] = [UserRole.WAREHOUSE]
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    roles: Optional[List[UserRole]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
