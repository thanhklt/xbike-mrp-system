"""Publish the catalog snapshot only after the caller's single database commit."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from app.core.errors import ConflictException
from app.core.transactions import Transaction
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.schemas import MatHangRead

_ACTIVE_MUTATION: ContextVar["MatHangMutation | None"] = ContextVar("catalog_mutation", default=None)


class MatHangMutation:
    def __init__(self, transaction: Transaction, cache: MatHangCache):
        self.transaction = transaction
        self.cache = cache

    def require_active(self) -> None:
        if _ACTIVE_MUTATION.get() is not self:
            raise RuntimeError("Caller must own the catalog mutation transaction")

    @asynccontextmanager
    async def scope(self) -> AsyncIterator[list[MatHangRead]]:
        if _ACTIVE_MUTATION.get() is not None:
            raise RuntimeError("Nested catalog mutation would commit the caller's transaction")
        async with self.cache.lock:
            self.cache.snapshot()
            prepared = None
            token = _ACTIVE_MUTATION.set(self)
            try:
                try:
                    async with self.transaction:
                        changes: list[MatHangRead] = []
                        yield changes
                        if changes:
                            prepared = self.cache.prepare(changes)
                except ConflictException:
                    raise
                except BaseException:
                    if prepared is not None:
                        self.cache.mark_unavailable()
                    raise
                if prepared is not None:
                    self.cache.publish(prepared)
            finally:
                _ACTIVE_MUTATION.reset(token)
