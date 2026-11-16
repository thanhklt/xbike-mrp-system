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
        Index("ix_lstt_doi_tuong", "loai_doi_tuong", "doi_tuong_id"),
        Index("ix_lstt_nhan_vien", "nhan_vien_id", "created_at"),
        Index("ix_lstt_thao_tac", "thao_tac", "created_at"),
        CheckConstraint(
            "loai_doi_tuong IN ('nhan_vien', 'mat_hang', 'nha_cung_cap', 'cong_thuc', 'phieu_nhap', 'phieu_xuat', 'yeu_cau_san_xuat', 'chung_tu_hoan_thanh_san_xuat')",
            name="ck_lstt_loai_doi_tuong",
        ),
        CheckConstraint(
            "thao_tac IN ('dang_nhap', 'tao', 'sua', 'xoa_nhap', 'gui', 'gui_lai', 'kiem_tra', 'duyet', 'tu_choi', 'hoan_tat', 'bat_dau', 'huy', 'khoa', 'mo_khoa', 'doi_vai_tro', 'doi_mat_khau', 'ngung', 'dung_lai', 'tao_phien_ban', 'dung_lai_phien_ban')",
            name="ck_lstt_thao_tac",
        ),
        CheckConstraint(
            "thao_tac NOT IN ('tu_choi', 'huy') OR COALESCE(btrim(ly_do), '') <> ''",
            name="ck_lstt_ly_do",
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
    trang_thai_truoc: Mapped[str | None] = mapped_column(String, nullable=True)
    trang_thai_sau: Mapped[str | None] = mapped_column(String, nullable=True)
    du_lieu_truoc: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    du_lieu_sau: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    ly_do: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
