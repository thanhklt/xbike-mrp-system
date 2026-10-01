from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.shared.enums import MaterialIssueStatus


class MaterialIssueRequest(Base):
    __tablename__ = "material_issue_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    work_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[MaterialIssueStatus] = mapped_column(
        Enum(MaterialIssueStatus, name="material_issue_status_enum"),
        default=MaterialIssueStatus.REQUESTED,
    )
    requested_by_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_by_user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    items: Mapped[list["MaterialIssueItem"]] = relationship(
        "MaterialIssueItem", back_populates="request", cascade="all, delete-orphan"
    )


class MaterialIssueItem(Base):
    __tablename__ = "material_issue_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    issue_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("material_issue_requests.id", ondelete="CASCADE"), nullable=False
    )
    part_id: Mapped[int] = mapped_column(Integer, ForeignKey("catalog_parts.id"), nullable=False)
    quantity_requested: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_issued: Mapped[float] = mapped_column(Float, default=0.0)
    source_bin_location: Mapped[str] = mapped_column(String(50), nullable=True)

    request: Mapped["MaterialIssueRequest"] = relationship("MaterialIssueRequest", back_populates="items")
