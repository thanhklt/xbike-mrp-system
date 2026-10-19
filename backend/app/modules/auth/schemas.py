from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.modules.users.schemas import NhanVienRead, ResponseMeta

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Password = Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten_dang_nhap: Username
    mat_khau: Password


class DoiMatKhauInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mat_khau_hien_tai: Password
    mat_khau_moi: SecretStr = Field(min_length=8, max_length=1024)


class LoginRequest(BaseModel):
    # Demo .local emails and usernames in seed.sql are valid login identifiers.
    email: Username
    password: Password


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


class AuthEmployee(BaseModel):
    """Internal credentials/principal; never used as an HTTP response schema."""

    id: int
    email: str | None
    ho_ten: str | None
    ten_dang_nhap: str
    roles: list[str]
    trang_thai: str | None
    password_hash: str = Field(repr=False, exclude=True)
    ma_nhan_vien: str
    vai_tro_id: int | None
    ma_vai_tro: str | None
    ngay_sinh: date | None
    so_dien_thoai: str | None
    ngay_vao_lam: date | None
    he_so_luong: Decimal | None
