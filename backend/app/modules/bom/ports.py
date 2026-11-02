"""Persistence operations required by BOM use cases."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.modules.bom.schemas import BomListQuery, BomRead, ChiTietBomInput
from app.shared.records import RecordPage


@dataclass(frozen=True)
class ActiveBom:
    bom_id: int
    version: int
    components: tuple[tuple[int, int], ...]


class BomRepository(Protocol):
    async def lock_bom_graph(self) -> None: ...

    async def list_bom(self, params: BomListQuery) -> RecordPage[BomRead]: ...

    async def get_by_id(self, bom_id: int) -> BomRead | None: ...

    async def get_active_for_item(self, mat_hang_id: int) -> BomRead | None: ...

    async def get_item_types(self, item_ids: Iterable[int]) -> dict[int, str]: ...

    async def load_active_graph(self) -> dict[int, ActiveBom]: ...

    async def next_version(self, mat_hang_id: int) -> int: ...

    async def add(
        self, mat_hang_id: int, version: int, chi_tiet: list[ChiTietBomInput]
    ) -> BomRead: ...

    async def deactivate(self, bom_id: int) -> BomRead: ...

    async def activate(self, bom_id: int) -> BomRead: ...
