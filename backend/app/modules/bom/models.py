"""ORM mapping matching infra/postgres/init.sql."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BOMHeader(Base):
    __tablename__ = "bom"
    __table_args__ = (
        CheckConstraint("version > 0", name="ck_bom_1"),
        CheckConstraint(
            "end_time IS NULL OR start_time IS NULL OR end_time > start_time", name="ck_bom_2"
        ),
        UniqueConstraint("mat_hang_id", "version", name="uq_bom_source"),
        Index("ix_bom_mat_hang_id", "mat_hang_id"),
        Index(
            "uq_bom_active", "mat_hang_id", unique=True, postgresql_where=text("is_active IS TRUE")
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_bom_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    items: Mapped[list["BOMItem"]] = relationship(
        "BOMItem", foreign_keys="BOMItem.bom_id", lazy="selectin", passive_deletes="all"
    )


class BOMItem(Base):
    __tablename__ = "chi_tiet_bom"
    __table_args__ = (
        CheckConstraint("so_luong > 0", name="ck_chi_tiet_bom_1"),
        UniqueConstraint("bom_id", "mat_hang_id", name="uq_chi_tiet_bom_source"),
        Index("ix_chi_tiet_bom_bom_id", "bom_id"),
        Index("ix_chi_tiet_bom_mat_hang_id", "mat_hang_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    bom_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bom.id", name="fk_chi_tiet_bom_bom_id", ondelete="RESTRICT"),
        nullable=False,
    )
    mat_hang_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mat_hang.id", name="fk_chi_tiet_bom_mat_hang_id", ondelete="RESTRICT"),
        nullable=False,
    )
    so_luong: Mapped[int] = mapped_column(Integer, nullable=False)
