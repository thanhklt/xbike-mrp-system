"""SQLAlchemy employee queries; ORM objects do not leave this adapter."""

from sqlalchemy import false, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DuplicateCodeException
from app.modules.nhan_vien.models import NhanVien, VaiTro
from app.modules.nhan_vien.schemas import (
    MAX_EMPLOYEE_ID,
    EmployeeCredentials,
    EmployeeRecord,
    NewEmployee,
    NhanVienListQuery,
    VaiTroListQuery,
    VaiTroRead,
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

    async def get_for_share(self, employee_id: int) -> EmployeeRecord | None:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            return None
        user = await self.session.scalar(
            select(NhanVien)
            .where(NhanVien.id == employee_id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
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

    async def get_for_update(self, employee_id: int) -> EmployeeRecord | None:
        if not 1 <= employee_id <= MAX_EMPLOYEE_ID:
            return None
        user = await self.session.scalar(
            select(NhanVien)
            .where(NhanVien.id == employee_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return employee_record(user) if user is not None else None

    async def create(self, employee: NewEmployee) -> EmployeeRecord:
        user = NhanVien(
            ten_dang_nhap=employee.ten_dang_nhap,
            ma_nhan_vien=employee.ma_nhan_vien,
            vai_tro_id=employee.vai_tro_id,
            mat_khau=employee.password_hash,
            trang_thai="hoat_dong",
            **employee.profile,
        )
        self.session.add(user)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            original = exc.orig
            if (
                getattr(original, "sqlstate", None) == "23505"
                or getattr(original, "sqlite_errorname", None) == "SQLITE_CONSTRAINT_UNIQUE"
            ):
                raise DuplicateCodeException() from exc
            raise
        # Read normalized database values (notably NUMERIC(5, 2)) so the ETag
        # returned by POST matches an immediate GET of the persisted resource.
        await self.session.refresh(user)
        return employee_record(user)

    async def _update(self, employee_id: int, changes: dict[str, object]) -> EmployeeRecord:
        if changes:
            await self.session.execute(
                update(NhanVien)
                .where(NhanVien.id == employee_id)
                .values(**changes)
                .execution_options(synchronize_session=False)
            )
        # Refresh the identity map, including role, before generating response/ETag/audit.
        result = await self.get_for_update(employee_id)
        assert result is not None  # The service holds this employee's row lock.
        return result

    async def update_profile(self, employee_id: int, changes: dict[str, object]) -> EmployeeRecord:
        return await self._update(employee_id, changes)

    async def set_role(self, employee_id: int, role_id: int) -> EmployeeRecord:
        return await self._update(employee_id, {"vai_tro_id": role_id})

    async def set_status(self, employee_id: int, status: str) -> EmployeeRecord:
        return await self._update(employee_id, {"trang_thai": status})

    async def get_role(self, role_id: int) -> VaiTroRead | None:
        if not 1 <= role_id <= MAX_EMPLOYEE_ID:
            return None
        role = await self.session.get(VaiTro, role_id)
        return VaiTroRead.model_validate(role) if role is not None else None

    async def list_roles(self, params: VaiTroListQuery) -> RecordPage[VaiTroRead]:
        total = await self.session.scalar(select(func.count()).select_from(VaiTro)) or 0
        offset = (params.page - 1) * params.page_size
        if offset >= total:
            return RecordPage([], total)
        roles = await self.session.scalars(
            select(VaiTro).order_by(VaiTro.id).offset(offset).limit(params.page_size)
        )
        return RecordPage([VaiTroRead.model_validate(role) for role in roles], total)


def employee_credentials(user: NhanVien) -> EmployeeCredentials:
    profile = employee_record(user)
    values = {name: getattr(profile, name) for name in EmployeeRecord.__dataclass_fields__}
    return EmployeeCredentials(
        **values,
        roles=[profile.ma_vai_tro] if profile.ma_vai_tro else [],
        password_hash=user.mat_khau,
    )
