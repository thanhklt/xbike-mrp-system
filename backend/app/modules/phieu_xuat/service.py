"""Issue workflow and production-facing cancellation in one shared transaction."""

import json
import re
from datetime import datetime, timezone
from hashlib import sha256

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InsufficientStock,
    InvalidWorkflowState,
    NotFoundException,
    PostedProductionDependency,
    PreconditionFailedException,
    PreconditionRequiredException,
)
from app.core.transactions import Transaction
from app.modules.audit.schemas import CreationAudit
from app.modules.audit.service import AuditService
from app.modules.inventory.ports import (
    InventoryIssueWriter,
    IssueReservation,
    IssueStockContext,
    StockIssueLine,
)
from app.modules.nhan_vien.schemas import ListResponseMeta, ResponseMeta
from app.modules.phieu_xuat.errors import (
    IssueDemandExceeded,
    IssueDependencyInvalid,
)
from app.modules.phieu_xuat.ports import IssuePart, IssueSource, PhieuXuatRepository
from app.modules.phieu_xuat.schemas import (
    INT_MAX,
    MONEY_MAX,
    PhieuXuatActionRead,
    PhieuXuatActionResponse,
    PhieuXuatCreate,
    PhieuXuatCuaToiListResponse,
    PhieuXuatCuaToiQuery,
    PhieuXuatListResponse,
    PhieuXuatPreviewRead,
    PhieuXuatPreviewResponse,
    PhieuXuatQuery,
    PhieuXuatRead,
    PhieuXuatResponse,
    PhieuXuatSourceResponse,
)


