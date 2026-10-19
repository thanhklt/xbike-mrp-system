"""ORM-independent data exchanged between employee services and repositories."""

from dataclasses import dataclass
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
