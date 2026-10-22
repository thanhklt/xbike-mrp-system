"""Employee lookup contract owned by the application service."""

from typing import Protocol

from app.modules.nhan_vien.dto import (
    EmployeeData,
    EmployeeListQuery,
    EmployeePage,
    NewEmployee,
    RoleData,
    RolePage,
)


class EmployeeRepository(Protocol):
    async def list(self, query: EmployeeListQuery) -> EmployeePage:
        """Return one ordered page and the total matching all filters."""
        ...

    async def get_by_id(self, employee_id: int) -> EmployeeData | None:
        """Return a snapshot, or None for a missing or unrepresentable ID."""
        ...

    async def list_roles(self, page: int, page_size: int) -> RolePage: ...


class EmployeeWriteRepository(Protocol):
    async def lock_writes(self) -> None:
        """Serialize employee mutations before refreshing actor and target rows."""
        ...

    async def get_for_update(self, employee_id: int) -> EmployeeData | None: ...

    async def get_role(self, role_id: int) -> RoleData | None: ...

    async def active_admin_count(self) -> int: ...

    async def create(self, employee: NewEmployee) -> EmployeeData: ...

    async def update_profile(
        self, employee_id: int, changes: dict[str, object]
    ) -> EmployeeData: ...

    async def set_role(self, employee_id: int, role_id: int) -> EmployeeData: ...

    async def set_status(self, employee_id: int, status: str) -> EmployeeData: ...