class PhieuXuatService:
    """UC-34..40; specs/use_cases/goods_issue/README.md (GI-AC-01..22)."""

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
        canonical = json.dumps(
            record.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        etag = '"' + sha256(canonical.encode()).hexdigest() + '"'
        return PhieuXuatResponse(data=record, meta=ResponseMeta(request_id=request_id)), etag

    @staticmethod
    def _role(actor: dict, role: str | None = None) -> None:
        allowed = {role} if role else {"quan_ly", "nhan_vien"}
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
        """UC-40: manager-only filtered list in one read-only snapshot."""
        self._role(actor, "quan_ly")
        await self.repository.begin_read_snapshot()
        result = await self.repository.list_issues(query, None)
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

    async def list_my_issues(
        self, query: PhieuXuatCuaToiQuery, actor: dict, request_id: str
    ) -> PhieuXuatCuaToiListResponse:
        """Scoped list for the current employee."""
        self._role(actor, "nhan_vien")
        await self.repository.begin_read_snapshot()
        result = await self.repository.list_my_issues(query, int(actor["sub"]))
        return PhieuXuatCuaToiListResponse(
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
        """UC-40: detail scoped to the request's current assignee or manager."""
        self._role(actor)
        await self.repository.begin_read_snapshot()
        record = (
            await self.repository.get_issue(issue_id, lock=False) if issue_id <= INT_MAX else None
        )
        if record is None:
            raise NotFoundException()
        await self._read_scope(record, actor)
        return self.response(record, request_id)

    async def _lock(self, issue_id: int, actor: dict) -> tuple[PhieuXuatRead, IssueSource]:
        result = await self.repository.lock_context(issue_id) if issue_id <= INT_MAX else None
        if result is None:
            raise NotFoundException()
        return result

    async def source_issues(
        self, source_id: int, actor: dict, request_id: str
    ) -> PhieuXuatSourceResponse:
        self._role(actor)
        if source_id > INT_MAX:
            raise NotFoundException()
        await self.repository.begin_read_snapshot()
        source = await self.repository.lock_source("xuat_linh_kien", source_id, lock=False)
        if "quan_ly" not in actor["roles"]:
            self._assigned(source, actor)
        return PhieuXuatSourceResponse(
            data=await self.repository.phieu_cua_yeu_cau(source_id),
            meta=ResponseMeta(request_id=request_id),
        )

    async def preview(
        self, source_id: int, kind: str, actor: dict, request_id: str
    ) -> PhieuXuatPreviewResponse:
        self._role(actor, "nhan_vien")
        if source_id > INT_MAX:
            raise NotFoundException()
        await self.repository.begin_read_snapshot()
        source = await self.repository.lock_source(kind, source_id, lock=False)
        self._assigned(source, actor)
        await self._validate(kind, source, lock=False)
        if await self.repository.exists_for_source(source_id, kind):
            raise ConflictException(message="Phiếu xuất đã tồn tại. Mở phiếu hiện có từ yêu cầu.")
        return PhieuXuatPreviewResponse(
            data=PhieuXuatPreviewRead(
                yeu_cau_san_xuat_id=source_id,
                loai_phieu=kind,
                chi_tiet=[
                    {"mat_hang_id": item, "so_luong": qty}
                    for item, qty in sorted(source.demand.items())
                ],
            ),
            meta=ResponseMeta(request_id=request_id),
        )

    @staticmethod
    def _require_if_match(if_match: str | None) -> str:
        if not if_match or not if_match.strip():
            raise PreconditionRequiredException()
        if not re.fullmatch(r'"[0-9a-f]{64}"', if_match.strip()):
            raise PreconditionFailedException()
        return if_match.strip()

    def _version(self, record: PhieuXuatRead, if_match: str) -> None:
        if if_match.strip() != self.response(record, "")[1]:
            raise PreconditionFailedException()

    @staticmethod
    def _source_status(kind: str, source: IssueSource) -> None:
        allowed = {"dang_thuc_hien"}
        if kind == "xuat_linh_kien":
            allowed.add("cho_bo_sung_linh_kien")
        if source.trang_thai not in allowed:
            raise InvalidWorkflowState()

    @staticmethod
    def _source_state(kind: str, source: IssueSource) -> None:
        PhieuXuatService._source_status(kind, source)
        if kind == "xuat_linh_kien":
            if not source.production_quantity or not source.demand:
                raise IssueDependencyInvalid()
        elif (
            source.request_kind != "xuat_giao"
            or source.production_quantity is None
            or (source.production_quantity > 0 and source.completion_status != "da_duyet")
        ):
            raise IssueDependencyInvalid()
        if not source.demand or any(
            type(qty) is not int or not 0 < qty <= INT_MAX for qty in source.demand.values()
        ):
            raise IssueDependencyInvalid()

    @staticmethod
    def _assigned(source: IssueSource, actor: dict) -> None:
        if source.assigned_id != int(actor["sub"]):
            raise ForbiddenException()

    async def _validate(
        self, kind: str, source: IssueSource, *, lock: bool = True
    ) -> list[IssuePart]:
        self._source_state(kind, source)
        parts = await self.repository.lock_parts(sorted(source.demand), posting=False, lock=lock)
        expected_kind = "linh_kien" if kind == "xuat_linh_kien" else "thanh_pham"
        if {part.id for part in parts} != set(source.demand) or any(
            part.kind != expected_kind for part in parts
        ):
            raise IssueDependencyInvalid()
        # UC-12 R7: an existing sent request may finish even if its TP was discontinued.
        return parts

    @staticmethod
    def _exact_lines(record: PhieuXuatRead, source: IssueSource) -> None:
        actual = {line.mat_hang_id: line.so_luong for line in record.chi_tiet}
        if len(actual) != len(record.chi_tiet) or actual != source.demand:
            raise IssueDemandExceeded()
        if record.tong_tien is not None or any(
            line.don_gia_thuc is not None or line.tong_gia is not None for line in record.chi_tiet
        ):
            raise IssueDependencyInvalid(message="Unposted issue already has frozen prices")

    @staticmethod
    def _stock_policy(
        record: PhieuXuatRead, source: IssueSource, stocks: list[IssueStockContext]
    ) -> tuple[dict[int, int], list[IssueReservation]]:
        if {stock.item_id for stock in stocks} != set(source.demand):
            raise IssueDependencyInvalid(message="Issue item missing")
        prices = {}
        reservations = []
        for stock in stocks:
            expected_kind = "linh_kien" if record.loai_phieu == "xuat_linh_kien" else "thanh_pham"
            if stock.kind != expected_kind or stock.stock != stock.ledger_balance:
                raise IssueDependencyInvalid(message="Item kind or ledger balance is inconsistent")
            if sum(hold.quantity for hold in stock.reservations) != stock.held:
                raise IssueDependencyInvalid(message="Held balance differs from reservations")
            own = [hold for hold in stock.reservations if hold.request_id == source.request_id]
            expected = (
                {"linh_kien": source.demand[stock.item_id]}
                if record.loai_phieu == "xuat_linh_kien"
                else {
                    key: value
                    for key, value in {
                        "thanh_pham_co_san": source.values["so_luong_dung_thanh_pham"],
                        "thanh_pham_san_xuat": source.production_quantity,
                    }.items()
                    if value
                }
            )
            if len(own) != len(expected) or {hold.kind: hold.quantity for hold in own} != expected:
                raise IssueDependencyInvalid(
                    message="Request reservations do not match the frozen demand"
                )
            if any(
                hold.kind == "thanh_pham_san_xuat" and hold.completion_id != source.completion_id
                for hold in own
            ):
                raise IssueDependencyInvalid(message="Reservation references another completion")
            quantity = source.demand[stock.item_id]
            if stock.stock < quantity or stock.held < quantity:
                raise InsufficientStock(stock.item_id, quantity, stock.stock)
            if type(stock.price) is not int or not 0 <= stock.price <= MONEY_MAX:
                raise IssueDependencyInvalid(message="Invalid catalog price")
            prices[stock.item_id] = stock.price
            reservations.extend(own)
        if sum(prices[line.mat_hang_id] * line.so_luong for line in record.chi_tiet) > MONEY_MAX:
            raise IssueDependencyInvalid(message="Issue money exceeds BIGINT range")
        return prices, reservations

    async def _audit(
        self,
        operation: str,
        before: PhieuXuatRead | None,
        after: PhieuXuatRead | None,
        actor: dict,
        reason: str | None = None,
    ) -> None:
        resource = after if after is not None else before
        if resource is None:
            raise ValueError("Audit requires an issue snapshot")
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="phieu_xuat",
                doi_tuong_id=resource.id,
                thao_tac=operation,
                trang_thai_truoc=before.trang_thai if before else None,
                trang_thai_sau=after.trang_thai if after else None,
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
                du_lieu_sau=after.model_dump(mode="json") if after else None,
                ly_do=reason,
            )
        )

    async def create_issue(
        self, payload: PhieuXuatCreate, actor: dict, request_id: str
    ) -> tuple[PhieuXuatResponse, str]:
        """UC-34/37: create exactly the request's frozen demand, without stock writes."""
        self._role(actor, "nhan_vien")
        async with self.transaction:
            source = await self.repository.lock_source(
                payload.loai_phieu, payload.yeu_cau_san_xuat_id
            )
            self._assigned(source, actor)
            await self._validate(payload.loai_phieu, source)
            if await self.repository.exists_for_source(source.request_id, payload.loai_phieu):
                raise ConflictException(message="Issue already exists for this request and type")
            record = await self.repository.add(payload, int(actor["sub"]), source.demand)
            await self._audit("tao", None, record, actor)
        return self.response(record, request_id)

    async def submit_issue(
        self, issue_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[PhieuXuatResponse, str]:
        """UC-34/37: submit or resubmit the same issue; rejected content is immutable."""
        self._role(actor, "nhan_vien")
        async with self.transaction:
            before, source = await self._lock(issue_id, actor)
            self._assigned(source, actor)
            self._version(before, self._require_if_match(if_match))
            if before.trang_thai not in {"nhap", "tu_choi"}:
                raise InvalidWorkflowState()
            await self._validate(before.loai_phieu, source)
            self._exact_lines(before, source)
            after = await self.repository.change_state(
                issue_id, "cho_duyet", int(actor["sub"]), datetime.now(timezone.utc)
            )
            await self._audit(
                "gui_lai" if before.trang_thai == "tu_choi" else "gui", before, after, actor
            )
        return self.response(after, request_id)

    async def reject_issue(
        self, issue_id: int, actor: dict, if_match: str | None, request_id: str, reason: str
    ) -> tuple[PhieuXuatResponse, str]:
        """UC-36/39: reject without changing stock or reservations."""
        self._role(actor, "quan_ly")
        if not reason.strip():
            raise IssueDependencyInvalid(message="Rejection reason is required")
        async with self.transaction:
            before, source = await self._lock(issue_id, actor)
            self._version(before, self._require_if_match(if_match))
            if before.trang_thai != "cho_duyet":
                raise InvalidWorkflowState()
            # Rejection only needs the source status; data checks must not block the escape path.
            self._source_status(before.loai_phieu, source)
            after = await self.repository.change_state(
                issue_id, "tu_choi", int(actor["sub"]), datetime.now(timezone.utc), reason.strip()
            )
            await self._audit("tu_choi", before, after, actor, reason.strip())
        return self.response(after, request_id)

    async def approve(
        self, issue_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[PhieuXuatActionResponse, str]:
        """UC-35/38: price, stock, holds, ledger, progress and audit commit together."""
        self._role(actor, "quan_ly")
        async with self.transaction:
            before, source = await self._lock(issue_id, actor)
            validator = self._require_if_match(if_match)
            repeated = before.trang_thai == "da_duyet"
            if repeated:
                entries = await self.repository.postings(issue_id)
                expected = {
                    (line.id, line.mat_hang_id, -line.so_luong, before.loai_phieu)
                    for line in before.chi_tiet
                }
                actual = {
                    (
                        row["chi_tiet_phieu_xuat_id"],
                        row["mat_hang_id"],
                        row["so_luong_bien_dong"],
                        row["loai_giao_dich"],
                    )
                    for row in entries
                }
                if not expected or len(entries) != len(expected) or actual != expected:
                    raise IssueDependencyInvalid(message="Approved issue has inconsistent ledger")
                ids = [row["id"] for row in entries]
                after = before
            else:
                self._version(before, validator)
                if before.trang_thai != "cho_duyet":
                    raise InvalidWorkflowState()
                self._source_state(before.loai_phieu, source)
                self._exact_lines(before, source)
                if await self.repository.postings(issue_id):
                    raise IssueDependencyInvalid(message="Unposted issue already has ledger")
                stocks = await self.inventory.lock_issue_stock(
                    source.request_id, sorted(source.demand)
                )
                at = datetime.now(timezone.utc)
                if source.trang_thai == "cho_bo_sung_linh_kien":
                    if {stock.item_id for stock in stocks} != set(source.demand):
                        raise IssueDependencyInvalid(message="Issue item missing")
                    for stock in stocks:
                        if any(hold.request_id == source.request_id for hold in stock.reservations):
                            raise IssueDependencyInvalid(message="Waiting request already holds components")
                        available = stock.stock - stock.held
                        if available < source.demand[stock.item_id]:
                            raise InsufficientStock(stock.item_id, source.demand[stock.item_id], available)
                    await self.inventory.reserve_issue_stock(source.request_id, source.demand, at)
                    stocks = await self.inventory.lock_issue_stock(source.request_id, sorted(source.demand))
                    ready = await self.repository.ready_for_production(source.request_id, at)
                    await self.audit.append(CreationAudit(
                        nhan_vien_id=int(actor["sub"]), loai_doi_tuong="yeu_cau_san_xuat",
                        doi_tuong_id=source.request_id, thao_tac="sua",
                        trang_thai_truoc=source.trang_thai, trang_thai_sau="dang_thuc_hien",
                        du_lieu_truoc=json.loads(json.dumps(source.values, default=str)),
                        du_lieu_sau=json.loads(json.dumps(ready, default=str)),
                    ))
                prices, reservations = self._stock_policy(before, source, stocks)
                after = await self.repository.freeze_prices(before, prices, int(actor["sub"]), at)
                ids = await self.inventory.issue_stock(
                    [
                        StockIssueLine(line.id, line.mat_hang_id, line.so_luong)
                        for line in before.chi_tiet
                    ],
                    before.loai_phieu,
                    int(actor["sub"]),
                    at,
                    issue_id=issue_id,
                    reservations=reservations,
                )
                if before.loai_phieu == "xuat_thanh_pham":
                    progress = await self.repository.update_progress(source.request_id, at)
                    await self.audit.append(
                        CreationAudit(
                            nhan_vien_id=int(actor["sub"]),
                            loai_doi_tuong="yeu_cau_san_xuat",
                            doi_tuong_id=source.request_id,
                            thao_tac="hoan_tat",
                            trang_thai_truoc=source.trang_thai,
                            trang_thai_sau="hoan_thanh",
                            du_lieu_truoc=json.loads(json.dumps(source.values, default=str)),
                            du_lieu_sau=json.loads(json.dumps(progress, default=str)),
                        )
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

    async def phieu_cua_yeu_cau(self, yeu_cau_id: int) -> list[dict]:
        return await self.repository.phieu_cua_yeu_cau(yeu_cau_id)

    # UC-28 Hủy yêu cầu sản xuất — R2 khóa phiếu trước khi kiểm tra (specs/use_cases/production/UC-28.md)
    async def co_phieu_da_ghi_so(self, yeu_cau_id: int) -> bool:
        """UC-35 AC-4 / UC-28 port: caller holds source lock and owns transaction."""
        records = await self.repository.lock_by_sources(yeu_cau_id)
        return any(record.trang_thai == "da_duyet" for record in records)

    # UC-28 Hủy yêu cầu sản xuất — R4 xử lý phiếu và lịch sử trong transaction của yêu cầu (specs/use_cases/production/UC-28.md)
    async def huy_phieu_chua_ghi_so(self, yeu_cau_id: int, ly_do: str, actor_id: int) -> None:
        """UC-28 port: clean unposted issues inside the caller's cancellation transaction."""
        records = await self.repository.lock_by_sources(yeu_cau_id)
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
                after = (
                    await self.repository.reject(record.id, actor_id, datetime.now(timezone.utc))
                ).values
                action = "tu_choi"
            await self.audit.append(
                CreationAudit(
                    nhan_vien_id=actor_id,
                    loai_doi_tuong="phieu_xuat",
                    doi_tuong_id=record.id,
                    thao_tac=action,
                    trang_thai_truoc=record.trang_thai,
                    trang_thai_sau=after.get("trang_thai"),
                    du_lieu_truoc=record.values,
                    du_lieu_sau=after,
                    ly_do=ly_do,
                )
            )
