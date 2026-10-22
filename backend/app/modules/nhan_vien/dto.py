"""ORM-independent data exchanged between employee services and repositories."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class EmployeeData:
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


@dataclass(frozen=True)
class EmployeeListQuery:
    """Validated filters and pagination; sort uses the employee API whitelist."""

    page: int
    page_size: int
    q: str | None
    sort: str
    vai_tro_id: int | None
    trang_thai: str | None


@dataclass(frozen=True)
class EmployeePage:
    items: tuple[EmployeeData, ...]
    total: int


@dataclass(frozen=True)
class NewEmployee:
    ten_dang_nhap: str
    ma_nhan_vien: str
    vai_tro_id: int
    password_hash: str = field(repr=False)
    profile: dict[str, object]


@dataclass(frozen=True)
class RoleData:
    id: int
    ma_vai_tro: str | None
    ten_vai_tro: str | None


@dataclass(frozen=True)
class RolePage:
    items: tuple[RoleData, ...]
    total: int
