"""One immutable item snapshot per application instance."""

import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.core.errors import AppException
from app.modules.mat_hang.schemas import MatHangRead


class MatHangCacheUnavailable(AppException):
    code = "danh_muc_chua_san_sang"
    default_message = "Danh mục mặt hàng chưa sẵn sàng; vui lòng thử lại"


@dataclass(frozen=True)
class ItemSnapshot:
    by_id: Mapping[int, MatHangRead]
    items: tuple[MatHangRead, ...]

    @classmethod
    def build(cls, items: Iterable[MatHangRead]) -> "ItemSnapshot":
        ordered = tuple(sorted(items, key=lambda item: item.id))
        return cls(MappingProxyType({item.id: item for item in ordered}), ordered)


class MatHangCache:
    def __init__(self):
        self.lock = asyncio.Lock()
        self._snapshot: ItemSnapshot | None = None
        self._available = False

    def snapshot(self) -> ItemSnapshot:
        if self._snapshot is None or not self._available:
            raise MatHangCacheUnavailable()
        return self._snapshot

    def mark_unavailable(self) -> None:
        self._available = False

    def replace(self, items: Iterable[MatHangRead]) -> None:
        self._snapshot = ItemSnapshot.build(items)
        self._available = True

    def prepare(self, changes: Iterable[MatHangRead]) -> ItemSnapshot:
        records = dict(self.snapshot().by_id)
        records.update({item.id: item for item in changes})
        return ItemSnapshot.build(records.values())

    def publish(self, snapshot: ItemSnapshot) -> None:
        # A local commit cannot repair a disconnected listener or incomplete reload.
        self._snapshot = snapshot


def filter_items(
    snapshot: ItemSnapshot,
    *,
    q: str | None = None,
    loai_mat_hang: str | None = None,
    is_active: bool | None = None,
    don_vi_tinh: str | None = None,
    mau_sac: str | None = None,
    don_gia_min: int | None = None,
    don_gia_max: int | None = None,
    sort: str = "id",
) -> list[MatHangRead]:
    field = sort.removeprefix("-")
    search = q.casefold() if q else None
    matches = []
    for item in snapshot.items:
        if search and not any(
            search in value.casefold() for value in (item.ma_mat_hang, item.ten_mat_hang)
        ):
            continue
        if any(
            value is not None and getattr(item, key) != value
            for key, value in (
                ("loai_mat_hang", loai_mat_hang),
                ("is_active", is_active),
                ("don_vi_tinh", don_vi_tinh),
                ("mau_sac", mau_sac),
            )
        ):
            continue
        if don_gia_min is not None and (item.don_gia is None or item.don_gia < don_gia_min):
            continue
        if don_gia_max is not None and (item.don_gia is None or item.don_gia > don_gia_max):
            continue
        matches.append(item)
    # Input snapshot is ID-ascending; stable sorting preserves ID ties.
    return sorted(
        matches,
        key=lambda item: (getattr(item, field) is None, getattr(item, field)),
        reverse=sort.startswith("-"),
    )
