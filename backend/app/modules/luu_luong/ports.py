"""Read contract for aggregated traffic counters."""

from datetime import date, datetime
from typing import Protocol


class LuuLuongReader(Protocol):
    async def sum_by_hour(self, tu: datetime, den: datetime) -> dict[datetime, int]: ...

    async def sum_by_day(self, tu: datetime, den: datetime, timezone: str) -> dict[date, int]: ...
