"""Persistence operations required by BOM use cases."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from app.modules.bom.schemas import BomListQuery, BomRead, ChiTietBomInput
from app.modules.mat_hang.schemas import MatHangRead
from app.shared.records import RecordPage


@dataclass(frozen=True)
class ActiveBom:
    bom_id: int
    version: int
    components: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class BomContext:
    item: MatHangRead
    versions: tuple[BomRead, ...]

    @property
    def active(self) -> BomRead | None:
        return next((version for version in self.versions if version.is_active), None)

    def state(self) -> dict:
        return {
            "is_active": self.item.is_active,
            "versions": [
                {
                    "id": v.id,
                    "version": v.version,
                    "is_active": v.is_active,
                    "activated": v.kich_hoat_gan_nhat_at.isoformat(),
                }
                for v in self.versions
            ],
        }


class BomRepository(Protocol):
    async def context(self, item_id: int) -> BomContext | None: ...

    async def context_for_bom(self, bom_id: int) -> BomContext | None: ...

    async def lock_versions(self, item_id: int) -> None: ...
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
