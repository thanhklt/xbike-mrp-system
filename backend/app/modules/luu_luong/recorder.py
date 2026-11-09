"""Count one request in its own short transaction; never fails the caller."""

import time
from collections.abc import Callable

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.logging import logger
from app.modules.luu_luong.models import LuuLuongTruyCap

WARNING_INTERVAL_SECONDS = 60.0


class LuuLuongRecorder:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        monotonic: Callable[[], float] = time.monotonic,
    ):
        self.session_factory = session_factory
        self.monotonic = monotonic
        self._last_warning: float | None = None

    async def record(self) -> None:
        statement = insert(LuuLuongTruyCap).values(
            gio_bat_dau=func.date_trunc("hour", func.now()), so_request=1
        )
        statement = statement.on_conflict_do_update(
            index_elements=[LuuLuongTruyCap.gio_bat_dau],
            set_={"so_request": LuuLuongTruyCap.so_request + 1},
        )
        try:
            async with self.session_factory() as session:
                await session.execute(statement)
                await session.commit()
        except Exception:
            self._warn()

    def _warn(self) -> None:
        now = self.monotonic()
        if self._last_warning is None or now - self._last_warning >= WARNING_INTERVAL_SECONDS:
            self._last_warning = now
            logger.warning("Không ghi được lưu lượng truy cập", exc_info=True)
