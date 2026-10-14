from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import (
    create_access_token,
    employee_roles,
    get_current_user_payload,
    verify_password,
)
from app.modules.auth.schemas import AuthUserResponse, LoginRequest, TokenResponse
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def authenticate(db: AsyncSession, identifier: str, password: str):
    # Username is unique; email is not unique in the source schema.
    user = await db.scalar(select(User).where(User.ten_dang_nhap == identifier))
    if user is None:
        matches = (await db.scalars(select(User).where(User.email == identifier))).all()
        user = matches[0] if len(matches) == 1 else None
    if user is None or not verify_password(password, user.mat_khau):
        raise UnauthorizedException(message="Invalid username/email or password")
    return TokenResponse(
        access_token=create_access_token(subject=user.id, roles=employee_roles(user)),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    return await authenticate(db, credentials.email, credentials.password)


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await authenticate(db, form_data.username, form_data.password)


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await db.get(User, int(payload["sub"]))
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.ho_ten,
        ten_dang_nhap=user.ten_dang_nhap,
        roles=employee_roles(user),
    )
