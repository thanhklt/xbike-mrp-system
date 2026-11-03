"""ORM mapping matching infra/postgres/init.sql."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GoodsReceiptNote(Base):
    __tablename__ = "PhieuNhap"
    __table_args__ = (
        Index("ix_phieu_nhap_nhan_vien_id", "nhan_vien_id"),
        Index("ix_phieu_nhap_ncc_id", "ncc_id"),
        CheckConstraint("trang_thai IN ('nhap', 'hoan_thanh')", name="phieu_nhap_trang_thai_check"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu_nhap: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_phieu_nhap_nhan_vien_id", ondelete="RESTRICT"),
        nullable=False,
    )
    ncc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nha_cung_cap.id", name="fk_phieu_nhap_ncc_id", ondelete="RESTRICT"),
        nullable=False,
    )
    ngay_nhap: Mapped[date] = mapped_column(Date, nullable=False)
    ghi_chu: Mapped[str | None] = mapped_column(String, nullable=True)
    tong_tien: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    items: Mapped[list["ReceiptItem"]] = relationship(
        "ReceiptItem",
        foreign_keys="ReceiptItem.phieu_nhap_id",
        lazy="selectin",
        passive_deletes="all",
    )


class ReceiptItem(Base):
    __tablename__ = "ChiTietPhieuNhap"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_nhap_1"),
        UniqueConstraint("phieu_nhap_id", "mat_hang_id", name="uq_chi_tiet_phieu_nhap_source"),
        Index("ix_chi_tiet_phieu_nhap_phieu_nhap_id", "phieu_nhap_id"),
        Index("ix_chi_tiet_phieu_nhap_mat_hang_id", "mat_hang_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
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
    don_gia_thuc: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_gia: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
