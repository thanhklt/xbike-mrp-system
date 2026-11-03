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
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PhieuNhap(Base):
    __tablename__ = "PhieuNhap"
    __table_args__ = (
        CheckConstraint("trang_thai IN ('nhap', 'hoan_thanh')", name="ck_phieu_nhap_trang_thai"),
        CheckConstraint("tong_tien >= 0", name="ck_phieu_nhap_tien"),
        CheckConstraint(
            "ma_phieu_nhap ~ '^PN-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu_nhap, 6) <> '000000'",
            name="ck_phieu_nhap_ma",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu_nhap: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    ncc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("NhaCungCap.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    ngay_nhap: Mapped[date] = mapped_column(Date, nullable=False)
    ghi_chu: Mapped[str | None] = mapped_column(Text, nullable=True)
    tong_tien: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    items: Mapped[list["ChiTietPhieuNhap"]] = relationship(
        "ChiTietPhieuNhap",
        foreign_keys="ChiTietPhieuNhap.phieu_nhap_id",
        lazy="selectin",
        passive_deletes="all",
    )


class ChiTietPhieuNhap(Base):
    __tablename__ = "ChiTietPhieuNhap"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_nhap_so_luong"),
        CheckConstraint("don_gia_thuc >= 0 AND tong_gia >= 0", name="ck_chi_tiet_phieu_nhap_tien"),
        Index(
            "ChiTietPhieuNhap_phieu_nhap_id_mat_hang_id_idx",
            "phieu_nhap_id",
            "mat_hang_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_nhap_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PhieuNhap.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    don_gia_thuc: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_gia: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
