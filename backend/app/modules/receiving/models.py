from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import GoodsReceiptStatus


class GoodsReceiptNote(Base):
    __tablename__ = "goods_receipt_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    grn_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    purchase_order_number: Mapped[str] = mapped_column(String(50), nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    status: Mapped[GoodsReceiptStatus] = mapped_column(
        Enum(GoodsReceiptStatus, name="goods_receipt_status_enum"),
        default=GoodsReceiptStatus.PENDING_INSPECTION,
    )
    received_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    items: Mapped[list["ReceiptItem"]] = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")


class ReceiptItem(Base):
    __tablename__ = "goods_receipt_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    receipt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("goods_receipt_notes.id", ondelete="CASCADE"), nullable=False
    )
    part_id: Mapped[int] = mapped_column(Integer, ForeignKey("catalog_parts.id"), nullable=False)
    quantity_shipped: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_accepted: Mapped[float] = mapped_column(Float, default=0.0)
    quantity_rejected: Mapped[float] = mapped_column(Float, default=0.0)
    lot_number: Mapped[str] = mapped_column(String(50), nullable=True)

    receipt: Mapped["GoodsReceiptNote"] = relationship("GoodsReceiptNote", back_populates="items")
