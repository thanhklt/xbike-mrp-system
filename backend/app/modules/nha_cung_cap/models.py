"""ORM mapping matching infra/postgres/init.sql."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, FetchedValue, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NhaCungCap(Base):
    __tablename__ = "NhaCungCap"
    __table_args__ = (
        CheckConstraint(
            "ma_ncc ~ '^NCC-[0-9]{6}$' AND right(ma_ncc, 6) <> '000000'", name="ck_nha_cung_cap_ma"
        ),
        CheckConstraint(
            "btrim(ten_ncc) <> '' AND btrim(so_dien_thoai) <> '' AND btrim(dia_chi) <> '' AND btrim(phuong) <> '' AND btrim(tinh) <> ''",
            name="ck_nha_cung_cap_thong_tin",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    ma_ncc: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, server_default=FetchedValue()
    )
    ten_ncc: Mapped[str] = mapped_column(String, nullable=False)
    so_dien_thoai: Mapped[str] = mapped_column(String, nullable=False)
    dia_chi: Mapped[str] = mapped_column(String, nullable=False)
    phuong: Mapped[str] = mapped_column(String, nullable=False)
    tinh: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
