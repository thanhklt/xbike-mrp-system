"""Persistence and availability contracts; no session escapes the adapter."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.mat_hang.schemas import MatHangCreate, MatHangRead


@dataclass(frozen=True)
class ItemReferences:
    has_bom: bool
    has_docs: bool
    has_stock: bool

    @property
    def has_any(self) -> bool:
        return self.has_bom or self.has_docs or self.has_stock


class MatHangRepository(Protocol):
    async def load_all(self) -> list[MatHangRead]: ...
    async def get_for_update(self, item_id: int) -> MatHangRead | None: ...
    async def find_duplicate(
        self,
        *,
        ma_mat_hang: str | None = None,
        sku: str | None = None,
        exclude_id: int | None = None,
    ) -> bool: ...
    async def get_references(self, item_id: int) -> ItemReferences: ...
    async def add(self, payload: MatHangCreate) -> MatHangRead: ...
    async def update(self, item_id: int, changes: dict[str, Any]) -> MatHangRead: ...
    async def lock_items(self, item_ids: Iterable[int]) -> list[MatHangRead]: ...


class ActiveMatHangReader(Protocol):
    async def require_active_items(self, item_ids: Iterable[int]) -> None: ...
