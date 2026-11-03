"""Issue workflow and production-facing cancellation in one shared transaction."""

import re
from collections.abc import Sequence
from datetime import datetime, timezone
from hashlib import sha256

from app.core.errors import (
    ForbiddenException,
    InvalidWorkflowState,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
    ReferencedResource,
)
from app.core.transactions import Transaction
from app.modules.audit.schemas import CreationAudit
from app.modules.audit.service import AuditService
from app.modules.inventory.ports import InventoryIssueWriter, StockIssueLine
from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta
from app.modules.phieu_xuat.errors import (
    IssueDemandExceeded,
    IssueDependencyInvalid,
    IssueInactiveItem,
)
from app.modules.phieu_xuat.ports import IssuePart, IssueSource, PhieuXuatRepository
from app.modules.phieu_xuat.schemas import (
    INT_MAX,
    MONEY_MAX,
    ChiTietPhieuXuatCreate,
    PhieuXuatActionRead,
    PhieuXuatActionResponse,
    PhieuXuatCreate,
    PhieuXuatListResponse,
    PhieuXuatPatch,
    PhieuXuatQuery,
    PhieuXuatRead,
    PhieuXuatResponse,
)


class PhieuXuatService:
    def __init__(
        self,
        repository: PhieuXuatRepository,
        audit: AuditService,
        transaction: Transaction,
        inventory: InventoryIssueWriter,
    ) -> None:
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.inventory = inventory

    @staticmethod
    def response(record: PhieuXuatRead, request_id: str) -> tuple[PhieuXuatResponse, str]:
        etag = '"' + sha256(record.model_dump_json().encode()).hexdigest() + '"'
        return PhieuXuatResponse(data=record, meta=ResponseMeta(request_id=request_id)), etag

    @staticmethod
    def _role(actor: dict, *, write: bool = False) -> None:
        allowed = {"quan_ly"} if write else {"quan_ly", "nhan_vien"}
        if not allowed.intersection(actor.get("roles", [])):
            raise ForbiddenException()

    async def _read_scope(self, record: PhieuXuatRead, actor: dict) -> None:
        self._role(actor)
        if "quan_ly" not in actor["roles"] and not await self.repository.assigned_to(
            record, int(actor["sub"])
        ):
            raise ForbiddenException()

    async def list_issues(
        self, query: PhieuXuatQuery, actor: dict, request_id: str
    ) -> PhieuXuatListResponse:
        self._role(actor)
        result = await self.repository.list_issues(
            query, None if "quan_ly" in actor["roles"] else int(actor["sub"])
        )
        return PhieuXuatListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=query.page,
                page_size=query.page_size,
                total=result.total,
                total_pages=(result.total + query.page_size - 1) // query.page_size,
            ),
        )

    async def get_issue(
        self, issue_id: int, actor: dict, request_id: str
    ) -> tuple[PhieuXuatResponse, str]:
        self._role(actor)
        record = await self.repository.get_issue(issue_id) if issue_id <= INT_MAX else None
        if record is None:
            raise NotFoundException()
        await self._read_scope(record, actor)
        return self.response(record, request_id)

    async def _context(
        self, issue_id: int, actor: dict, if_match: str | None
    ) -> tuple[PhieuXuatRead, IssueSource]:
        self._role(actor, write=True)
        result = await self.repository.lock_context(issue_id) if issue_id <= INT_MAX else None
        if result is None:
            raise NotFoundException()
        if not if_match or not if_match.strip():
            raise PreconditionRequiredException()
        if not re.fullmatch(r'"[^"\r\n]+"', if_match.strip()):
            raise PreconditionFailedException()
        return result

    def _version(self, record: PhieuXuatRead, if_match: str) -> None:
        if if_match.strip() != self.response(record, "")[1]:
            raise PreconditionFailedException()

    @staticmethod
    def _source_state(source: IssueSource) -> None:
        if (
            source.trang_thai not in {"da_gui", "dang_thuc_hien"}
            or source.request_status == "da_huy"
        ):
            raise InvalidWorkflowState()

    async def _validate(
        self,
        kind: str,
        lines: Sequence[ChiTietPhieuXuatCreate],
        source: IssueSource,
        *,
        posting: bool = False,
    ) -> list[IssuePart]:
        self._source_state(source)
        parts = await self.repository.lock_parts(
            [line.mat_hang_id for line in lines], posting=posting
        )
        if len(parts) != len(lines):
            raise NotFoundException(message="Item not found")
        allowed = (
            {"thanh_pham"}
            if kind == "xuat_thanh_pham"
            else {"nguyen_vat_lieu", "linh_kien", "ban_thanh_pham"}
        )
        for part in parts:
            if not part.active:
                raise IssueInactiveItem()
            if part.kind not in allowed or part.id not in source.demand:
                raise IssueDependencyInvalid()
        if any(line.so_luong > source.demand[line.mat_hang_id] for line in lines):
            raise IssueDemandExceeded()
        return parts

    async def _audit(
        self,
        operation: str,
        before: PhieuXuatRead | None,
        after: PhieuXuatRead | None,
        actor: dict,
        reason: str | None = None,
    ) -> None:
        resource = after if after is not None else before
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="phieu_xuat",
                doi_tuong_id=resource.id,
                thao_tac=operation,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else None,
                ly_do=reason,
            )
        )

    async def create_issue(
        self, payload: PhieuXuatCreate, actor: dict, request_id: str
    ) -> tuple[PhieuXuatResponse, str]:
        self._role(actor, write=True)
        async with self.transaction:
            source = await self.repository.lock_source(
                payload.loai_phieu, payload.lenh_san_xuat_id, payload.yeu_cau_san_xuat_id
            )
            await self._validate(payload.loai_phieu, payload.chi_tiet, source)
            record = await self.repository.add(payload, int(actor["sub"]))
            await self._audit("tao", None, record, actor)
        return self.response(record, request_id)

    async def patch_issue(
        self,
        issue_id: int,
        payload: PhieuXuatPatch,
        actor: dict,
        if_match: str | None,
        request_id: str,
    ) -> tuple[PhieuXuatResponse, str]:
        async with self.transaction:
            before, source = await self._context(issue_id, actor, if_match)
            self._version(before, if_match)
            if before.trang_thai != "nhap":
                raise InvalidWorkflowState()
            if await self.repository.postings(issue_id):
                raise ReferencedResource()
            after = before
            if payload.chi_tiet is not None:
                await self._validate(before.loai_phieu, payload.chi_tiet, source)
                old = [
                    {"mat_hang_id": line.mat_hang_id, "so_luong": line.so_luong}
                    for line in before.chi_tiet
                ]
                if old != [line.model_dump() for line in payload.chi_tiet]:
                    after = await self.repository.replace_lines(issue_id, payload.chi_tiet)
                    await self._audit("sua", before, after, actor)
        return self.response(after, request_id)

    async def delete_issue(self, issue_id: int, actor: dict, if_match: str | None) -> None:
        async with self.transaction:
            before, _ = await self._context(issue_id, actor, if_match)
            self._version(before, if_match)
            if before.trang_thai != "nhap":
                raise InvalidWorkflowState()
            if await self.repository.postings(issue_id):
                raise ReferencedResource()
            await self.repository.delete_draft(issue_id)
            await self._audit("xoa_nhap", before, None, actor)

    async def transition(
        self,
        issue_id: int,
        operation: str,
        actor: dict,
        if_match: str | None,
        request_id: str,
        reason: str | None = None,
    ) -> tuple[PhieuXuatResponse, str]:
        states = {
            "gui": ("nhap", "cho_duyet"),
            "tu_choi": ("cho_duyet", "tu_choi"),
            "ve_nhap": ("tu_choi", "nhap"),
        }
        async with self.transaction:
            before, source = await self._context(issue_id, actor, if_match)
            self._version(before, if_match)
            old, new = states[operation]
            if before.trang_thai != old:
                raise InvalidWorkflowState()
            if operation == "gui":
                await self._validate(before.loai_phieu, before.chi_tiet, source)
            after = await self.repository.change_state(issue_id, new)
            await self._audit(operation, before, after, actor, reason)
        return self.response(after, request_id)

    async def approve(
        self, issue_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[PhieuXuatActionResponse, str]:
        async with self.transaction:
            before, source = await self._context(issue_id, actor, if_match)
            repeated = before.trang_thai == "da_duyet"
            if repeated:
                ids = await self.repository.postings(issue_id)
                if len(ids) != len(before.chi_tiet):
                    raise IssueDependencyInvalid(message="Approved issue has incomplete ledger")
                after = before
            else:
                self._version(before, if_match)
                if before.trang_thai != "cho_duyet":
                    raise InvalidWorkflowState()
                parts = await self._validate(
                    before.loai_phieu, before.chi_tiet, source, posting=True
                )
                approved = await self.repository.approved_quantities(before)
                for line in before.chi_tiet:
                    if (
                        approved.get(line.mat_hang_id, 0) + line.so_luong
                        > source.demand[line.mat_hang_id]
                    ):
                        raise IssueDemandExceeded()
                prices = {part.id: part.price for part in parts}
                if (
                    any(
                        not isinstance(price, int) or isinstance(price, bool) or price < 0
                        for price in prices.values()
                    )
                    or sum(prices[line.mat_hang_id] * line.so_luong for line in before.chi_tiet)
                    > MONEY_MAX
                ):
                    raise IssueDependencyInvalid(message="Invalid or overflowing catalog price")
                after = await self.repository.freeze_prices(before, prices)
                ids = await self.inventory.issue_stock(
                    [
                        StockIssueLine(line.id, line.mat_hang_id, line.so_luong)
                        for line in before.chi_tiet
                    ],
                    before.loai_phieu,
                    int(actor["sub"]),
                    datetime.now(timezone.utc),
                )
                if before.loai_phieu == "xuat_thanh_pham":
                    total = sum(approved.values()) + sum(line.so_luong for line in before.chi_tiet)
                    await self.repository.update_progress(
                        source.request_id, total, sum(source.demand.values())
                    )
                await self._audit("duyet", before, after, actor)
        result = PhieuXuatActionResponse(
            data=PhieuXuatActionRead(
                **after.model_dump(), giao_dich_kho_ids=ids, da_ghi_so_truoc_do=repeated
            ),
            meta=ResponseMeta(request_id=request_id),
        )
        return result, self.response(after, request_id)[1]

    async def tong_da_xuat_thanh_pham(self, yeu_cau_ids: list[int]) -> dict[int, int]:
        return await self.repository.tong_da_xuat_thanh_pham(yeu_cau_ids)

    async def co_phieu_da_ghi_so(self, yeu_cau_id: int, lenh_ids: list[int]) -> bool:
        records = await self.repository.lock_by_sources(yeu_cau_id, lenh_ids)
        return any(record.trang_thai == "da_duyet" for record in records)

    async def huy_phieu_chua_ghi_so(
        self, yeu_cau_id: int, lenh_ids: list[int], ly_do: str, actor_id: int
    ) -> None:
        records = await self.repository.lock_by_sources(yeu_cau_id, lenh_ids)
        if any(record.trang_thai == "da_duyet" for record in records):
            raise PostedProductionDependency()
        for record in records:
            if record.trang_thai not in {"nhap", "cho_duyet"}:
                continue
            if record.trang_thai == "nhap":
                await self.repository.delete_draft(record.id)
                after = {}
                action = "xoa_nhap"
            else:
                after = (await self.repository.reject(record.id)).values
                action = "tu_choi"
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=actor_id,
                    loai_doi_tuong="phieu_xuat",
                    doi_tuong_id=record.id,
                    thao_tac=action,
                    du_lieu_truoc=record.values,
                    du_lieu_sau=after,
                    ly_do=ly_do,
                )
            )
