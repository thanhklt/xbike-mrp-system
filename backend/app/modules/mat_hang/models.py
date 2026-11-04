"""MatHang mapping matching the authoritative bootstrap SQL."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Identity,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MatHang(Base):
    __tablename__ = "MatHang"
    __table_args__ = (
        CheckConstraint("so_luong_ton >= 0", name="ck_mat_hang_so_luong_ton"),
        CheckConstraint(
            "loai_mat_hang IN ('nguyen_vat_lieu', 'linh_kien', 'ban_thanh_pham', 'thanh_pham')",
            name="ck_mat_hang_loai_mat_hang",
        ),
        CheckConstraint("don_gia >= 0", name="ck_mat_hang_don_gia"),
        CheckConstraint(
            "ma_mat_hang ~ '^MH-[0-9]{6}$' AND right(ma_mat_hang, 6) <> '000000'",
            name="ck_mat_hang_ma",
        ),
        CheckConstraint("ten_mat_hang ~ '[^[:space:]]'", name="ck_mat_hang_ten"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_mat_hang: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ten_mat_hang: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    loai_mat_hang: Mapped[str] = mapped_column(String, nullable=False)
    don_vi_tinh: Mapped[str] = mapped_column(String, nullable=False)
    mau_sac: Mapped[str | None] = mapped_column(String, nullable=True)
    mo_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    don_gia: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    so_luong_ton: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    ton_kho_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
