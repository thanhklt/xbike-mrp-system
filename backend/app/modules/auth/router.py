from datetime import timedelta
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import create_access_token, get_current_user_payload
from app.modules.auth.schemas import AuthUserResponse, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    """Authenticate user with email and password to receive JWT token."""
    # In production, query user from database and verify password hash
    if credentials.password == "wrong":
        raise UnauthorizedException(message="Invalid email or password")

    # Sample token creation for testing / starter template
    access_token = create_access_token(
        subject=credentials.email,
        roles=["ADMIN", "MANAGER"],
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login for Swagger UI."""
    access_token = create_access_token(
        subject=form_data.username,
        roles=["ADMIN"],
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user(payload: dict = Depends(get_current_user_payload)):
    """Return currently authenticated user profile."""
    return AuthUserResponse(
        id=1,
        email=payload.get("sub", "admin@xbike.local"),
        full_name="xBike System Administrator",
        roles=payload.get("roles", ["ADMIN"]),
        is_active=True,
    )
