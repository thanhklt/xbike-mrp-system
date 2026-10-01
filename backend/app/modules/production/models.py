from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.shared.enums import WorkOrderStatus


class WorkOrder(Base):
    __tablename__ = "production_work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    work_order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    product_part_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("catalog_parts.id"), nullable=False, index=True
    )
    bom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bom_headers.id"), nullable=False, index=True
    )
    quantity_planned: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_completed: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_scrapped: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[WorkOrderStatus] = mapped_column(
        Enum(WorkOrderStatus, name="work_order_status_enum"),
        default=WorkOrderStatus.PLANNED,
    )
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_finish: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
