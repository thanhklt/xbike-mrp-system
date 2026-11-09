"""Read hourly counters; [tu, den) are UTC instants."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.luu_luong.models import LuuLuongTruyCap


class SqlAlchemyLuuLuongRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def sum_by_hour(self, tu: datetime, den: datetime) -> dict[datetime, int]:
        rows = await self.session.execute(
            select(LuuLuongTruyCap.gio_bat_dau, LuuLuongTruyCap.so_request).where(
                LuuLuongTruyCap.gio_bat_dau >= tu, LuuLuongTruyCap.gio_bat_dau < den
            )
        )
        return {gio: int(so) for gio, so in rows.all()}

    async def sum_by_day(self, tu: datetime, den: datetime, timezone: str) -> dict[date, int]:
        ngay = func.date(func.timezone(timezone, LuuLuongTruyCap.gio_bat_dau))
        rows = await self.session.execute(
            select(ngay, func.sum(LuuLuongTruyCap.so_request))
            .where(LuuLuongTruyCap.gio_bat_dau >= tu, LuuLuongTruyCap.gio_bat_dau < den)
            .group_by(ngay)
        )
        return {day: int(total) for day, total in rows.all()}
