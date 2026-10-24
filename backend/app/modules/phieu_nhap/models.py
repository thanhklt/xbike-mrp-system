"""ORM mapping matching infra/postgres/init.sql."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GoodsReceiptNote(Base):
    __tablename__ = "phieu_nhap"
    __table_args__ = (
        Index("ix_phieu_nhap_nhan_vien_id", "nhan_vien_id"),
        Index("ix_phieu_nhap_ncc_id", "ncc_id"),
        CheckConstraint("trang_thai IN ('nhap', 'hoan_thanh')", name="phieu_nhap_trang_thai_check"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ma_phieu_nhap: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_phieu_nhap_nhan_vien_id", ondelete="RESTRICT"),
        nullable=True,
    )
    ncc_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("nha_cung_cap.id", name="fk_phieu_nhap_ncc_id", ondelete="RESTRICT"),
        nullable=True,
    )
    tong_tien: Mapped[int | None] = mapped_column(Integer, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        foreign_keys="ReceiptItem.phieu_nhap_id",
        lazy="selectin",
        passive_deletes="all",
    )


class ReceiptItem(Base):
    __tablename__ = "chi_tiet_phieu_nhap"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_nhap_1"),
        UniqueConstraint("phieu_nhap_id", "mat_hang_id", name="uq_chi_tiet_phieu_nhap_source"),
        Index("ix_chi_tiet_phieu_nhap_phieu_nhap_id", "phieu_nhap_id"),
        Index("ix_chi_tiet_phieu_nhap_mat_hang_id", "mat_hang_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    phieu_nhap_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "phieu_nhap.id", name="fk_chi_tiet_phieu_nhap_phieu_nhap_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_chi_tiet_phieu_nhap_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    don_gia_thuc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tong_gia: Mapped[int | None] = mapped_column(Integer, nullable=True)
