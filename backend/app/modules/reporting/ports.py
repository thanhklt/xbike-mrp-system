"""Counters needed to construct the current dashboard."""

from datetime import datetime
from typing import Protocol


class ReportingRepository(Protocol):
    async def count_active_work_orders(self) -> int: ...

    async def count_catalog_parts(self) -> int: ...

    async def count_dispatches(self, start: datetime, end: datetime) -> int: ...
