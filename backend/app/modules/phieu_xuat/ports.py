"""Issue snapshots and persistence required when canceling production."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PhieuXuatSnapshot:
    id: int
    trang_thai: str
    values: dict[str, Any]


class PhieuXuatRepository(Protocol):
    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]: ...

    async def lock_by_sources(
        self, yeu_cau_id: int, lenh_ids: list[int]
    ) -> list[PhieuXuatSnapshot]: ...

    async def delete_draft(self, issue_id: int) -> None: ...

    async def reject(self, issue_id: int) -> PhieuXuatSnapshot: ...
