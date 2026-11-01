from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.modules.nhan_vien.service import NhanVienRead, ResponseMeta

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Password = Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid") # Nếu dư sẽ báo lỗi

    ten_dang_nhap: Username
    mat_khau: Password


class DoiMatKhauInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_khau_hien_tai: Password
    mat_khau_moi: SecretStr = Field(min_length=8, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class TokenRead(TokenResponse):
    nhan_vien: NhanVienRead


class LoginResponse(BaseModel):
    data: TokenRead
    meta: ResponseMeta


class MeResponse(BaseModel):
    data: NhanVienRead
    meta: ResponseMeta


class PasswordChanged(BaseModel):
    da_doi: Literal[True] = True


class PasswordChangeResponse(BaseModel):
    data: PasswordChanged
    meta: ResponseMeta


class AuthError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class AuthErrorResponse(BaseModel):
    error: AuthError
    meta: ResponseMeta
