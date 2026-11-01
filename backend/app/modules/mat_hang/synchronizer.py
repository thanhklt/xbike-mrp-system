"""PostgreSQL notifications and reconciliation for application-owned snapshots."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress

import asyncpg
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository
from app.modules.mat_hang.schemas import MatHangRead

CHANNEL = "mat_hang_changed"
logger = logging.getLogger(__name__)


class MatHangSynchronizer:
    def __init__(
        self,
        cache: MatHangCache,
        load_items: Callable[[], Awaitable[list[MatHangRead]]],
        connect: Callable[[], Awaitable[asyncpg.Connection]],
        *,
        reconcile_seconds: float = 30,
        retry_seconds: float = 1,
    ):
        self.cache = cache
        self.load_items = load_items
        self.connect = connect
        self.reconcile_seconds = reconcile_seconds
        self.retry_seconds = retry_seconds
        self._connection: asyncpg.Connection | None = None
        self._task: asyncio.Task | None = None
        self._changed = asyncio.Event()
        self._stopping = False

    def _on_change(self, connection, pid, channel, payload) -> None:
        self._changed.set()

    def _on_disconnect(self, connection) -> None:
        if not self._stopping:
            self.cache.mark_unavailable()
            self._changed.set()

    async def _listen(self) -> None:
        connection = await self.connect()
        self._connection = connection
        connection.add_termination_listener(self._on_disconnect)
        await connection.add_listener(CHANNEL, self._on_change)

    async def refresh(self) -> None:
        async with self.cache.lock:
            items = await self.load_items()
            if self._connection is None or self._connection.is_closed():
                raise ConnectionError("Listener is disconnected")
            self.cache.replace(items)

    async def start(self) -> None:
        try:
            # LISTEN is committed before the initial snapshot is read. Notifications
            # arriving while it loads stay pending for the worker.
            await self._listen()
            await self.refresh()
            self._task = asyncio.create_task(self._run(), name="mat-hang-synchronizer")
        except BaseException:
            self.cache.mark_unavailable()
            await self._close_connection()
            raise

    async def _close_connection(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None and not connection.is_closed():
            try:
                await connection.close(timeout=5)
            except (OSError, TimeoutError, asyncpg.PostgresError):
                connection.terminate()

    async def _run(self) -> None:
        backoff = self.retry_seconds
        while True:
            try:
                if self._connection is None or self._connection.is_closed():
                    await self._listen()
                else:
                    with suppress(TimeoutError):
                        await asyncio.wait_for(self._changed.wait(), self.reconcile_seconds)
                self._changed.clear()
                await self.refresh()
                backoff = self.retry_seconds
            except asyncio.CancelledError:
                raise
            except Exception:
                self.cache.mark_unavailable()
                logger.warning("Item snapshot synchronization failed; reconnecting")
                await self._close_connection()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)

    async def stop(self) -> None:
        self._stopping = True
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        await self._close_connection()
        self.cache.mark_unavailable()


def create_synchronizer(
    cache: MatHangCache,
    database_url: str,
    sessions: async_sessionmaker[AsyncSession],
) -> MatHangSynchronizer:
    async def load_items() -> list[MatHangRead]:
        async with sessions() as session:
            return await SqlAlchemyMatHangRepository(session).load_all()

    async def connect() -> asyncpg.Connection:
        url = make_url(database_url).set(drivername="postgresql")
        return await asyncpg.connect(url.render_as_string(hide_password=False), timeout=10)

    return MatHangSynchronizer(cache, load_items, connect)
