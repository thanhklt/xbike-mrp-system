"""ORM mapping matching infra/postgres/init.sql."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LuuLuongTruyCap(Base):
    __tablename__ = "LuuLuongTruyCap"
    __table_args__ = (CheckConstraint("so_request >= 0", name="ck_luu_luong_truy_cap_so_request"),)

    gio_bat_dau: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    so_request: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
