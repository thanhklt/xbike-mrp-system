from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.enums import ItemType, PartCategory, UnitOfMeasure


class Part(Base):
    __tablename__ = "catalog_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    part_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    item_type: Mapped[ItemType] = mapped_column(
        Enum(ItemType, name="item_type_enum"), default=ItemType.RAW_MATERIAL
    )
    category: Mapped[PartCategory] = mapped_column(
        Enum(PartCategory, name="part_category_enum"), default=PartCategory.HARDWARE
    )
    unit: Mapped[UnitOfMeasure] = mapped_column(
        Enum(UnitOfMeasure, name="unit_of_measure_enum"), default=UnitOfMeasure.PCS
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7)
    safety_stock: Mapped[float] = mapped_column(Float, default=10.0)
    standard_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
