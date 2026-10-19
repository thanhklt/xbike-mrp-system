"""Employee queries and ORM-to-DTO mapping for the lookup service."""

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nhan_vien.dto import EmployeeData, EmployeeListQuery, EmployeePage
from app.modules.nhan_vien.models import User

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
