from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, List, Optional, Union

import bcrypt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    roles: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "roles": roles or [],
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise UnauthorizedException(
            message="Could not validate credentials", details={"error": str(exc)}
        ) from exc


async def get_current_user_payload(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[AsyncSession, Depends(get_db)]
) -> dict:
    """Validate the token and reload permissions from the employee record."""
    from app.modules.users.models import User

    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise UnauthorizedException(message="Invalid token subject") from exc
    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise UnauthorizedException(message="Employee no longer exists")
    if user.trang_thai != "hoat_dong":
        raise UnauthorizedException(message="Employee account is not active")
    payload["roles"] = employee_roles(user)
    return payload


def employee_roles(user) -> list[str]:
    role = user.role.ma_vai_tro if user.role else None
    return [role] if role else []


def require_roles(allowed_roles: List[str]):
    """Role-based access control dependency factory."""

    async def role_checker(payload: Annotated[dict, Depends(get_current_user_payload)]) -> dict:
        user_roles = payload.get("roles", [])
        if not any(role in allowed_roles for role in user_roles):
            raise ForbiddenException(message="You do not have permission to perform this action")
        return payload

    return role_checker
