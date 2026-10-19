import hashlib
import hmac
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
    """Read Argon2id credentials and legacy bcrypt without truncating passwords."""
    try:
        if hashed_password.startswith("$argon2id$"):
            return password_hasher.verify(hashed_password, plain_password)
        encoded = plain_password.encode("utf-8")
        if len(encoded) > 72:
            return False
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except (ValueError, InvalidHashError, VerificationError):
        return False


def get_password_hash(password: str) -> str:
    """All newly written passwords use Argon2id; bcrypt remains read-only."""
    return password_hasher.hash(password)


def password_version(password_hash: str) -> str:
    """Keyed credential version; neither the password nor its hash enters JWTs."""
    return hmac.new(
        settings.SECRET_KEY.encode(),
        b"xbike-password-version\0" + password_hash.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(
    subject: Union[str, Any],
    roles: Optional[List[str]] = None,
    expires_delta: Optional[timedelta] = None,
    *,
    credential_version: str | None = None,
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
    if credential_version is not None:
        to_encode["pwdv"] = credential_version
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        return payload
    except JWTError as exc:
        raise UnauthorizedException(message="Could not validate credentials") from exc
