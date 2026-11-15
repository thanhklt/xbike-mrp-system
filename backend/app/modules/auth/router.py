from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_auth_service, get_current_user_payload
from app.modules.auth.schema import (
    AuthErrorResponse,
    LoginInput,
    LoginResponse,
    MeResponse,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.nhan_vien.service import ResponseMeta


# UC-01 Đăng nhập — Main 2–6: header chống cache (specs/use_cases/identity_access/UC-01.md)
# UC-02 Đăng xuất — A1, A2: không cache kết quả xác minh phiên (specs/use_cases/identity_access/UC-02.md)
def auth_response_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(auth_response_headers)],
    responses={code: {"model": AuthErrorResponse} for code in (401, 403, 409, 422, 500)},
)


# UC-01 Đăng nhập — Main 2–6; A1–A4 (specs/use_cases/identity_access/UC-01.md)
@router.post("/dang_nhap", response_model=LoginResponse, dependencies=[Depends(reject_query)])
async def dang_nhap(
    credentials: LoginInput,
    service: Annotated[AuthService, Depends(get_auth_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> LoginResponse:
    token = await service.login(credentials.ten_dang_nhap, credentials.mat_khau.get_secret_value())
    return LoginResponse(data=token, meta=ResponseMeta(request_id=request_id))


# UC-01 Đăng nhập — R1, D1: OAuth2 bằng tên đăng nhập (specs/use_cases/identity_access/UC-01.md)
@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return await service.authenticate(form_data.username, form_data.password)


# UC-02 Đăng xuất — A1, A2: GET /auth/me xác minh phiên hiện tại (specs/use_cases/identity_access/UC-02.md)
@router.get(
    "/me",
    response_model=MeResponse,
    dependencies=[Depends(reject_query)],
    responses={200: {"headers": {"ETag": {"schema": {"type": "string"}}}}},
)
async def get_current_user(
    payload: Annotated[dict, Depends(get_current_user_payload)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    request_id: Annotated[str, Depends(get_request_id)],
    response: Response,
) -> MeResponse:
    user = await service.get_current_user(payload)
    response.headers["ETag"] = f'"{sha256(user.model_dump_json().encode()).hexdigest()}"'
    return MeResponse(data=user, meta=ResponseMeta(request_id=request_id))
