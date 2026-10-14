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


class AuditTrailLog(Base):
    __tablename__ = "lich_su_thao_tac"
    __table_args__ = (
        Index("ix_lich_su_thao_tac_nhan_vien_id", "nhan_vien_id"),
        Index("ix_audit_doi_tuong", "loai_doi_tuong", "doi_tuong_id", "created_at"),
        Index("ix_audit_nhan_vien_created", "nhan_vien_id", "created_at"),
        CheckConstraint(
            "loai_doi_tuong IN ('nhan_vien', 'vai_tro', 'mat_hang', 'nha_cung_cap', 'cong_thuc', 'phieu_nhap', 'phieu_xuat', 'yeu_cau_san_xuat', 'lenh_san_xuat', 'chung_tu_hoan_thanh_san_xuat', 'phieu_dieu_chinh_kho', 'phieu_loi_dieu_chinh')",
            name="lich_su_thao_tac_loai_doi_tuong_check",
        ),
        CheckConstraint(
            "thao_tac IN ('tao', 'sua', 'xoa_nhap', 'gui', 'bat_dau', 'duyet', 'tu_choi', 've_nhap', 'hoan_tat', 'cap_quyen', 'thu_hoi_quyen', 'vo_hieu_hoa', 'huy', 'ghi_nhan_loi', 'nhan_xu_ly', 'mo_lai', 'giai_quyet')",
            name="lich_su_thao_tac_thao_tac_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_lich_su_thao_tac_nhan_vien_id", ondelete="RESTRICT"),
        nullable=False,
    )
    loai_doi_tuong: Mapped[str] = mapped_column(String, nullable=False)
    doi_tuong_id: Mapped[int] = mapped_column(Integer, nullable=False)
    thao_tac: Mapped[str] = mapped_column(String, nullable=False)
    du_lieu_truoc: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    du_lieu_sau: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ly_do: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("now()")
    )
