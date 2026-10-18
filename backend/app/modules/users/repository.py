"""SQLAlchemy employee queries; ORM objects do not leave this adapter."""

from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.schemas import MAX_EMPLOYEE_ID, EmployeeRecord, NhanVienListQuery
from app.shared.records import RecordPage


def employee_record(user: User) -> EmployeeRecord:
    values = {
        name: getattr(user, name)
        for name in EmployeeRecord.__dataclass_fields__
        if name != "ma_vai_tro"
    }
    return EmployeeRecord(**values, ma_vai_tro=user.role.ma_vai_tro if user.role else None)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_employees(self, params: NhanVienListQuery) -> RecordPage[EmployeeRecord]:
        query = select(User)
        if params.q:
            query = query.where(
                or_(
                    User.ma_nhan_vien.icontains(params.q, autoescape=True),
                    User.ho_ten.icontains(params.q, autoescape=True),
                )
            )
        if params.vai_tro_id is not None:
            query = query.where(
                User.vai_tro_id == params.vai_tro_id
                if params.vai_tro_id <= MAX_EMPLOYEE_ID
                else false()
            )
        if params.trang_thai is not None:
            query = query.where(User.trang_thai == params.trang_thai)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        employees: list[EmployeeRecord] = []
        if offset < total:
            sort_column = getattr(User, params.sort.removeprefix("-"))
            ordering = sort_column.desc() if params.sort.startswith("-") else sort_column.asc()
            records = (
                await self.session.scalars(
                    query.order_by(ordering, User.id).offset(offset).limit(params.page_size)
                )
            ).all()
            employees = [employee_record(user) for user in records]
        return RecordPage(employees, total)

    async def get_by_id(self, employee_id: int) -> EmployeeRecord | None:
        user = await self.session.scalar(select(User).where(User.id == employee_id))
        return employee_record(user) if user is not None else None
