"""API schemas matching the PostgreSQL model; no generated sample values."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nhan_vien_id: int
    loai_doi_tuong: Literal[
        "nhan_vien",
        "vai_tro",
        "mat_hang",
        "nha_cung_cap",
        "cong_thuc",
        "phieu_nhap",
        "phieu_xuat",
        "yeu_cau_san_xuat",
        "lenh_san_xuat",
        "chung_tu_hoan_thanh_san_xuat",
        "phieu_dieu_chinh_kho",
        "phieu_loi_dieu_chinh",
    ]
    doi_tuong_id: int
    thao_tac: Literal[
        "tao",
        "sua",
        "xoa_nhap",
        "gui",
        "bat_dau",
        "duyet",
        "tu_choi",
        "ve_nhap",
        "hoan_tat",
        "cap_quyen",
        "thu_hoi_quyen",
        "vo_hieu_hoa",
        "huy",
        "ghi_nhan_loi",
        "nhan_xu_ly",
        "mo_lai",
        "giai_quyet",
    ]
    du_lieu_truoc: dict | None
    du_lieu_sau: dict | None
    ly_do: str | None
    created_at: datetime
