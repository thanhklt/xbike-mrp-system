"""Persistence operations and boundary contract for mat_hang module."""

from collections.abc import Sequence
from typing import Protocol

from app.modules.catalog.models import Part as MatHang
from app.modules.inventory.models import StockLevel


class MatHangRepository(Protocol):
    async def list_items(
        self,
        *,
        q: str | None = None,
        loai_mat_hang: str | None = None,
        is_active: bool | None = None,
        don_vi_tinh: str | None = None,
        mau_sac: str | None = None,
        don_gia_min: int | None = None,
        don_gia_max: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_field: str = "id",
        is_desc: bool = False,
    ) -> tuple[Sequence[MatHang], int]: ...

    async def get_by_id(self, item_id: int) -> MatHang | None: ...

    async def find_duplicate(
        self,
        *,
        ma_mat_hang: str | None = None,
        sku: str | None = None,
        exclude_id: int | None = None,
    ) -> MatHang | None: ...

    async def get_reference_info(self, item_id: int) -> dict: ...

    async def add(self, item: MatHang) -> MatHang: ...

    async def init_stock(self, item_id: int) -> StockLevel: ...

    async def update(self, item: MatHang) -> MatHang: ...

    async def delete(self, item: MatHang) -> None: ...

    async def log_audit(
        self,
        actor_id: int | None,
        thao_tac: str,
        record_id: int,
        before: dict | None,
        after: dict | None,
    ) -> None: ...
