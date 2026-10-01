from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FinishedGoodsDispatch(Base):
    __tablename__ = "finished_goods_dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dispatch_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    destination_dealer: Mapped[str] = mapped_column(String(255), nullable=False)
    carrier_tracking_number: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PREPARING")
    dispatched_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    dispatched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["DispatchItem"]] = relationship(
        "DispatchItem", back_populates="dispatch", cascade="all, delete-orphan"
    )


class DispatchItem(Base):
    __tablename__ = "finished_goods_dispatch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dispatch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("finished_goods_dispatches.id", ondelete="CASCADE"), nullable=False
    )
    product_part_id: Mapped[int] = mapped_column(Integer, ForeignKey("catalog_parts.id"), nullable=False)
    quantity_dispatched: Mapped[float] = mapped_column(Float, nullable=False)
    serial_numbers: Mapped[str] = mapped_column(Text, nullable=True)

    dispatch: Mapped["FinishedGoodsDispatch"] = relationship("FinishedGoodsDispatch", back_populates="items")
