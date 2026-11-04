"""Adjustment and ticket mappings matching the agreed PostgreSQL bootstrap."""

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PhieuDieuChinhKho(Base):
    __tablename__ = "PhieuDieuChinhKho"
    __table_args__ = (
        CheckConstraint(
            "trang_thai IN ('nhap', 'da_xac_nhan', 'loi')",
            name="ck_phieu_dieu_chinh_kho_trang_thai",
        ),
        CheckConstraint("btrim(ly_do) <> ''", name="ck_dieu_chinh_ly_do"),
        CheckConstraint(
            "(trang_thai = 'da_xac_nhan' AND confirmed_at IS NOT NULL AND confirmed_at >= created_at) OR (trang_thai <> 'da_xac_nhan' AND confirmed_at IS NULL)",
            name="ck_dieu_chinh_xac_nhan",
        ),
        CheckConstraint(
            "ma_phieu ~ '^DCK-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_phieu, 6) <> '000000'",
            name="ck_phieu_dieu_chinh_kho_ma",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phieu_nhap_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PhieuNhap.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    ly_do: Mapped[str] = mapped_column(Text, nullable=False)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChiTietPhieuDieuChinhKho(Base):
    __tablename__ = "ChiTietPhieuDieuChinhKho"
    __table_args__ = (
        Index(
            "ChiTietPhieuDieuChinhKho_phieu_dieu_chinh_kho_id_giao_dich_goc_id_idx",
            "phieu_dieu_chinh_kho_id",
            "giao_dich_goc_id",
            unique=True,
        ),
        Index("ix_dieu_chinh_nguon", "giao_dich_goc_id"),
        CheckConstraint(
            "so_luong_hieu_luc_truoc >= 0 AND so_luong_dung >= 0 AND so_luong_bien_dong <> 0 AND so_luong_bien_dong = so_luong_dung - so_luong_hieu_luc_truoc",
            name="ck_chi_tiet_phieu_dieu_chinh_kho_luong",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_dieu_chinh_kho_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PhieuDieuChinhKho.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    giao_dich_goc_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("GiaoDichKho.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    so_luong_hieu_luc_truoc: Mapped[int] = mapped_column(Integer, nullable=False)
    so_luong_dung: Mapped[int] = mapped_column(Integer, nullable=False)
    so_luong_bien_dong: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketLoiDieuChinh(Base):
    __tablename__ = "TicketLoiDieuChinh"
    __table_args__ = (
        Index("ix_ticket_trang_thai", "trang_thai", "created_at"),
        CheckConstraint(
            "trang_thai IN ('cho_xu_ly', 'dang_xu_ly', 'da_xu_ly')",
            name="ck_ticket_loi_dieu_chinh_trang_thai",
        ),
        CheckConstraint("btrim(mo_ta_loi) <> ''", name="ck_ticket_mo_ta"),
        CheckConstraint(
            "trang_thai = 'cho_xu_ly' OR nguoi_xu_ly_id IS NOT NULL", name="ck_ticket_nguoi_xu_ly"
        ),
        CheckConstraint(
            "(trang_thai = 'da_xu_ly' AND nguoi_xu_ly_id IS NOT NULL AND ket_qua_xu_ly IS NOT NULL AND btrim(ket_qua_xu_ly) <> '' AND closed_at IS NOT NULL AND closed_at >= created_at) OR (trang_thai <> 'da_xu_ly' AND closed_at IS NULL)",
            name="ck_ticket_dong",
        ),
        CheckConstraint(
            "ma_ticket ~ '^TKDC-[0-9]{4}(0[1-9]|1[0-2])-[0-9]{6}$' AND right(ma_ticket, 6) <> '000000'",
            name="ck_ticket_loi_dieu_chinh_ma",
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_ticket: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    phieu_nhap_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PhieuNhap.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    nguoi_tao_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    mo_ta_loi: Mapped[str] = mapped_column(Text, nullable=False)
    trang_thai: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'cho_xu_ly'")
    )
    nguoi_xu_ly_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("NhanVien.id", deferrable=True, initially="IMMEDIATE"), nullable=True
    )
    ket_qua_xu_ly: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chi_tiet: Mapped[list["ChiTietTicketLoiDieuChinh"]] = relationship(
        foreign_keys="ChiTietTicketLoiDieuChinh.ticket_id",
        order_by="ChiTietTicketLoiDieuChinh.id",
        lazy="selectin",
        passive_deletes="all",
    )


class ChiTietTicketLoiDieuChinh(Base):
    __tablename__ = "ChiTietTicketLoiDieuChinh"
    __table_args__ = (
        Index(
            "ChiTietTicketLoiDieuChinh_ticket_id_chi_tiet_phieu_nhap_id_idx",
            "ticket_id",
            "chi_tiet_phieu_nhap_id",
            unique=True,
        ),
        CheckConstraint(
            "so_luong_hieu_luc_truoc >= 0 AND so_luong_de_nghi >= 0 AND so_luong_bien_dong <> 0 AND so_luong_bien_dong = so_luong_de_nghi - so_luong_hieu_luc_truoc",
            name="ck_chi_tiet_ticket_loi_dieu_chinh_luong",
        ),
        CheckConstraint("ton_kho_tai_thoi_diem >= 0", name="ck_ticket_ton_chup"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("TicketLoiDieuChinh.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    chi_tiet_phieu_nhap_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ChiTietPhieuNhap.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong_hieu_luc_truoc: Mapped[int] = mapped_column(Integer, nullable=False)
    so_luong_de_nghi: Mapped[int] = mapped_column(Integer, nullable=False)
    so_luong_bien_dong: Mapped[int] = mapped_column(Integer, nullable=False)
    ton_kho_tai_thoi_diem: Mapped[int] = mapped_column(Integer, nullable=False)
