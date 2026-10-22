"""ORM mapping matching infra/postgres/init.sql."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Supplier(Base):
    __tablename__ = "nha_cung_cap"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ma_ncc: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ten_ncc: Mapped[str | None] = mapped_column(String, nullable=True)
    so_dien_thoai: Mapped[str | None] = mapped_column(String, nullable=True)
    dia_chi: Mapped[str | None] = mapped_column(String, nullable=True)
    phuong: Mapped[str | None] = mapped_column(String, nullable=True)
    tinh: Mapped[str | None] = mapped_column(String, nullable=True)
