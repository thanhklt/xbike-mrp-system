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
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IssueNote(Base):
    __tablename__ = "phieu_xuat"
    __table_args__ = (
        CheckConstraint(
            "(loai_phieu = 'xuat_vat_tu' AND lenh_san_xuat_id IS NOT NULL AND yeu_cau_san_xuat_id IS NULL) OR (loai_phieu = 'xuat_thanh_pham' AND yeu_cau_san_xuat_id IS NOT NULL AND lenh_san_xuat_id IS NULL)",
            name="ck_phieu_xuat_1",
        ),
        Index("ix_phieu_xuat_nhan_vien_id", "nhan_vien_id"),
        Index("ix_phieu_xuat_yeu_cau_san_xuat_id", "yeu_cau_san_xuat_id"),
        Index("ix_phieu_xuat_lenh_san_xuat_id", "lenh_san_xuat_id"),
        CheckConstraint(
            "loai_phieu IN ('xuat_vat_tu', 'xuat_thanh_pham')", name="phieu_xuat_loai_phieu_check"
        ),
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')",
            name="phieu_xuat_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_phieu_xuat_nhan_vien_id", ondelete="RESTRICT"),
        nullable=True,
    )
    loai_phieu: Mapped[str] = mapped_column(String, nullable=False)
    yeu_cau_san_xuat_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "yeu_cau_san_xuat.id", name="fk_phieu_xuat_yeu_cau_san_xuat_id", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    lenh_san_xuat_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("lenh_san_xuat.id", name="fk_phieu_xuat_lenh_san_xuat_id", ondelete="RESTRICT"),
        nullable=True,
    )
    tong_tien: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    items: Mapped[list["IssueItem"]] = relationship(
        "IssueItem", foreign_keys="IssueItem.phieu_xuat_id", lazy="selectin", passive_deletes="all"
    )


class IssueItem(Base):
    __tablename__ = "chi_tiet_phieu_xuat"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_xuat_1"),
        UniqueConstraint("phieu_xuat_id", "mat_hang_id", name="uq_chi_tiet_phieu_xuat_source"),
        Index("ix_chi_tiet_phieu_xuat_phieu_xuat_id", "phieu_xuat_id"),
        Index("ix_chi_tiet_phieu_xuat_mat_hang_id", "mat_hang_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "phieu_xuat.id", name="fk_chi_tiet_phieu_xuat_phieu_xuat_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_chi_tiet_phieu_xuat_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    don_gia_thuc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tong_gia: Mapped[int | None] = mapped_column(Integer, nullable=True)


# Both issue flows share phieu_xuat; filter queries on loai_phieu.
MaterialIssueRequest = IssueNote
MaterialIssueItem = IssueItem
