"""Issue snapshots and persistence required when canceling production."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.modules.phieu_xuat.schemas import (
    PhieuXuatCreate,
    PhieuXuatQuery,
    PhieuXuatRead,
)
from app.shared.records import RecordPage


@dataclass(frozen=True)
class IssueSource:
    trang_thai: str
    assigned_id: int | None
    request_id: int
    demand: dict[int, int]
    request_kind: str
    production_quantity: int | None
    completion_id: int | None
    completion_status: str | None
    values: dict[str, Any]


@dataclass(frozen=True)
class IssuePart:
    id: int
    kind: str
    active: bool
    price: int
    stock: int


@dataclass(frozen=True)
class PhieuXuatSnapshot:
    id: int
    trang_thai: str
    values: dict[str, Any]


class PhieuXuatRepository(Protocol):
    async def begin_read_snapshot(self) -> None: ...
    async def list_issues(
        self, params: PhieuXuatQuery, employee_id: int | None
    ) -> RecordPage[PhieuXuatRead]: ...
    async def get_issue(self, issue_id: int, *, lock: bool = True) -> PhieuXuatRead | None: ...
    async def assigned_to(self, record: PhieuXuatRead, employee_id: int) -> bool: ...
    async def lock_source(self, kind: str, request_id: int) -> IssueSource: ...
    async def lock_context(self, issue_id: int) -> tuple[PhieuXuatRead, IssueSource] | None: ...
    async def lock_parts(self, item_ids: list[int], *, posting: bool) -> list[IssuePart]: ...
    async def exists_for_source(self, request_id: int, kind: str) -> bool: ...
    async def add(
        self, payload: PhieuXuatCreate, actor_id: int, demand: dict[int, int]
    ) -> PhieuXuatRead: ...
    async def change_state(
        self, issue_id: int, state: str, actor_id: int, at: datetime, reason: str | None = None
    ) -> PhieuXuatRead: ...
    async def postings(self, issue_id: int) -> list[dict[str, Any]]: ...
    async def freeze_prices(
        self, record: PhieuXuatRead, prices: dict[int, int], actor_id: int, at: datetime
    ) -> PhieuXuatRead: ...
    async def update_progress(self, request_id: int, at: datetime) -> dict[str, Any]: ...
    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]: ...

    async def lock_by_sources(
        self, yeu_cau_id: int, lenh_ids: list[int]
    ) -> list[PhieuXuatSnapshot]: ...

    async def delete_draft(self, issue_id: int) -> None: ...

    async def reject(self, issue_id: int, actor_id: int, at: datetime) -> PhieuXuatSnapshot: ...
