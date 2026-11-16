"""UC-15–19: specs/use_cases/bom; caller-owned catalog/audit transactions."""

from collections.abc import Iterable

from app.core.errors import (
    ConflictException,
    ForbiddenException,
    InvalidInputException,
    NotFoundException,
)
from app.core.preconditions import make_etag, verify_if_match
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.bom.ports import ActiveBom, BomContext, BomRepository
from app.modules.bom.schemas import (
    BomDetailResponse,
    BomFormula,
    BomListQuery,
    BomListResponse,
    BomRead,
    BomTreeNode,
    BomTreeRead,
    BomTreeResponse,
    ChiTietBomInput,
    ListResponseMeta,
    ResponseMeta,
)
from app.modules.mat_hang.mutation import MatHangMutation
from app.modules.mat_hang.ports import MatHangRepository
from app.modules.mat_hang.schemas import MatHangRead


def require_manager(actor: dict) -> None:
    _require_role(actor, {"quan_ly"})


def _require_role(actor: dict, allowed: set[str]) -> None:
    roles = actor.get("roles")
    if not isinstance(roles, (list, tuple, set, frozenset)) or not allowed.intersection(roles):
        raise ForbiddenException()


def _version(context: BomContext, bom_id: int) -> BomRead:
    record = next((v for v in context.versions if v.id == bom_id), None)
    if record is None:
        raise NotFoundException()
    return record


def _etag(context: BomContext, bom_id: int) -> str:
    return make_etag(
        {"version": _version(context, bom_id).model_dump(mode="json"), "state": context.state()}
    )


def _detail(context: BomContext, bom_id: int, request_id: str) -> tuple[BomDetailResponse, str]:
    return BomDetailResponse(
        data=_version(context, bom_id), meta=ResponseMeta(request_id=request_id)
    ), _etag(context, bom_id)


class BomPlanningReader:
    """Compatibility port for legacy production; does not implement production v4."""

    def __init__(self, repository: BomRepository):
        self.repository = repository

    async def lock_graph(self) -> None:
        await self.repository.lock_bom_graph()

    async def active_graph(self) -> dict[int, ActiveBom]:
        return await self.repository.load_active_graph()


