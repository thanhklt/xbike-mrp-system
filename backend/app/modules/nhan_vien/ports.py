"""Employee lookup contract owned by the application service."""

from typing import Protocol

from app.modules.nhan_vien.dto import EmployeeData, EmployeeListQuery, EmployeePage


class EmployeeRepository(Protocol):
    async def list(self, query: EmployeeListQuery) -> EmployeePage:
        """Return one ordered page and the total matching all filters."""
        ...

    async def get_by_id(self, employee_id: int) -> EmployeeData | None:
        """Return a snapshot, or None for a missing or unrepresentable ID."""
        ...
