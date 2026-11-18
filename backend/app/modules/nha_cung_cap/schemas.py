"""API schemas matching the PostgreSQL model; no generated sample values."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

SupplierSort = Literal["id", "-id", "ma_ncc", "-ma_ncc", "ten_ncc", "-ten_ncc"]


def nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Supplier information must not be blank")
    return value


SupplierText = Annotated[str, Field(min_length=1), AfterValidator(nonblank)]


class NhaCungCapCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten_ncc: SupplierText
    so_dien_thoai: SupplierText
    dia_chi: SupplierText
    phuong: SupplierText
    tinh: SupplierText


class NhaCungCapPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ten_ncc: SupplierText | SkipJsonSchema[None] = None
    so_dien_thoai: SupplierText | SkipJsonSchema[None] = None
    dia_chi: SupplierText | SkipJsonSchema[None] = None
    phuong: SupplierText | SkipJsonSchema[None] = None
    tinh: SupplierText | SkipJsonSchema[None] = None

    @field_validator("ten_ncc", "so_dien_thoai", "dia_chi", "phuong", "tinh")
    @classmethod
    def reject_null(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Supplier information must not be null")
        return value


class NhaCungCapListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    q: str | None = None
    tinh: str | None = Field(
        default=None, description="Tìm một phần tỉnh/thành, không phân biệt hoa/thường và dấu."
    )
    phuong: str | None = Field(
        default=None, description="Tìm một phần phường/xã, không phân biệt hoa/thường và dấu."
    )
    sort: SupplierSort = "id"

    @field_validator("q", "tinh", "phuong")
    @classmethod
    def normalize_filter(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ma_ncc: str
    ten_ncc: str
    so_dien_thoai: str
    dia_chi: str
    phuong: str
    tinh: str


class NhaCungCapRead(SupplierResponse):
    """Current supplier information, Catalog UC-13/44."""


class ResponseMeta(BaseModel):
    request_id: str


class ListResponseMeta(ResponseMeta):
    page: int
    page_size: int
    total: int
    total_pages: int


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
