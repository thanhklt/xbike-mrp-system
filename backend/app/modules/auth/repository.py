"""Credential lookup against the existing employee/role mappings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schemas import AuthEmployee
from app.modules.nhan_vien.models import User


def auth_employee(user: User) -> AuthEmployee:
    role = user.role.ma_vai_tro if user.role else None
    return AuthEmployee(
        id=user.id,
        email=user.email,
        full_name=user.ho_ten,
        ten_dang_nhap=user.ten_dang_nhap,
        roles=[role] if role else [],
        trang_thai=user.trang_thai,
        password_hash=user.mat_khau,
    )


class SqlAlchemyAuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_username(self, identifier: str) -> AuthEmployee | None:
        user = await self.session.scalar(select(User).where(User.ten_dang_nhap == identifier))
        return auth_employee(user) if user is not None else None

    async def find_unique_by_email(self, identifier: str) -> AuthEmployee | None:
        matches = (await self.session.scalars(select(User).where(User.email == identifier))).all()
        return auth_employee(matches[0]) if len(matches) == 1 else None

    async def get_by_id(self, employee_id: int) -> AuthEmployee | None:
        user = await self.session.scalar(select(User).where(User.id == employee_id))
        return auth_employee(user) if user is not None else None
