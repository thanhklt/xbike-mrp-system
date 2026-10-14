"""ORM mapping matching infra/postgres/init.sql."""

from sqlalchemy import Boolean, CheckConstraint, Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Part(Base):
    __tablename__ = "mat_hang"
    __table_args__ = (
        CheckConstraint(
            "loai_mat_hang IN ('nguyen_vat_lieu', 'linh_kien', 'ban_thanh_pham', 'thanh_pham')",
            name="mat_hang_loai_mat_hang_check",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_mat_hang: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ten_mat_hang: Mapped[str | None] = mapped_column(String, nullable=True)
    sku: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    loai_mat_hang: Mapped[str] = mapped_column(String, nullable=False)
    don_vi_tinh: Mapped[str] = mapped_column(String, nullable=False)
    mau_sac: Mapped[str | None] = mapped_column(String, nullable=True)
    mo_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    don_gia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
