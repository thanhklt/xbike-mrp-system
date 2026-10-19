"""Authentication and atomic password changes, independent of HTTP/ORM sessions."""

import asyncio
import hmac

from app.core.config import settings
from app.core.errors import (
    ForbiddenException,
    InactiveAccountException,
    InvalidCredentialsException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    password_version,
    verify_password,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.auth.ports import AuthRepository
from app.modules.auth.schemas import AuthEmployee, TokenRead, TokenResponse
from app.modules.users.schemas import MAX_EMPLOYEE_ID, NhanVienRead


def _require_active(user: AuthEmployee) -> None:
    if user.trang_thai != "hoat_dong":
        raise InactiveAccountException()
    if not {"quan_tri_vien", "quan_ly", "nhan_vien"}.intersection(user.roles):
        raise ForbiddenException()


def _require_current_password(user: AuthEmployee, payload: dict) -> None:
    version = payload.get("pwdv")
    if (
        not isinstance(version, str)
        or not version.isascii()
        or not hmac.compare_digest(version, password_version(user.password_hash))
    ):
        raise UnauthorizedException(message="Please sign in again")


class AuthService:
    def __init__(self, repository: AuthRepository, audit: AuditWriter, transaction: Transaction):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction

    async def _issue_token(self, user: AuthEmployee | None, password: str) -> TokenRead:
        if user is None or not await asyncio.to_thread(
            verify_password, password, user.password_hash
        ):
            raise InvalidCredentialsException()
        _require_active(user)
        return TokenRead(
            access_token=create_access_token(
                subject=user.id,
                roles=user.roles,
                credential_version=password_version(user.password_hash),
            ),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            nhan_vien=NhanVienRead.model_validate(user),
        )

    async def login(self, username: str, password: str) -> TokenRead:
        return await self._issue_token(await self.repository.find_by_username(username), password)

    async def authenticate(self, identifier: str, password: str) -> TokenResponse:
        """Compatibility for the existing /login and OAuth2 /token endpoints."""
        user = await self.repository.find_by_username(identifier)
        if user is None:
            user = await self.repository.find_unique_by_email(identifier)
        result = await self._issue_token(user, password)
        return TokenResponse(**result.model_dump(exclude={"nhan_vien"}))

    async def current_payload(self, token: str) -> dict:
        payload = decode_access_token(token)
        subject = payload.get("sub", "")
        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdecimal()
            or len(subject) > 10
        ):
            raise UnauthorizedException(message="Invalid token subject")
        user_id = int(subject)
        if not 1 <= user_id <= MAX_EMPLOYEE_ID:
            raise UnauthorizedException(message="Invalid token subject")
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        _require_active(user)
        _require_current_password(user, payload)
        payload["roles"] = user.roles
        return payload

    async def get_current_user(self, payload: dict) -> NhanVienRead:
        user = await self.repository.get_by_id(int(payload["sub"]))
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        _require_active(user)
        _require_current_password(user, payload)
        return NhanVienRead.model_validate(user)

    async def change_password(
        self, payload: dict, current_password: str, new_password: str
    ) -> None:
        async with self.transaction:
            user = await self.repository.lock_by_id(int(payload["sub"]))
            if user is None:
                raise UnauthorizedException(message="Employee no longer exists")
            _require_active(user)
            _require_current_password(user, payload)
            if not await asyncio.to_thread(verify_password, current_password, user.password_hash):
                raise InvalidCredentialsException()
            new_hash = await asyncio.to_thread(get_password_hash, new_password)
            await self.repository.set_password_hash(user.id, new_hash)
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=user.id,
                    loai_doi_tuong="nhan_vien",
                    doi_tuong_id=user.id,
                    thao_tac="sua",
                    du_lieu_sau={"da_doi_mat_khau": True},
                )
            )
