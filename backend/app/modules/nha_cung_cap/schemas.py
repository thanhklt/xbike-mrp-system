"""API schemas matching the PostgreSQL model; no generated sample values."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from app.modules.users.schemas import ListResponseMeta, ResponseMeta

SupplierSort = Literal["id", "-id", "ma_ncc", "-ma_ncc", "ten_ncc", "-ten_ncc"]


def require_nonzero_supplier_code(value: str) -> str:
    if value == "NCC-000000":
        raise ValueError("Supplier code must be NCC-000001 through NCC-999999")
    return value


SupplierCode = Annotated[
    str, Field(pattern=r"^NCC-[0-9]{6}$"), AfterValidator(require_nonzero_supplier_code)
]


class NhaCungCapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ma_ncc: SupplierCode
    ten_ncc: str = Field(min_length=1)
    so_dien_thoai: str | None = None
    dia_chi: str | None = None
    phuong: str | None = None
    tinh: str | None = None


class NhaCungCapPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ma_ncc: SupplierCode | None = None
    ten_ncc: str | None = Field(default=None, min_length=1)
    so_dien_thoai: str | None = None
    dia_chi: str | None = None
    phuong: str | None = None
    tinh: str | None = None

    @field_validator("ma_ncc", "ten_ncc")
    @classmethod
    def reject_explicit_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("This field cannot be null when supplied")
        return value


class NhaCungCapListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    tinh: str | None = None
    phuong: str | None = None
    sort: SupplierSort = "id"


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_ncc: str
    ten_ncc: str | None
    so_dien_thoai: str | None
    dia_chi: str | None
    phuong: str | None
    tinh: str | None


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ma_ncc: str
    ten_ncc: str | None = None
    so_dien_thoai: str | None = None
    dia_chi: str | None = None
    phuong: str | None = None
    tinh: str | None = None


class NhaCungCapRead(SupplierResponse):
    """Legacy rows may have no supplier name, as explicitly agreed for GET."""


class NhaCungCapListResponse(BaseModel):
    data: list[NhaCungCapRead]
    meta: ListResponseMeta


class NhaCungCapDetailResponse(BaseModel):
    data: NhaCungCapRead
    meta: ResponseMeta


class SupplierError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]]


class SupplierErrorResponse(BaseModel):
    error: SupplierError
    meta: ResponseMeta
