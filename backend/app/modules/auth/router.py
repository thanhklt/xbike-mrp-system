from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.dependencies import get_auth_service, get_current_user_payload
from app.modules.auth.schemas import AuthUserResponse, LoginRequest, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]
):
    return await service.authenticate(credentials.email, credentials.password)


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return await service.authenticate(form_data.username, form_data.password)


@router.get("/me", response_model=AuthUserResponse)
async def get_current_user(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return await service.get_current_user(int(payload["sub"]))
