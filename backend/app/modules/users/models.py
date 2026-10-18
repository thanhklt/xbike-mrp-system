"""ORM mapping matching infra/postgres/init.sql."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "nhan_vien"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    vai_tro_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "vai_tro.id", name="nhan_vien_vai_tro_id_fkey", deferrable=True, initially="IMMEDIATE"
        ),
        nullable=True,
    )
    tai_khoan_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Unresolved in source v2: no tai_khoan table/FK"
    )
    ten_dang_nhap: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    mat_khau: Mapped[str] = mapped_column(
        String, nullable=False, comment="Password hash only, never plaintext"
    )
    ma_nhan_vien: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ho_ten: Mapped[str | None] = mapped_column(String, nullable=True)
    ngay_sinh: Mapped[date | None] = mapped_column(Date, nullable=True)
    so_dien_thoai: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    ngay_vao_lam: Mapped[date | None] = mapped_column(Date, nullable=True)
    he_so_luong: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    trang_thai: Mapped[str | None] = mapped_column(
        String, nullable=True, server_default=text("'hoat_dong'")
    )

    role: Mapped["Role | None"] = relationship(
        "Role", foreign_keys=[vai_tro_id], lazy="selectin", passive_deletes="all"
    )


class Role(Base):
    __tablename__ = "vai_tro"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    ma_vai_tro: Mapped[str | None] = mapped_column(String, nullable=True)
    ten_vai_tro: Mapped[str | None] = mapped_column(String, nullable=True)
