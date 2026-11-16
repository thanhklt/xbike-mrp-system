"""Mappings for the agreed PostgreSQL bootstrap; no legacy inventory ownership."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PhieuXuat(Base):
    __tablename__ = "PhieuXuat"
    __table_args__ = (
        Index("ix_px_trang_thai_loai", "trang_thai", "loai_phieu", "created_at"),
        Index("uq_phieu_xuat_yeu_cau_loai", "yeu_cau_san_xuat_id", "loai_phieu", unique=True),
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')",
            name="ck_px_trang_thai",
        ),
        CheckConstraint(
            "loai_phieu IN ('xuat_linh_kien', 'xuat_thanh_pham')", name="ck_px_loai_phieu"
        ),
        CheckConstraint("tong_tien >= 0", name="ck_px_tien"),
        CheckConstraint("phien_ban > 0", name="ck_px_phien_ban"),
        CheckConstraint("trang_thai = 'nhap' OR gui_at IS NOT NULL", name="ck_px_gui"),
        CheckConstraint(
            "trang_thai NOT IN ('da_duyet', 'tu_choi') OR (nguoi_xu_ly_id IS NOT NULL AND xu_ly_at IS NOT NULL)",
            name="ck_px_xu_ly",
        ),
        CheckConstraint(
            "trang_thai <> 'tu_choi' OR COALESCE(btrim(ly_do_tu_choi), '') <> ''",
            name="ck_px_ly_do",
        ),
        CheckConstraint(
            "trang_thai <> 'da_duyet' OR tong_tien IS NOT NULL", name="ck_px_tien_duyet"
        ),
        CheckConstraint(
            "ma_phieu_xuat ~ '^PX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu_xuat, 6) <> '000000'",
            name="ck_px_ma",
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    loai_phieu: Mapped[str] = mapped_column(String, nullable=False)
    yeu_cau_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("YeuCauSanXuat.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    tong_tien: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    gui_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    nguoi_xu_ly_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE")
    )
    xu_ly_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ly_do_tu_choi: Mapped[str | None] = mapped_column(Text)
    phien_ban: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ChiTietPhieuXuat(Base):
    __tablename__ = "ChiTietPhieuXuat"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_phieu_xuat_so_luong"),
        CheckConstraint(
            "(don_gia_thuc IS NULL AND tong_gia IS NULL) OR (don_gia_thuc >= 0 AND tong_gia = so_luong::bigint * don_gia_thuc)",
            name="ck_chi_tiet_phieu_xuat_tien",
        ),
        Index(
            "uq_chi_tiet_phieu_xuat",
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
    don_gia_thuc: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tong_gia: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
