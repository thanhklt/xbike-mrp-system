"""BOM snapshots mapped to the agreed PostgreSQL bootstrap schema."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Bom(Base):
    __tablename__ = "Bom"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_bom_version"),
        CheckConstraint(
            "end_time IS NULL OR (start_time IS NOT NULL AND end_time > start_time)",
            name="ck_bom_thoi_gian",
        ),
        Index("Bom_mat_hang_id_version_idx", "mat_hang_id", "version", unique=True),
        Index("uq_bom_hien_hanh", "mat_hang_id", unique=True, postgresql_where=text("is_active")),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    chi_tiet: Mapped[list["ChiTietBom"]] = relationship(
        lazy="selectin", order_by="ChiTietBom.id", passive_deletes="all"
    )


class ChiTietBom(Base):
    __tablename__ = "ChiTietBom"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_bom_so_luong"),
        Index("ChiTietBom_bom_id_mat_hang_id_idx", "bom_id", "mat_hang_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    bom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("Bom.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("MatHang.id", deferrable=True, initially="IMMEDIATE"), nullable=False
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
