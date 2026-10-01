from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(subject: Union[str, Any], roles: List[str] = [], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "roles": roles,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as exc:
        raise UnauthorizedException(message="Could not validate credentials", details={"error": str(exc)})


async def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Dependency that extracts payload from current bearer token."""
    return decode_access_token(token)


def require_roles(allowed_roles: List[str]):
    """Role-based access control dependency factory."""
    async def role_checker(payload: dict = Depends(get_current_user_payload)) -> dict:
        user_roles = payload.get("roles", [])
        if not any(role in allowed_roles for role in user_roles):
            raise ForbiddenException(message="You do not have permission to perform this action")
        return payload

    return role_checker
