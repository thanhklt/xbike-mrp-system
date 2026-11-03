"""Mappings for the agreed PostgreSQL bootstrap; no legacy inventory ownership."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PhieuXuat(Base):
    __tablename__ = "PhieuXuat"
    __table_args__ = (
        Index("ix_xuat_lenh", "lenh_san_xuat_id"),
        Index("ix_xuat_yeu_cau", "yeu_cau_san_xuat_id"),
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')",
            name="ck_phieu_xuat_trang_thai",
        ),
        CheckConstraint(
            "loai_phieu IN ('xuat_vat_tu', 'xuat_thanh_pham')", name="ck_phieu_xuat_loai_phieu"
        ),
        CheckConstraint("tong_tien >= 0", name="ck_phieu_xuat_tien"),
        CheckConstraint(
            "(loai_phieu = 'xuat_vat_tu' AND lenh_san_xuat_id IS NOT NULL AND yeu_cau_san_xuat_id IS NULL) OR (loai_phieu = 'xuat_thanh_pham' AND yeu_cau_san_xuat_id IS NOT NULL AND lenh_san_xuat_id IS NULL)",
            name="ck_phieu_xuat_nguon",
        ),
        CheckConstraint(
            "ma_phieu_xuat ~ '^PX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu_xuat, 6) <> '000000'",
            name="ck_phieu_xuat_ma",
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    loai_phieu: Mapped[str] = mapped_column(String, nullable=False)
    yeu_cau_san_xuat_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("YeuCauSanXuat.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    lenh_san_xuat_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("LenhSanXuat.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    tong_tien: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ChiTietPhieuXuat(Base):
    __tablename__ = "ChiTietPhieuXuat"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_xuat_so_luong"),
        CheckConstraint("don_gia_thuc >= 0 AND tong_gia >= 0", name="ck_chi_tiet_phieu_xuat_tien"),
        Index(
            "ChiTietPhieuXuat_phieu_xuat_id_mat_hang_id_idx",
            "phieu_xuat_id",
            "mat_hang_id",
            unique=True,
        ),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_xuat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PhieuXuat.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    don_gia_thuc: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    tong_gia: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
