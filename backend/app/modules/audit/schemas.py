"""UC-43 input/output and persistence records; see specs/use_cases/audit/UC-43.md."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

MAX_AUDIT_ID = 2**31 - 1


class CreationAudit(BaseModel):
    nhan_vien_id: int
    loai_doi_tuong: str
    doi_tuong_id: int
    thao_tac: str = "tao"
    du_lieu_sau: dict[str, Any] | None
    du_lieu_truoc: dict[str, Any] | None = None
    ly_do: str | None = None
    trang_thai_truoc: str | None = None
    trang_thai_sau: str | None = None


ThaoTac = Literal[
    "dang_nhap",
    "tao",
    "sua",
    "xoa_nhap",
    "gui",
    "gui_lai",
    "kiem_tra",
    "bat_dau",
    "duyet",
    "tu_choi",
    "hoan_tat",
    "huy",
    "khoa",
    "mo_khoa",
    "doi_vai_tro",
    "doi_mat_khau",
    "ngung",
    "dung_lai",
    "tao_phien_ban",
    "dung_lai_phien_ban",
]

# Existing exclusion-query callers remain valid; these are not valid v4 stored actions.
ExcludedAction = Literal[
    ThaoTac,
    "ve_nhap",
    "cap_quyen",
    "thu_hoi_quyen",
    "vo_hieu_hoa",
    "ghi_nhan_loi",
    "nhan_xu_ly",
    "giai_quyet",
    "xac_nhan",
]

AuditObject = Literal[
    "nhan_vien",
    "mat_hang",
    "nha_cung_cap",
    "cong_thuc",
    "phieu_nhap",
    "phieu_xuat",
    "yeu_cau_san_xuat",
    "chung_tu_hoan_thanh_san_xuat",
]


def _exact_date(value: object) -> object:
    if value is None or type(value) is date:
        return value
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        raise ValueError("Expected YYYY-MM-DD")
    return value


class AuditListQuery(BaseModel):
    """UC-43 / AC-10..12: structural validation, before accessing audit data."""

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    search: str | None = None
    sort_by: Literal["id", "created_at"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
    nhan_vien_id: int | None = Field(default=None, gt=0, le=MAX_AUDIT_ID)
    loai_doi_tuong: AuditObject | None = None
    doi_tuong_id: int | None = Field(default=None, gt=0, le=MAX_AUDIT_ID)
    thao_tac: ThaoTac | None = None
    bo_thao_tac: ExcludedAction | None = None
    tu_ngay: Annotated[date | None, BeforeValidator(_exact_date)] = None
    den_ngay: Annotated[date | None, BeforeValidator(_exact_date)] = None

    @field_validator("search")
    @classmethod
    def trim_search(cls, value: str | None) -> str | None:
        return (value.strip() or None) if value is not None else None

    @model_validator(mode="after")
    def valid_date_range(self) -> "AuditListQuery":
        if self.tu_ngay == date.min:
            raise ValueError("tu_ngay cannot be the minimum date: UTC conversion would overflow")
        if self.den_ngay == date.max:
            raise ValueError("den_ngay cannot be the maximum date")
        if self.tu_ngay is not None and self.den_ngay is not None and self.tu_ngay > self.den_ngay:
            raise ValueError("tu_ngay must not be after den_ngay")
        return self


@dataclass(frozen=True)
class AuditRecord:
    """Internal evidence crossing the repository/service boundary; not an ORM object."""

    id: int
    nhan_vien_id: int
    loai_doi_tuong: str
    doi_tuong_id: int
    thao_tac: str
    trang_thai_truoc: str | None
    trang_thai_sau: str | None
    du_lieu_truoc: dict[str, Any] | None = field(repr=False)
    du_lieu_sau: dict[str, Any] | None = field(repr=False)
    ly_do: str | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nhan_vien_id: int
    loai_doi_tuong: AuditObject
    doi_tuong_id: int
    thao_tac: ThaoTac
    trang_thai_truoc: str | None
    trang_thai_sau: str | None
    ly_do: str | None
    created_at: datetime
    du_lieu_truoc: dict | None
    du_lieu_sau: dict | None


class AuditDetailResponse(BaseModel):
    success: bool = True
    data: AuditLogResponse
    message: str = "Audit entry retrieved successfully"


class AuditError(BaseModel):
    code: str
    message: str
    details: dict | list


class AuditErrorResponse(BaseModel):
    """The existing audit error envelope; intentionally not the v3 meta envelope."""

    success: Literal[False] = False
    error: AuditError
    timestamp: datetime


class AuditInternalError(BaseModel):
    detail: str
