from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Union

import bcrypt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.errors import UnauthorizedException

password_hasher = PasswordHasher()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Accept new Argon2id hashes and existing bcrypt credentials."""
    try:
        if hashed_password.startswith("$argon2"):
            return password_hasher.verify(hashed_password, plain_password)
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, InvalidHashError, VerificationError):
        return False


def get_password_hash(password: str) -> str:
    """Hash new credentials with Argon2id; never log the input or result."""
    return password_hasher.hash(password)


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
