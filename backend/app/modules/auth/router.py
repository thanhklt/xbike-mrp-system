from hashlib import sha256
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.request_context import get_request_id, reject_query
from app.dependencies import get_auth_service, get_current_user_payload
from app.modules.auth.schemas import (
    AuthErrorResponse,
    DoiMatKhauInput,
    LoginInput,
    LoginRequest,
    LoginResponse,
    MeResponse,
    PasswordChanged,
    PasswordChangeResponse,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.users.schemas import ResponseMeta


def auth_response_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(auth_response_headers)],
    responses={code: {"model": AuthErrorResponse} for code in (401, 403, 409, 422, 500)},
)


@router.post("/dang_nhap", response_model=LoginResponse, dependencies=[Depends(reject_query)])
async def dang_nhap(
    credentials: LoginInput,
    service: Annotated[AuthService, Depends(get_auth_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> LoginResponse:
    token = await service.login(credentials.ten_dang_nhap, credentials.mat_khau.get_secret_value())
    return LoginResponse(data=token, meta=ResponseMeta(request_id=request_id))

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[AuthService, Depends(get_auth_service)],
):
    return await service.authenticate(form_data.username, form_data.password)


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


@router.post(
    "/doi_mat_khau", response_model=PasswordChangeResponse, dependencies=[Depends(reject_query)]
)
async def doi_mat_khau(
    credentials: DoiMatKhauInput,
    payload: Annotated[dict, Depends(get_current_user_payload)],
    service: Annotated[AuthService, Depends(get_auth_service)],
    request_id: Annotated[str, Depends(get_request_id)],
) -> PasswordChangeResponse:
    await service.change_password(
        payload,
        credentials.mat_khau_hien_tai.get_secret_value(),
        credentials.mat_khau_moi.get_secret_value(),
    )
    return PasswordChangeResponse(data=PasswordChanged(), meta=ResponseMeta(request_id=request_id))
