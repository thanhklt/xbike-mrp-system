"""ORM mapping matching infra/postgres/init.sql."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LichSuThaoTac(Base):
    __tablename__ = "LichSuThaoTac"
    __table_args__ = (
        Index(
            "LichSuThaoTac_loai_doi_tuong_doi_tuong_id_created_at_idx",
            "loai_doi_tuong",
            "doi_tuong_id",
            "created_at",
        ),
        Index("LichSuThaoTac_nhan_vien_id_created_at_idx", "nhan_vien_id", "created_at"),
        CheckConstraint(
            "loai_doi_tuong IN ('nhan_vien', 'vai_tro', 'mat_hang', 'nha_cung_cap', 'cong_thuc', 'phieu_nhap', 'phieu_xuat', 'yeu_cau_san_xuat', 'lenh_san_xuat', 'chung_tu_hoan_thanh_san_xuat', 'phieu_dieu_chinh_kho', 'ticket_loi_dieu_chinh')",
            name="ck_lich_su_thao_tac_loai_doi_tuong",
        ),
        CheckConstraint(
            "thao_tac IN ('tao', 'sua', 'xoa_nhap', 'gui', 'bat_dau', 'duyet', 'tu_choi', 've_nhap', 'hoan_tat', 'cap_quyen', 'thu_hoi_quyen', 'vo_hieu_hoa', 'huy', 'ghi_nhan_loi', 'nhan_xu_ly', 'giai_quyet', 'xac_nhan', 'dang_nhap')",
            name="ck_lich_su_thao_tac_thao_tac",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    loai_doi_tuong: Mapped[str] = mapped_column(String, nullable=False)
    doi_tuong_id: Mapped[int] = mapped_column(Integer, nullable=False)
    thao_tac: Mapped[str] = mapped_column(String, nullable=False)
    du_lieu_truoc: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    du_lieu_sau: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    ly_do: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
