"""SQLAlchemy employee queries; ORM objects do not leave this adapter."""

from sqlalchemy import false, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.nhan_vien.models import NhanVien
from app.modules.nhan_vien.schemas import (
    MAX_EMPLOYEE_ID,
    EmployeeCredentials,
    EmployeeRecord,
    NhanVienListQuery,
)
from app.shared.records import RecordPage


def employee_record(user: NhanVien) -> EmployeeRecord:
    values = {
        name: getattr(user, name)
        for name in EmployeeRecord.__dataclass_fields__
        if name != "ma_vai_tro"
    }
    return EmployeeRecord(**values, ma_vai_tro=user.role.ma_vai_tro if user.role else None)


class SqlAlchemyNhanVienRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_employees(self, params: NhanVienListQuery) -> RecordPage[EmployeeRecord]:
        query = select(NhanVien)
        if params.q:
            query = query.where(
                or_(
                    NhanVien.ma_nhan_vien.icontains(params.q, autoescape=True),
                    NhanVien.ho_ten.icontains(params.q, autoescape=True),
                )
            )
        if params.vai_tro_id is not None:
            query = query.where(
                NhanVien.vai_tro_id == params.vai_tro_id
                if params.vai_tro_id <= MAX_EMPLOYEE_ID
                else false()
            )
        if params.trang_thai is not None:
            query = query.where(NhanVien.trang_thai == params.trang_thai)
        total = await self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = (params.page - 1) * params.page_size
        employees: list[EmployeeRecord] = []
        if offset < total:
            sort_column = getattr(NhanVien, params.sort.removeprefix("-"))
            ordering = sort_column.desc() if params.sort.startswith("-") else sort_column.asc()
            records = (
                await self.session.scalars(
                    query.order_by(ordering, NhanVien.id).offset(offset).limit(params.page_size)
                )
            ).all()
            employees = [employee_record(user) for user in records]
        return RecordPage(employees, total)

    async def get_by_id(self, employee_id: int) -> EmployeeRecord | None:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            return None
        user = await self.session.scalar(select(NhanVien).where(NhanVien.id == employee_id))
        return employee_record(user) if user is not None else None

    async def find_by_username(self, identifier: str) -> EmployeeCredentials | None:
        user = await self.session.scalar(
            select(NhanVien).where(NhanVien.ten_dang_nhap == identifier)
        )
        return employee_credentials(user) if user is not None else None

    async def find_unique_by_email(self, identifier: str) -> EmployeeCredentials | None:
        matches = (
            await self.session.scalars(
                select(NhanVien).where(NhanVien.email == identifier).limit(2)
            )
        ).all()
        return employee_credentials(matches[0]) if len(matches) == 1 else None

    async def get_credentials_by_id(self, employee_id: int) -> EmployeeCredentials | None:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            return None
        user = await self.session.scalar(select(NhanVien).where(NhanVien.id == employee_id))
        return employee_credentials(user) if user is not None else None

    async def lock_credentials_by_id(self, employee_id: int) -> EmployeeCredentials | None:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            return None
        user = await self.session.scalar(
            select(NhanVien)
            .where(NhanVien.id == employee_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return employee_credentials(user) if user is not None else None

    async def set_password_hash(self, employee_id: int, password_hash: str) -> None:
        await self.session.execute(
            update(NhanVien).where(NhanVien.id == employee_id).values(mat_khau=password_hash)
        )


def employee_credentials(user: NhanVien) -> EmployeeCredentials:
    profile = employee_record(user)
    values = {name: getattr(profile, name) for name in EmployeeRecord.__dataclass_fields__}
    return EmployeeCredentials(
        **values,
        roles=[profile.ma_vai_tro] if profile.ma_vai_tro else [],
        password_hash=user.mat_khau,
    )
