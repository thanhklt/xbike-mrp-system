"""Login and current-account policy, independent of HTTP and database sessions."""

from app.core.config import settings
from app.core.errors import InactiveAccountException, UnauthorizedException
from app.core.security import create_access_token, decode_access_token, verify_password
from app.modules.auth.ports import AuthRepository
from app.modules.auth.schemas import AuthUserResponse, TokenResponse


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

    async def authenticate(self, identifier: str, password: str) -> TokenResponse:
        user = await self.repository.find_by_username(identifier)
        if user is None:
            user = await self.repository.find_unique_by_email(identifier)
        if (
            user is None
            or not verify_password(password, user.password_hash)
            or user.trang_thai != "hoat_dong"
        ):
            raise UnauthorizedException(message="Invalid username/email or password")
        return TokenResponse(
            access_token=create_access_token(subject=user.id, roles=user.roles),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def current_payload(self, token: str) -> dict:
        payload = decode_access_token(token)
        try:
            user_id = int(payload["sub"])
        except (KeyError, ValueError, TypeError) as exc:
            raise UnauthorizedException(message="Invalid token subject") from exc
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        if user.trang_thai != "hoat_dong":
            raise InactiveAccountException()
        payload["roles"] = user.roles
        return payload

    async def get_current_user(self, employee_id: int) -> AuthUserResponse:
        user = await self.repository.get_by_id(employee_id)
        if user is None:
            raise UnauthorizedException(message="Employee no longer exists")
        return AuthUserResponse.model_validate(user.model_dump())
