"""Employee queries needed by the user application service."""

from typing import Protocol

from app.modules.users.schemas import EmployeeRecord, NhanVienListQuery
from app.shared.records import RecordPage


class UserRepository(Protocol):
    async def list_employees(self, params: NhanVienListQuery) -> RecordPage[EmployeeRecord]: ...

    async def get_by_id(self, employee_id: int) -> EmployeeRecord | None: ...
