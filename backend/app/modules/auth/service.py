"""JWT orchestration through the employee module's public service."""

from app.config.settings import settings
from app.core.errors import UnauthorizedException
from app.core.security import create_access_token, decode_access_token
from app.modules.auth.schema import TokenRead, TokenResponse
from app.modules.nhan_vien.service import AuthIdentity, NhanVienRead, NhanVienService


def _issue_token(identity: AuthIdentity) -> TokenRead:
    return TokenRead(
        access_token=create_access_token(
            subject=identity.profile.id,
            roles=identity.roles,
            credential_version=identity.credential_version,
        ),
        expires_in=settings.access_token_expire_minutes * 60,
        nhan_vien=identity.profile,
    )


class AuthService:
    def __init__(self, employees: NhanVienService):
        self.employees = employees

    async def login(self, username: str, password: str) -> TokenRead:
        identity = await self.employees.authenticate_employee(username, password)
        await self.employees.record_login(identity.profile.id)
        return _issue_token(identity)

    async def authenticate(self, identifier: str, password: str) -> TokenResponse:
        identity = await self.employees.authenticate_employee(
            identifier, password, allow_email=True
        )
        await self.employees.record_login(identity.profile.id)
        result = _issue_token(identity)
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
        identity = await self.employees.get_auth_identity(
            int(subject), credential_version=payload.get("pwdv")
        )
        payload["roles"] = identity.roles
        return payload

    async def get_current_user(self, payload: dict) -> NhanVienRead:
        identity = await self.employees.get_auth_identity(
            int(payload["sub"]), credential_version=payload.get("pwdv")
        )
        return identity.profile

    async def change_password(
        self, payload: dict, current_password: str, new_password: str
    ) -> None:
        await self.employees.change_password(
            int(payload["sub"]),
            current_password,
            new_password,
            credential_version=payload.get("pwdv"),
        )
