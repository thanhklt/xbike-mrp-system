"""SQLAlchemy mappings owned by production orders, matching the bootstrap SQL."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Identity, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LenhSanXuat(Base):
    __tablename__ = "LenhSanXuat"
    __table_args__ = (
        CheckConstraint(
            "trang_thai IN ('nhap', 'da_gui', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')",
            name="ck_lenh_san_xuat_trang_thai",
        ),
        CheckConstraint("so_luong > 0", name="ck_lenh_san_xuat_so_luong"),
        CheckConstraint(
            "lenh_san_xuat_cha_id IS NULL OR lenh_san_xuat_cha_id <> id",
            name="ck_lenh_khong_tu_lam_cha",
        ),
        CheckConstraint(
            "trang_thai IN ('nhap','da_huy') OR nhan_vien_id IS NOT NULL",
            name="ck_lenh_nguoi_thuc_hien",
        ),
        CheckConstraint(
            "ma_lenh_san_xuat ~ '^LSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_lenh_san_xuat, 6) <> '000000'",
            name="ck_lenh_san_xuat_ma",
        ).ddl_if(dialect="postgresql"),
        Index("ix_lenh_cha", "lenh_san_xuat_cha_id"),
        Index("ix_lenh_yeu_cau", "yeu_cau_san_xuat_id"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_lenh_san_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    yeu_cau_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("YeuCauSanXuat.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    lenh_san_xuat_cha_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("LenhSanXuat.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    bom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Bom.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    nhan_vien_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    chi_tiet: Mapped[list["ChiTietLenhSanXuat"]] = relationship(
        foreign_keys="ChiTietLenhSanXuat.lenh_san_xuat_id",
        lazy="selectin",
        order_by="ChiTietLenhSanXuat.id",
        passive_deletes="all",
    )


class ChiTietLenhSanXuat(Base):
    __tablename__ = "ChiTietLenhSanXuat"
    __table_args__ = (
        CheckConstraint("so_luong_can > 0", name="ck_chi_tiet_lenh_san_xuat_so_luong_can"),
        Index(
            "ChiTietLenhSanXuat_lenh_san_xuat_id_mat_hang_id_idx",
            "lenh_san_xuat_id",
            "mat_hang_id",
            unique=True,
        ),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    lenh_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LenhSanXuat.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong_can: Mapped[int] = mapped_column(Integer, nullable=False)
