from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    # Demo .local emails and usernames in seed.sql are valid login identifiers.
    email: str = Field(min_length=1)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(BaseModel):
    id: int
    email: str | None
    full_name: str | None
    ten_dang_nhap: str
    roles: list[str]


class AuthEmployee(BaseModel):
    """Internal credentials/principal; never used as an HTTP response schema."""

    id: int
    email: str | None
    full_name: str | None
    ten_dang_nhap: str
    roles: list[str]
    trang_thai: str | None
    password_hash: str = Field(repr=False, exclude=True)
