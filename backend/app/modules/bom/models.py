from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BOMHeader(Base):
    __tablename__ = "bom_headers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_parts.id"), nullable=False, index=True
    )
    bom_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items: Mapped[list["BOMItem"]] = relationship("BOMItem", back_populates="header", cascade="all, delete-orphan")


class BOMItem(Base):
    __tablename__ = "bom_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    bom_header_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bom_headers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_parts.id"), nullable=False, index=True
    )
    quantity_required: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    scrap_factor_percent: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(String(255), nullable=True)

    header: Mapped["BOMHeader"] = relationship("BOMHeader", back_populates="items")
