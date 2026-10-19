"""Credential lookup against the existing employee/role mappings."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.schemas import AuthEmployee
from app.modules.users.models import User


def auth_employee(user: User) -> AuthEmployee:
    role = user.role.ma_vai_tro if user.role else None
    return AuthEmployee(
        id=user.id,
        email=user.email,
        ho_ten=user.ho_ten,
        ten_dang_nhap=user.ten_dang_nhap,
        roles=[role] if role else [],
        trang_thai=user.trang_thai,
        password_hash=user.mat_khau,
        ma_nhan_vien=user.ma_nhan_vien,
        vai_tro_id=user.vai_tro_id,
        ma_vai_tro=role,
        ngay_sinh=user.ngay_sinh,
        so_dien_thoai=user.so_dien_thoai,
        ngay_vao_lam=user.ngay_vao_lam,
        he_so_luong=user.he_so_luong,
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

    async def lock_by_id(self, employee_id: int) -> AuthEmployee | None:
        user = await self.session.scalar(
            select(User)
            .where(User.id == employee_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return auth_employee(user) if user is not None else None

    async def set_password_hash(self, employee_id: int, password_hash: str) -> None:
        await self.session.execute(
            update(User).where(User.id == employee_id).values(mat_khau=password_hash)
        )
