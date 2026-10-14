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


class ProductionRequest(Base):
    __tablename__ = "yeu_cau_san_xuat"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_yeu_cau_san_xuat_1"),
        Index("ix_yeu_cau_san_xuat_mat_hang_id", "mat_hang_id"),
        Index("ix_yeu_cau_san_xuat_nhan_vien_id", "nhan_vien_id"),
        Index("ix_yeu_cau_san_xuat_nhan_vien_duoc_giao_id", "nhan_vien_duoc_giao_id"),
        CheckConstraint(
            "trang_thai IN ('nhap', 'da_gui', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')",
            name="yeu_cau_san_xuat_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_yeu_cau_san_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_yeu_cau_san_xuat_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    nhan_vien_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_yeu_cau_san_xuat_nhan_vien_id", ondelete="RESTRICT"),
        nullable=False,
    )
    nhan_vien_duoc_giao_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "nhan_vien.id", name="fk_yeu_cau_san_xuat_nhan_vien_duoc_giao_id", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    orders: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder",
        foreign_keys="WorkOrder.yeu_cau_san_xuat_id",
        lazy="selectin",
        passive_deletes="all",
    )


class WorkOrder(Base):
    __tablename__ = "lenh_san_xuat"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_lenh_san_xuat_1"),
        CheckConstraint(
            "lenh_san_xuat_cha_id IS NULL OR lenh_san_xuat_cha_id <> id", name="ck_lenh_san_xuat_2"
        ),
        Index("ix_lenh_san_xuat_yeu_cau_san_xuat_id", "yeu_cau_san_xuat_id"),
        Index("ix_lenh_san_xuat_lenh_san_xuat_cha_id", "lenh_san_xuat_cha_id"),
        Index("ix_lenh_san_xuat_mat_hang_id", "mat_hang_id"),
        Index("ix_lenh_san_xuat_bom_id", "bom_id"),
        Index("ix_lenh_san_xuat_nhan_vien_id", "nhan_vien_id"),
        CheckConstraint(
            "trang_thai IN ('nhap', 'da_gui', 'dang_thuc_hien', 'hoan_thanh', 'da_huy')",
            name="lenh_san_xuat_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_lenh_san_xuat: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    yeu_cau_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "yeu_cau_san_xuat.id", name="fk_lenh_san_xuat_yeu_cau_san_xuat_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    lenh_san_xuat_cha_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "lenh_san_xuat.id", name="fk_lenh_san_xuat_lenh_san_xuat_cha_id", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_lenh_san_xuat_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    bom_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom.id", name="fk_lenh_san_xuat_bom_id", ondelete="RESTRICT"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
    nhan_vien_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("nhan_vien.id", name="fk_lenh_san_xuat_nhan_vien_id", ondelete="RESTRICT"),
        nullable=True,
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    items: Mapped[list["WorkOrderItem"]] = relationship(
        "WorkOrderItem",
        foreign_keys="WorkOrderItem.lenh_san_xuat_id",
        lazy="selectin",
        passive_deletes="all",
    )


class WorkOrderItem(Base):
    __tablename__ = "chi_tiet_lenh_san_xuat"
    __table_args__ = (
        CheckConstraint("so_luong_can > 0", name="ck_chi_tiet_lenh_san_xuat_1"),
        UniqueConstraint(
            "lenh_san_xuat_id", "mat_hang_id", name="uq_chi_tiet_lenh_san_xuat_source"
        ),
        Index("ix_chi_tiet_lenh_san_xuat_lenh_san_xuat_id", "lenh_san_xuat_id"),
        Index("ix_chi_tiet_lenh_san_xuat_mat_hang_id", "mat_hang_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    lenh_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "lenh_san_xuat.id",
            name="fk_chi_tiet_lenh_san_xuat_lenh_san_xuat_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "mat_hang.id", name="fk_chi_tiet_lenh_san_xuat_mat_hang_id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    so_luong_can: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductionCompletion(Base):
    __tablename__ = "chung_tu_hoan_thanh_sx"
    __table_args__ = (
        CheckConstraint("so_luong_hoan_thanh > 0", name="ck_chung_tu_hoan_thanh_sx_1"),
        Index("ix_chung_tu_hoan_thanh_sx_lenh_san_xuat_id", "lenh_san_xuat_id"),
        Index("ix_chung_tu_hoan_thanh_sx_nhan_vien_id", "nhan_vien_id"),
        CheckConstraint(
            "trang_thai IN ('nhap', 'cho_duyet', 'da_duyet', 'tu_choi')",
            name="chung_tu_hoan_thanh_sx_trang_thai_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_phieu: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    lenh_san_xuat_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "lenh_san_xuat.id",
            name="fk_chung_tu_hoan_thanh_sx_lenh_san_xuat_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    so_luong_hoan_thanh: Mapped[int] = mapped_column(Integer, nullable=False)
    nhan_vien_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "nhan_vien.id", name="fk_chung_tu_hoan_thanh_sx_nhan_vien_id", ondelete="RESTRICT"
        ),
        nullable=True,
    )
    trang_thai: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'nhap'"))
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
