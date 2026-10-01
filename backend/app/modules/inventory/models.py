from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.enums import StockMovementType


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)


class StockLevel(Base):
    __tablename__ = "stock_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_parts.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("warehouses.id"), nullable=False, index=True
    )
    bin_location: Mapped[str] = mapped_column(String(50), default="A-01-01")
    quantity_on_hand: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_allocated: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_reserved: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_parts.id"), nullable=False, index=True
    )
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(StockMovementType, name="stock_movement_type_enum"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    reference_order_number: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
