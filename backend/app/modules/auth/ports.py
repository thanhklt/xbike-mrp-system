"""Credential and current-principal lookup contract."""

from typing import Protocol

from app.modules.auth.schemas import AuthEmployee


class AuthRepository(Protocol):
    async def find_by_username(self, identifier: str) -> AuthEmployee | None: ...

    async def find_unique_by_email(self, identifier: str) -> AuthEmployee | None: ...

    async def get_by_id(self, employee_id: int) -> AuthEmployee | None: ...

    async def lock_by_id(self, employee_id: int) -> AuthEmployee | None: ...

    async def set_password_hash(self, employee_id: int, password_hash: str) -> None: ...
