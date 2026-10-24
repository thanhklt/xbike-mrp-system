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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StockLevel(Base):
    __tablename__ = "ton_kho"
    __table_args__ = (
        CheckConstraint("so_luong >= 0", name="ck_ton_kho_1"),
        {"comment": "Balance updated with ledger, document and audit in one backend transaction"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_ton_kho_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)


class StockAdjustment(Base):
    __tablename__ = "phieu_dieu_chinh_kho"
    __table_args__ = (
        Index("ix_phieu_dieu_chinh_kho_nhan_vien_id", "nhan_vien_id"),
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi', 'loi')",
            name="phieu_dieu_chinh_kho_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "nhan_vien.id", name="fk_phieu_dieu_chinh_kho_nhan_vien_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    ly_do: Mapped[str] = mapped_column(Text, nullable=False)
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("now()")
    )

    items: Mapped[list["StockAdjustmentItem"]] = relationship(
        "StockAdjustmentItem",
        foreign_keys="StockAdjustmentItem.phieu_dieu_chinh_kho_id",
        lazy="selectin",
        passive_deletes="all",
    )


class StockAdjustmentItem(Base):
    __tablename__ = "chi_tiet_phieu_dieu_chinh_kho"
    __table_args__ = (
        CheckConstraint("so_luong_bien_dong <> 0", name="ck_chi_tiet_phieu_dieu_chinh_kho_1"),
        Index(
            "ix_chi_tiet_phieu_dieu_chinh_kho_phieu_dieu_chinh_kho_id", "phieu_dieu_chinh_kho_id"
        ),
        Index("ix_chi_tiet_phieu_dieu_chinh_kho_mat_hang_id", "mat_hang_id"),
        Index("ix_chi_tiet_phieu_dieu_chinh_kho_giao_dich_goc_id", "giao_dich_goc_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_dieu_chinh_kho_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "phieu_dieu_chinh_kho.id",
            name="fk_chi_tiet_phieu_dieu_chinh_kho_phieu_dieu_chinh_kho_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "mat_hang.id", name="fk_chi_tiet_phieu_dieu_chinh_kho_mat_hang_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    giao_dich_goc_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "giao_dich_kho.id",
            name="fk_chi_tiet_phieu_dieu_chinh_kho_giao_dich_goc_id",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        nullable=True,
    )
    so_luong_bien_dong: Mapped[int] = mapped_column(Integer, nullable=False)


class AdjustmentErrorTicket(Base):
    __tablename__ = "ticket_loi_dieu_chinh"
    __table_args__ = (
        CheckConstraint(
            "trang_thai = 'cho_xu_ly' OR nguoi_xu_ly_id IS NOT NULL",
            name="ck_ticket_loi_dieu_chinh_1",
        ),
        CheckConstraint(
            "trang_thai <> 'da_xu_ly' OR NULLIF(btrim(ket_qua_xu_ly), '') IS NOT NULL",
            name="ck_ticket_loi_dieu_chinh_2",
        ),
        Index("ix_ticket_loi_dieu_chinh_nguoi_xu_ly_id", "nguoi_xu_ly_id"),
        CheckConstraint(
            "trang_thai IN ('cho_xu_ly', 'dang_xu_ly', 'da_xu_ly')",
            name="ticket_loi_dieu_chinh_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    phieu_dieu_chinh_kho_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "phieu_dieu_chinh_kho.id",
            name="fk_ticket_loi_dieu_chinh_phieu_dieu_chinh_kho_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        unique=True,
    )
    mo_ta_loi: Mapped[str] = mapped_column(Text, nullable=False)
    trang_thai: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'cho_xu_ly'")
    )
    nguoi_xu_ly_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "nhan_vien.id", name="fk_ticket_loi_dieu_chinh_nguoi_xu_ly_id", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    ket_qua_xu_ly: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("now()")
    )


class StockMovement(Base):
    __tablename__ = "giao_dich_kho"
    __table_args__ = (
        CheckConstraint("so_luong_bien_dong <> 0", name="ck_giao_dich_kho_1"),
        CheckConstraint(
            "num_nonnulls(chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id, chung_tu_hoan_thanh_sx_id, chi_tiet_phieu_dieu_chinh_id) = 1",
            name="ck_giao_dich_kho_2",
        ),
        CheckConstraint(
            "(loai_giao_dich = 'nhap_vat_tu' AND chi_tiet_phieu_nhap_id IS NOT NULL AND so_luong_bien_dong > 0) OR (loai_giao_dich IN ('xuat_vat_tu','xuat_thanh_pham') AND chi_tiet_phieu_xuat_id IS NOT NULL AND so_luong_bien_dong < 0) OR (loai_giao_dich = 'nhap_san_pham_san_xuat' AND chung_tu_hoan_thanh_sx_id IS NOT NULL AND so_luong_bien_dong > 0) OR (loai_giao_dich = 'dieu_chinh_ton_kho' AND chi_tiet_phieu_dieu_chinh_id IS NOT NULL)",
            name="ck_giao_dich_kho_3",
        ),
        Index("ix_giao_dich_kho_mat_hang_id", "mat_hang_id"),
        Index("ix_giao_dich_kho_nhan_vien_id", "nhan_vien_id"),
        Index("ix_giao_dich_kho_mat_hang_posted", "mat_hang_id", "posted_at"),
        CheckConstraint(
            "loai_giao_dich IN ('nhap_vat_tu', 'xuat_vat_tu', 'nhap_san_pham_san_xuat', 'xuat_thanh_pham', 'dieu_chinh_ton_kho')",
            name="giao_dich_kho_loai_giao_dich_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_giao_dich_kho_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    loai_giao_dich: Mapped[str] = mapped_column(String, nullable=False)
    so_luong_bien_dong: Mapped[int] = mapped_column(Integer, nullable=False)
    chi_tiet_phieu_nhap_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "chi_tiet_phieu_nhap.id",
            name="fk_giao_dich_kho_chi_tiet_phieu_nhap_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        unique=True,
    )
    chi_tiet_phieu_xuat_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "chi_tiet_phieu_xuat.id",
            name="fk_giao_dich_kho_chi_tiet_phieu_xuat_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        unique=True,
    )
    chung_tu_hoan_thanh_sx_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "chung_tu_hoan_thanh_sx.id",
            name="fk_giao_dich_kho_chung_tu_hoan_thanh_sx_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        unique=True,
    )
    chi_tiet_phieu_dieu_chinh_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "chi_tiet_phieu_dieu_chinh_kho.id",
            name="fk_giao_dich_kho_chi_tiet_phieu_dieu_chinh_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        unique=True,
    )
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_giao_dich_kho_nhan_vien_id", ondelete="RESTRICT"),
        nullable=False,
    )
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=text("now()")
    )
