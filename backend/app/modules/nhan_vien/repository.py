"""Employee persistence, write locks and ORM-independent snapshots."""

from sqlalchemy import false, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nhan_vien.dto import (
    EmployeeData,
    EmployeeListQuery,
    EmployeePage,
    NewEmployee,
    RoleData,
    RolePage,
)
from app.modules.nhan_vien.errors import EmployeeError
from app.modules.nhan_vien.models import Role, User

# IDs in PostgreSQL use signed 32-bit integers.
MAX_EMPLOYEE_ID = 2**31 - 1

_SORT_COLUMNS = {
    "id": User.id,
    "ma_nhan_vien": User.ma_nhan_vien,
    "ho_ten": User.ho_ten,
    "ten_dang_nhap": User.ten_dang_nhap,
}


def _to_employee_data(user: User) -> EmployeeData:
    return EmployeeData(
        id=user.id,
        ma_nhan_vien=user.ma_nhan_vien,
        ho_ten=user.ho_ten,
        vai_tro_id=user.vai_tro_id,
        ma_vai_tro=user.role.ma_vai_tro if user.role else None,
        trang_thai=user.trang_thai,
        ten_dang_nhap=user.ten_dang_nhap,
        ngay_sinh=user.ngay_sinh,
        so_dien_thoai=user.so_dien_thoai,
        email=user.email,
        ngay_vao_lam=user.ngay_vao_lam,
        he_so_luong=user.he_so_luong,
    )


class SqlAlchemyEmployeeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, query: EmployeeListQuery) -> EmployeePage:
        statement = select(User)
        if query.q:
            statement = statement.where(
                or_(
                    User.ma_nhan_vien.icontains(query.q, autoescape=True),
                    User.ho_ten.icontains(query.q, autoescape=True),
                )
            )
        if query.vai_tro_id is not None:
            statement = statement.where(
                User.vai_tro_id == query.vai_tro_id
                if query.vai_tro_id <= MAX_EMPLOYEE_ID
                else false()
            )
        if query.trang_thai is not None:
            statement = statement.where(User.trang_thai == query.trang_thai)

        total = (
            await self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        offset = (query.page - 1) * query.page_size
        if offset >= total:
            return EmployeePage(items=(), total=total)

        sort_column = _SORT_COLUMNS[query.sort.removeprefix("-")]
        ordering = sort_column.desc() if query.sort.startswith("-") else sort_column.asc()
        records = (
            await self._session.scalars(
                statement.order_by(ordering, User.id).offset(offset).limit(query.page_size)
            )
        ).all()
        return EmployeePage(items=tuple(_to_employee_data(user) for user in records), total=total)

    async def get_by_id(self, employee_id: int) -> EmployeeData | None:
        if employee_id > MAX_EMPLOYEE_ID:
            return None
        user = await self._session.scalar(select(User).where(User.id == employee_id))
        return _to_employee_data(user) if user is not None else None

    async def lock_writes(self) -> None:
        if self._session.get_bind().dialect.name == "postgresql":
            # Shared by all account mutations; count/ETag checks follow this lock.
            await self._session.execute(text("SELECT pg_advisory_xact_lock(769231001)"))

    async def get_for_update(self, employee_id: int) -> EmployeeData | None:
        if employee_id > MAX_EMPLOYEE_ID:
            return None
        user = await self._session.scalar(
            select(User)
            .where(User.id == employee_id)
            .with_for_update(of=User)
            .execution_options(populate_existing=True)
        )
        return _to_employee_data(user) if user else None

    async def get_role(self, role_id: int) -> RoleData | None:
        role = await self._session.get(Role, role_id)
        return RoleData(role.id, role.ma_vai_tro, role.ten_vai_tro) if role else None

    async def list_roles(self, page: int, page_size: int) -> RolePage:
        total = await self._session.scalar(select(func.count()).select_from(Role)) or 0
        offset = (page - 1) * page_size
        if offset >= total:
            return RolePage((), total)
        roles = (
            await self._session.scalars(
                select(Role).order_by(Role.id).offset(offset).limit(page_size)
            )
        ).all()
        return RolePage(tuple(RoleData(r.id, r.ma_vai_tro, r.ten_vai_tro) for r in roles), total)

    async def active_admin_count(self) -> int:
        return (
            await self._session.scalar(
                select(func.count())
                .select_from(User)
                .join(Role, User.vai_tro_id == Role.id)
                .where(Role.ma_vai_tro == "quan_tri_vien", User.trang_thai == "hoat_dong")
            )
            or 0
        )

    async def create(self, employee: NewEmployee) -> EmployeeData:
        # The existing v3 table has no identity/sequence. Every allocator uses
        # the same transaction lock, so competing API requests cannot share an ID.
        await self.lock_writes()
        largest_id = await self._session.scalar(select(func.max(User.id))) or 0
        employee_id = max(largest_id, 0) + 1
        if employee_id > MAX_EMPLOYEE_ID:
            raise EmployeeError("het_dai_id", "Đã hết dải ID nhân viên.", 409)
        user = User(
            id=employee_id,
            ten_dang_nhap=employee.ten_dang_nhap,
            ma_nhan_vien=employee.ma_nhan_vien,
            vai_tro_id=employee.vai_tro_id,
            mat_khau=employee.password_hash,
            trang_thai="hoat_dong",
            **employee.profile,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise EmployeeError(
                "ma_bi_trung", "Tên đăng nhập hoặc mã nhân viên đã tồn tại.", 409
            ) from exc
        return await self._snapshot(user.id)

    async def _snapshot(self, employee_id: int) -> EmployeeData:
        user = await self._session.scalar(
            select(User).where(User.id == employee_id).execution_options(populate_existing=True)
        )
        assert user is not None
        return _to_employee_data(user)

    async def update_profile(self, employee_id: int, changes: dict[str, object]) -> EmployeeData:
        user = await self._session.get(User, employee_id)
        assert user is not None
        for name, value in changes.items():
            setattr(user, name, value)
        await self._session.flush()
        return await self._snapshot(employee_id)

    async def set_role(self, employee_id: int, role_id: int) -> EmployeeData:
        return await self.update_profile(employee_id, {"vai_tro_id": role_id})

    async def set_status(self, employee_id: int, status: str) -> EmployeeData:
        return await self.update_profile(employee_id, {"trang_thai": status})
