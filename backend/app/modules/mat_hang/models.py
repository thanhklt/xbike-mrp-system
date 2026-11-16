"""MatHang mapping matching the authoritative bootstrap SQL."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    FetchedValue,
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
        CheckConstraint(
            "so_luong_ton >= 0 AND so_luong_dang_giu >= 0 AND so_luong_dang_giu <= so_luong_ton",
            name="ck_mat_hang_ton",
        ),
        CheckConstraint("loai_mat_hang = 'thanh_pham' OR is_active", name="ck_mat_hang_active"),
        CheckConstraint("btrim(don_vi_tinh) <> ''", name="ck_mat_hang_don_vi_tinh"),
        CheckConstraint(
            "loai_mat_hang IN ('linh_kien', 'thanh_pham')",
            name="ck_mat_hang_loai",
        ),
        CheckConstraint("don_gia >= 0", name="ck_mat_hang_don_gia"),
        CheckConstraint(
            "ma_mat_hang ~ '^MH-[0-9]{6}$' AND right(ma_mat_hang, 6) <> '000000'",
            name="ck_mat_hang_ma",
        ),
        CheckConstraint("ten_mat_hang ~ '[^[:space:]]'", name="ck_mat_hang_ten"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_mat_hang: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, server_default=FetchedValue()
    )
    ten_mat_hang: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    loai_mat_hang: Mapped[str] = mapped_column(String, nullable=False)
    don_vi_tinh: Mapped[str] = mapped_column(String, nullable=False)
    mau_sac: Mapped[str | None] = mapped_column(String, nullable=True)
    mo_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    don_gia: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    so_luong_ton: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    so_luong_dang_giu: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    so_luong_con_dung: Mapped[int] = mapped_column(
        Integer, Computed("so_luong_ton - so_luong_dang_giu", persisted=True), nullable=True
    )
    ton_kho_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