class BomService:
    def __init__(
        self,
        repository: BomRepository,
        audit: AuditWriter,
        mutation: MatHangMutation,
        items: MatHangRepository,
    ):
        self.repository, self.audit, self.mutation, self.items = repository, audit, mutation, items

    async def list_bom(self, params: BomListQuery, actor: dict, request_id: str) -> BomListResponse:
        """UC-15 / AC-1–7: read only, combined filters and stable pagination."""
        _require_role(actor, {"quan_ly", "nhan_vien"})
        result = await self.repository.list_bom(params)
        return BomListResponse(
            data=result.items,
            meta=ListResponseMeta(
                request_id=request_id,
                page=params.page,
                page_size=params.page_size,
                total=result.total,
                total_pages=(result.total + params.page_size - 1) // params.page_size,
            ),
        )

    async def _context(self, bom_id: int) -> BomContext:
        if not 0 < bom_id <= 2**31 - 1:
            raise NotFoundException()
        context = await self.repository.context_for_bom(bom_id)
        if context is None:
            raise NotFoundException()
        return context

    async def get_bom(
        self, bom_id: int, actor: dict, request_id: str
    ) -> tuple[BomDetailResponse, str]:
        """UC-15: snapshot/validator of this version plus current formula state."""
        _require_role(actor, {"quan_ly", "nhan_vien"})
        return _detail(await self._context(bom_id), bom_id, request_id)

    async def get_cau_truc(self, bom_id: int, actor: dict, request_id: str) -> BomTreeResponse:
        """UC-15: historical version has only leaves, never a current child graph."""
        _require_role(actor, {"quan_ly", "nhan_vien"})
        record = _version(await self._context(bom_id), bom_id)
        return BomTreeResponse(
            data=BomTreeRead(
                bom_id=record.id,
                mat_hang_id=record.mat_hang_id,
                version=record.version,
                children=[
                    BomTreeNode(
                        mat_hang_id=line.mat_hang_id,
                        so_luong_tren_mot_don_vi_cha=line.so_luong,
                        bom_id=None,
                        children=[],
                    )
                    for line in record.chi_tiet
                ],
            ),
            meta=ResponseMeta(request_id=request_id),
        )

    async def item_detail(self, item_id: int) -> tuple[MatHangRead, str]:
        """Catalog collaborator: DB snapshot for its representation and validator."""
        if not 0 < item_id <= 2**31 - 1:
            raise NotFoundException()
        context = await self.repository.context(item_id)
        if context is None:
            raise NotFoundException()
        values = context.item.model_dump(mode="json")
        return context.item, make_etag(
            {"item": values, "bom": context.state()}
            if context.item.loai_mat_hang == "thanh_pham"
            else values
        )

    async def lock_catalog(self) -> None:
        self.mutation.require_active()
        await self.repository.lock_bom_graph()

    async def _lock_rows(self, item_id: int, components: Iterable[int]) -> bool:
        """Output item and components in one ascending-id pass, then its versions.

        Stock and production paths lock MatHang rows by ascending id; locking the
        output first and components later could deadlock against them.
        """
        rows = await self.items.lock_items({item_id, *components}, exclusive=True)
        if item_id not in {row.id for row in rows}:
            return False
        await self.repository.lock_versions(item_id)
        return True

    async def lock_item(self, item_id: int, *, reuse: bool) -> tuple[MatHangRead, str] | None:
        """Catalog collaborator (UC-11/12): caller holds lock_catalog(); None if missing.

        reuse=True also locks the components UC-12 would reactivate.
        """
        self.mutation.require_active()
        components = await self.repository.reuse_lines(item_id) if reuse else ()
        if not await self._lock_rows(item_id, components):
            return None
        return await self.item_detail(item_id)

    async def _locked(self, bom_id: int, components: Iterable[int] = ()) -> BomContext:
        """Lock graph, then rows; `components` adds lines a new version will use."""
        await self.lock_catalog()
        ref = await self.repository.bom_ref(bom_id) if 0 < bom_id <= 2**31 - 1 else None
        if ref is None:
            raise NotFoundException()
        item_id, lines = ref
        await self._lock_rows(item_id, {*lines, *components})
        return await self._context(bom_id)

    async def _validate(self, item: MatHangRead, formula: BomFormula) -> None:
        if item.loai_mat_hang != "thanh_pham":
            raise InvalidInputException(message="Công thức chỉ dành cho thành phẩm")
        ids = {line.mat_hang_id for line in formula.chi_tiet}
        records = await self.items.lock_items(sorted(ids))
        if ids != {record.id for record in records}:
            raise NotFoundException(message="Linh kiện không tồn tại")
        if any(record.loai_mat_hang != "linh_kien" for record in records):
            raise InvalidInputException(message="Thành phần chỉ được là linh kiện")

    async def _audit(
        self, action: str, before: BomContext | None, after: BomContext, bom_id: int, actor: dict
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="cong_thuc",
                doi_tuong_id=bom_id,
                thao_tac=action,
                trang_thai_truoc=("dang_dung" if before.active else "da_ngung") if before else None,
                trang_thai_sau="dang_dung" if after.active else "da_ngung",
                du_lieu_truoc={
                    "versions": [v.model_dump(mode="json") for v in before.versions],
                    "mat_hang": before.item.model_dump(mode="json"),
                }
                if before
                else None,
                du_lieu_sau={
                    "versions": [v.model_dump(mode="json") for v in after.versions],
                    "mat_hang": after.item.model_dump(mode="json"),
                },
            )
        )
        if before:
            await self._audit_item(before.item, after.item, actor)

    async def _audit_item(self, before: MatHangRead, after: MatHangRead, actor: dict) -> None:
        if before.is_active == after.is_active:
            return
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="mat_hang",
                doi_tuong_id=after.id,
                thao_tac="dung_lai" if after.is_active else "ngung",
                trang_thai_truoc="dang_dung" if before.is_active else "da_ngung",
                trang_thai_sau="dang_dung" if after.is_active else "da_ngung",
                du_lieu_truoc=before.model_dump(mode="json"),
                du_lieu_sau=after.model_dump(mode="json"),
            )
        )

    async def _set_item_active(self, context: BomContext, active: bool, actor: dict) -> None:
        """Repair a finished item whose flag disagrees with its formula (UC-12 R3)."""
        after = await self.items.update(context.item.id, {"is_active": active})
        await self._audit_item(context.item, after, actor)

    async def create_initial_formula(
        self, item: MatHangRead, formula: BomFormula, actor: dict
    ) -> None:
        """UC-16: caller UC-10 owns transaction/cache; never commits here."""
        require_manager(actor)
        self.mutation.require_active()
        await self._validate(item, formula)
        context = await self.repository.context(item.id)
        if context is None or context.versions:
            raise ConflictException(message="Không tạo công thức riêng cho thành phẩm đã có")
        created = await self.repository.add(item.id, 1, formula.chi_tiet)
        await self._audit("tao", None, await self._context(created.id), created.id, actor)

    async def create_version(
        self, bom_id: int, formula: BomFormula, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[BomDetailResponse, str]:
        """UC-17: immutable version; BOM-AC-04/05/06 transaction and concurrency."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            before = await self._locked(bom_id, (line.mat_hang_id for line in formula.chi_tiet))
            verify_if_match(if_match, _etag(before, bom_id))
            await self._validate(before.item, formula)
            number = max(v.version for v in before.versions) + 1
            if number > 2**31 - 1:
                raise ConflictException(message="Hết dải phiên bản công thức")
            if before.active:
                await self.repository.deactivate(before.active.id)
            created = await self.repository.add(before.item.id, number, formula.chi_tiet)
            item = await self.items.update(before.item.id, {"is_active": True})
            after = await self._context(created.id)
            await self._audit("tao_phien_ban", before, after, created.id, actor)
            changes.append(item)
            result = _detail(after, created.id, request_id)
        return result

    async def _activate(self, before: BomContext, bom_id: int, actor: dict) -> BomContext:
        self.mutation.require_active()
        target = _version(before, bom_id)
        if target.is_active:
            raise ConflictException(message="Version is already active")
        await self._validate(
            before.item,
            BomFormula(
                chi_tiet=[
                    ChiTietBomInput(mat_hang_id=line.mat_hang_id, so_luong=line.so_luong)
                    for line in target.chi_tiet
                ]
            ),
        )
        if before.active:
            await self.repository.deactivate(before.active.id)
        await self.repository.activate(bom_id)
        await self.items.update(before.item.id, {"is_active": True})
        after = await self._context(bom_id)
        await self._audit("dung_lai_phien_ban", before, after, bom_id, actor)
        return after

    async def _stop(self, before: BomContext, bom_id: int, actor: dict) -> BomContext:
        self.mutation.require_active()
        if not _version(before, bom_id).is_active:
            raise ConflictException(message="Version is not active")
        await self.repository.deactivate(bom_id)
        await self.items.update(before.item.id, {"is_active": False})
        after = await self._context(bom_id)
        await self._audit("ngung", before, after, bom_id, actor)
        return after

    async def activate_bom(
        self, bom_id: int, actor: dict, if_match: str | None, request_id: str
    ) -> tuple[BomDetailResponse, str]:
        """UC-18: reuse a historical version under the same locks as its validator."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            before = await self._locked(bom_id)
            verify_if_match(if_match, _etag(before, bom_id))
            after = await self._activate(before, bom_id, actor)
            changes.append(after.item)
            result = _detail(after, bom_id, request_id)
        return result

    async def delete_bom(self, bom_id: int, actor: dict, if_match: str | None) -> None:
        """UC-19: stop, never hard-delete; preserves stock/holds/request snapshots."""
        require_manager(actor)
        async with self.mutation.scope() as changes:
            before = await self._locked(bom_id)
            verify_if_match(if_match, _etag(before, bom_id))
            after = await self._stop(before, bom_id, actor)
            changes.append(after.item)

    async def stop_for_item_in_transaction(self, item_id: int, actor: dict) -> None:
        """UC-12/19: catalog owns transaction; no nested mutation/commit."""
        require_manager(actor)
        self.mutation.require_active()
        context = await self.repository.context(item_id)
        if context is None or not context.versions:
            raise ConflictException(message="Thành phẩm chưa có công thức")
        if context.active:
            await self._stop(context, context.active.id, actor)
        elif context.item.is_active:
            await self._set_item_active(context, False, actor)

    async def reuse_last_for_item_in_transaction(self, item_id: int, actor: dict) -> None:
        """UC-12/18: most recently activated version, not greatest version number."""
        require_manager(actor)
        self.mutation.require_active()
        context = await self.repository.context(item_id)
        if context is None or not context.versions:
            raise ConflictException(message="Thành phẩm chưa có công thức")
        if context.active is None:
            latest = max(context.versions, key=lambda v: (v.kich_hoat_gan_nhat_at, v.id))
            await self._activate(context, latest.id, actor)
        elif not context.item.is_active:
            await self._set_item_active(context, True, actor)
