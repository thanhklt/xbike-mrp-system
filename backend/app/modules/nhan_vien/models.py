"""Employee and role mappings for the PostgreSQL demo bootstrap."""

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Identity, Integer, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NhanVien(Base):
    __tablename__ = "NhanVien"
    __table_args__ = (
        CheckConstraint("trang_thai IN ('hoat_dong', 'bi_khoa')", name="ck_nhan_vien_trang_thai"),
        CheckConstraint("he_so_luong >= 0", name="ck_nhan_vien_he_so_luong"),
        CheckConstraint(
            "ma_nhan_vien ~ '^NV-[0-9]{6}$' AND right(ma_nhan_vien, 6) <> '000000'",
            name="ck_nhan_vien_ma",
        ).ddl_if(dialect="postgresql"),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    vai_tro_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("VaiTro.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
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
    trang_thai: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'hoat_dong'")
    )

    role: Mapped["VaiTro | None"] = relationship(
        "VaiTro", foreign_keys=[vai_tro_id], lazy="selectin", passive_deletes="all"
    )


class VaiTro(Base):
    __tablename__ = "VaiTro"
    __table_args__ = (
        CheckConstraint(
            "ma_vai_tro IN ('nhan_vien', 'quan_ly', 'quan_tri_vien')",
            name="ck_vai_tro_ma_vai_tro",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, Identity(always=False), primary_key=True)
    ma_vai_tro: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ten_vai_tro: Mapped[str] = mapped_column(String, nullable=False)
