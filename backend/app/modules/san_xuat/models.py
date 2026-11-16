"""Mappings for the agreed PostgreSQL bootstrap; no legacy inventory ownership."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class YeuCauSanXuat(Base):
    __tablename__ = "YeuCauSanXuat"
    __table_args__ = (
        CheckConstraint(
            "trang_thai IN ('nhap', 'da_gui', 'cho_bo_sung_linh_kien', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')",
            name="ck_yeu_cau_san_xuat_trang_thai",
        ),
        CheckConstraint("loai_yeu_cau IN ('dap_ung', 'cho_kho')", name="ck_ycsx_loai"),
        CheckConstraint(
            "loai_yeu_cau = 'dap_ung' OR COALESCE(so_luong_dung_thanh_pham, 0) = 0",
            name="ck_ycsx_cho_kho",
        ),
        CheckConstraint("so_luong > 0", name="ck_ycsx_so_luong"),
        CheckConstraint("phien_ban > 0", name="ck_ycsx_phien_ban"),
        CheckConstraint(
            "trang_thai = 'nhap' OR (bom_id IS NOT NULL AND gui_at IS NOT NULL)",
            name="ck_ycsx_bom_chot",
        ),
        CheckConstraint(
            "(so_luong_dung_thanh_pham IS NULL AND so_luong_can_san_xuat IS NULL AND kiem_tra_lan_dau_at IS NULL) "
            "OR (so_luong_dung_thanh_pham >= 0 AND so_luong_can_san_xuat >= 0 "
            "AND so_luong_dung_thanh_pham + so_luong_can_san_xuat = so_luong "
            "AND kiem_tra_lan_dau_at IS NOT NULL)",
            name="ck_ycsx_so_luong_chot",
        ),
        CheckConstraint(
            "trang_thai NOT IN ('cho_bo_sung_linh_kien', 'dang_thuc_hien', 'hoan_thanh') OR so_luong_can_san_xuat IS NOT NULL",
            name="ck_ycsx_da_kiem_tra",
        ),
        CheckConstraint(
            "started_at IS NULL OR (so_luong_can_san_xuat > 0 AND trang_thai IN ('dang_thuc_hien', 'hoan_thanh'))",
            name="ck_ycsx_bat_dau",
        ),
        CheckConstraint(
            "(trang_thai = 'hoan_thanh') = (completed_at IS NOT NULL)",
            name="ck_ycsx_hoan_thanh",
        ),
        CheckConstraint(
            "(trang_thai = 'da_huy') = (huy_at IS NOT NULL AND nguoi_huy_id IS NOT NULL AND COALESCE(btrim(ly_do_huy), '') <> '')",
            name="ck_ycsx_huy",
        ),
        CheckConstraint(
            "ma_yeu_cau_san_xuat ~ '^YCSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_yeu_cau_san_xuat, 6) <> '000000'",
            name="ck_ycsx_ma",
        ).ddl_if(dialect="postgresql"),
        Index("ix_ycsx_nhan_vien_duoc_giao", "nhan_vien_duoc_giao_id", "trang_thai", "created_at"),
        Index("ix_ycsx_trang_thai", "trang_thai", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_yeu_cau_san_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    loai_yeu_cau: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'dap_ung'"))
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    han_hoan_thanh: Mapped[date] = mapped_column(Date, nullable=False)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    nhan_vien_duoc_giao_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    bom_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("Bom.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    so_luong_dung_thanh_pham: Mapped[int | None] = mapped_column(Integer, nullable=True)
    so_luong_can_san_xuat: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    gui_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    kiem_tra_lan_dau_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    huy_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    nguoi_huy_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    ly_do_huy: Mapped[str | None] = mapped_column(Text, nullable=True)
    phien_ban: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


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


class ChungTuHoanThanhSx(Base):
    __tablename__ = "ChungTuHoanThanhSx"
    __table_args__ = (
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')",
            name="ck_chung_tu_hoan_thanh_sx_trang_thai",
        ),
        CheckConstraint(
            "so_luong_hoan_thanh > 0", name="ck_chung_tu_hoan_thanh_sx_so_luong_hoan_thanh"
        ),
        CheckConstraint(
            "ma_phieu ~ '^HTSX-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu, 6) <> '000000'",
            name="ck_chung_tu_hoan_thanh_sx_ma",
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    lenh_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("LenhSanXuat.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    so_luong_hoan_thanh: Mapped[int] = mapped_column(Integer, nullable=False)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
