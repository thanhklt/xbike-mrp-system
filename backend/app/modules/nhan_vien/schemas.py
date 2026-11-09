"""Employee API schemas and internal records shared with the repository."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, SecretStr, field_validator

MAX_EMPLOYEE_ID = 2**31 - 1


@dataclass(frozen=True)
class EmployeeRecord:
    """Internal employee data, validated for the selected public projection in the service."""

    id: int
    ma_nhan_vien: str
    ho_ten: str | None
    vai_tro_id: int | None
    ma_vai_tro: str | None
    trang_thai: str | None
    ten_dang_nhap: str
    ngay_sinh: date | None
    so_dien_thoai: str | None
    email: str | None
    ngay_vao_lam: date | None
    he_so_luong: Decimal | None


EmployeeStatus = Literal["hoat_dong", "bi_khoa"]
RoleCode = Literal["nhan_vien", "quan_ly", "quan_tri_vien"]
EmployeeSort = Literal[
    "id",
    "-id",
    "ma_nhan_vien",
    "-ma_nhan_vien",
    "ho_ten",
    "-ho_ten",
    "ten_dang_nhap",
    "-ten_dang_nhap",
]


class NhanVienListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    sort: EmployeeSort = "id"
    vai_tro_id: int | None = Field(default=None, gt=0)
    trang_thai: EmployeeStatus | None = None


class NhanVienAssignmentRead(BaseModel):
    """Limited projection for managers assigning work."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    ma_nhan_vien: str
    ho_ten: str | None
    vai_tro_id: int | None
    ma_vai_tro: RoleCode | None
    trang_thai: EmployeeStatus


class NhanVienRead(NhanVienAssignmentRead):
    ten_dang_nhap: str
    ngay_sinh: date | None
    so_dien_thoai: str | None
    email: str | None
    ngay_vao_lam: date | None
    he_so_luong: Decimal | None = Field(ge=0)


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


class NhanVienDetailResponse(BaseModel):
    data: NhanVienRead | NhanVienAssignmentRead
    meta: ResponseMeta


class NhanVienListResponse(BaseModel):
    data: list[NhanVienRead | NhanVienAssignmentRead]
    meta: ListResponseMeta


class EmployeeCredentials(BaseModel):
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


class AuthIdentity(BaseModel):
    """Verified identity exposed to auth; credential hashes stay internal."""

    profile: NhanVienRead
    roles: list[str]
    credential_version: str = Field(repr=False, exclude=True)


def _date_string(value: object) -> object:
    if value is not None and (
        not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-"
    ):
        raise ValueError("Use a date string in YYYY-MM-DD format")
    return value


def _decimal_string(value: object) -> object:
    if value is not None and not isinstance(value, str):
        raise ValueError("Use a decimal JSON string")
    return value


ProfileDate = Annotated[date | None, BeforeValidator(_date_string)]
SalaryCoefficient = Annotated[
    Annotated[Decimal, Field(ge=0, max_digits=5, decimal_places=2)] | None,
    BeforeValidator(_decimal_string),
]


class NhanVienPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ho_ten: str | None = None
    ngay_sinh: ProfileDate = None
    so_dien_thoai: str | None = None
    email: str | None = None
    ngay_vao_lam: ProfileDate = None
    he_so_luong: SalaryCoefficient = None


class NhanVienCreate(NhanVienPatch):
    ten_dang_nhap: str = Field(min_length=1, max_length=255)
    ma_nhan_vien: str = Field(pattern=r"^NV-[0-9]{6}$")
    vai_tro_id: int = Field(strict=True, gt=0, le=MAX_EMPLOYEE_ID)
    mat_khau: SecretStr = Field(min_length=8, max_length=1024, repr=False, exclude=True)

    @field_validator("ma_nhan_vien")
    @classmethod
    def valid_employee_code(cls, value: str) -> str:
        if value == "NV-000000":
            raise ValueError("Employee code must be nonzero")
        return value


class DoiVaiTroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vai_tro_id: int = Field(strict=True, gt=0, le=MAX_EMPLOYEE_ID)


class LyDoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ly_do: str = Field(min_length=1)


class VaiTroListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class VaiTroRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_vai_tro: RoleCode
    ten_vai_tro: str
    mo_ta: str | None


class VaiTroListResponse(BaseModel):
    data: list[VaiTroRead]
    meta: ListResponseMeta


@dataclass(frozen=True)
class NewEmployee:
    ten_dang_nhap: str
    ma_nhan_vien: str
    vai_tro_id: int
    password_hash: str = field(repr=False)
    profile: dict[str, object]
