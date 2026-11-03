"""Issue snapshots and persistence required when canceling production."""

from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.phieu_xuat.schemas import (
    ChiTietPhieuXuatCreate,
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
    request_status: str
    demand: dict[int, int]


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
    async def list_issues(
        self, params: PhieuXuatQuery, employee_id: int | None
    ) -> RecordPage[PhieuXuatRead]: ...
    async def get_issue(self, issue_id: int) -> PhieuXuatRead | None: ...
    async def assigned_to(self, record: PhieuXuatRead, employee_id: int) -> bool: ...
    async def lock_source(
        self, kind: str, order_id: int | None, request_id: int | None
    ) -> IssueSource: ...
    async def lock_context(self, issue_id: int) -> tuple[PhieuXuatRead, IssueSource] | None: ...
    async def lock_parts(self, item_ids: list[int], *, posting: bool) -> list[IssuePart]: ...
    async def add(self, payload: PhieuXuatCreate, actor_id: int) -> PhieuXuatRead: ...
    async def replace_lines(
        self, issue_id: int, lines: list[ChiTietPhieuXuatCreate]
    ) -> PhieuXuatRead: ...
    async def change_state(self, issue_id: int, state: str) -> PhieuXuatRead: ...
    async def approved_quantities(self, record: PhieuXuatRead) -> dict[int, int]: ...
    async def postings(self, issue_id: int) -> list[int]: ...
    async def freeze_prices(
        self, record: PhieuXuatRead, prices: dict[int, int]
    ) -> PhieuXuatRead: ...
    async def update_progress(self, request_id: int, total: int, required: int) -> None: ...
    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]: ...

    async def lock_by_sources(
        self, yeu_cau_id: int, lenh_ids: list[int]
    ) -> list[PhieuXuatSnapshot]: ...

    async def delete_draft(self, issue_id: int) -> None: ...

    async def reject(self, issue_id: int) -> PhieuXuatSnapshot: ...
