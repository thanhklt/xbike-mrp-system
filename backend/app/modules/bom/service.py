"""BOM snapshots, active-graph validation and atomic audit."""

from app.core.errors import (
    BomCycleException,
    InvalidInputException,
    MissingBomException,
    NotFoundException,
)
from app.core.transactions import Transaction
from app.modules.audit.ports import AuditWriter
from app.modules.audit.schemas import CreationAudit
from app.modules.bom.ports import ActiveBom, BomRepository
from app.modules.bom.schemas import (
    BomCreate,
    BomDetailResponse,
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
from app.modules.mat_hang.ports import ActiveMatHangReader


def _detail(record: BomRead, request_id: str) -> BomDetailResponse:
    return BomDetailResponse(data=record, meta=ResponseMeta(request_id=request_id))


def _check_cycle(output: int, graph: dict[int, ActiveBom]) -> None:
    visited: set[int] = set()
    pending = [component for component, _ in graph[output].components]
    while pending:
        item_id = pending.pop()
        if item_id == output:
            raise BomCycleException()
        if item_id in visited:
            continue
        visited.add(item_id)
        child = graph.get(item_id)
        if child is not None:
            pending.extend(component for component, _ in child.components)


def _tree_node(
    item_id: int, quantity: int, graph: dict[int, ActiveBom], path: frozenset[int]
) -> BomTreeNode:
    if item_id in path:
        raise BomCycleException()
    child = graph.get(item_id)
    return BomTreeNode(
        mat_hang_id=item_id,
        so_luong_tren_mot_don_vi_cha=quantity,
        bom_id=child.bom_id if child else None,
        children=[
            _tree_node(component, amount, graph, path | {item_id})
            for component, amount in child.components
        ]
        if child
        else [],
    )


class BomPlanningReader:
    """Read the current graph, serializing plan submission with BOM mutations."""

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
        transaction: Transaction,
        items: ActiveMatHangReader,
    ):
        self.repository = repository
        self.audit = audit
        self.transaction = transaction
        self.items = items

    async def list_bom(self, params: BomListQuery, request_id: str) -> BomListResponse:
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

    async def _require_bom(self, bom_id: int) -> BomRead:
        if bom_id > 2**31 - 1:
            raise NotFoundException()
        record = await self.repository.get_by_id(bom_id)
        if record is None:
            raise NotFoundException(message=f"BOM {bom_id} không tồn tại")
        return record

    async def get_bom(self, bom_id: int, request_id: str) -> BomDetailResponse:
        return _detail(await self._require_bom(bom_id), request_id)

    async def get_cau_truc(self, bom_id: int, request_id: str) -> BomTreeResponse:
        record = await self._require_bom(bom_id)
        graph = await self.repository.load_active_graph()
        return BomTreeResponse(
            data=BomTreeRead(
                bom_id=record.id,
                mat_hang_id=record.mat_hang_id,
                version=record.version,
                children=[
                    _tree_node(
                        line.mat_hang_id, line.so_luong, graph, frozenset({record.mat_hang_id})
                    )
                    for line in record.chi_tiet
                ],
            ),
            meta=ResponseMeta(request_id=request_id),
        )

    async def _validate_formula(self, output: int, components: list[ChiTietBomInput]) -> None:
        item_ids = [output, *(component.mat_hang_id for component in components)]
        await self.items.require_active_items(item_ids)
        types = await self.repository.get_item_types(item_ids)
        if types[output] not in {"ban_thanh_pham", "thanh_pham"}:
            raise InvalidInputException(
                message=f"mat_hang_id {output}: đầu ra phải là bán thành phẩm hoặc thành phẩm"
            )
        for component in components:
            if types[component.mat_hang_id] not in {
                "nguyen_vat_lieu",
                "linh_kien",
                "ban_thanh_pham",
            }:
                raise InvalidInputException(
                    message=f"mat_hang_id {component.mat_hang_id}: loại thành phần không hợp lệ"
                )
        graph = await self.repository.load_active_graph()
        for component in components:
            if (
                types[component.mat_hang_id] == "ban_thanh_pham"
                and component.mat_hang_id not in graph
                and component.mat_hang_id != output
            ):
                raise MissingBomException(
                    message=f"mat_hang_id {component.mat_hang_id}: chưa có BOM hiện hành"
                )
        # The candidate supplies the output node; legacy self-edges are cycles, not missing BOMs.
        graph[output] = ActiveBom(0, 0, tuple((c.mat_hang_id, c.so_luong) for c in components))
        _check_cycle(output, graph)

    async def _audit(
        self, action: str, after: BomRead, actor: dict, before: BomRead | None = None
    ) -> None:
        await self.audit.append(
            CreationAudit(
                nhan_vien_id=int(actor["sub"]),
                loai_doi_tuong="cong_thuc",
                doi_tuong_id=after.id,
                thao_tac=action,
                du_lieu_sau=after.model_dump(mode="json"),
                du_lieu_truoc=before.model_dump(mode="json") if before else None,
            )
        )

    async def _close_current(self, output: int, actor: dict) -> None:
        old = await self.repository.get_active_for_item(output)
        if old is not None:
            closed = await self.repository.deactivate(old.id)
            await self._audit("vo_hieu_hoa", closed, actor, old)

    async def create_bom(
        self, payload: BomCreate, actor: dict, request_id: str
    ) -> BomDetailResponse:
        async with self.transaction:
            await self.repository.lock_bom_graph()
            await self._validate_formula(payload.mat_hang_id, payload.chi_tiet)
            await self._close_current(payload.mat_hang_id, actor)
            version = await self.repository.next_version(payload.mat_hang_id)
            created = await self.repository.add(payload.mat_hang_id, version, payload.chi_tiet)
            await self._audit("tao", created, actor)
        return _detail(created, request_id)

    async def delete_bom(self, bom_id: int, actor: dict) -> None:
        async with self.transaction:
            await self.repository.lock_bom_graph()
            record = await self._require_bom(bom_id)
            if record.is_active:
                closed = await self.repository.deactivate(bom_id)
                await self._audit("vo_hieu_hoa", closed, actor, record)

    async def activate_bom(self, bom_id: int, actor: dict, request_id: str) -> BomDetailResponse:
        async with self.transaction:
            await self.repository.lock_bom_graph()
            record = await self._require_bom(bom_id)
            if record.is_active:
                return _detail(record, request_id)
            components = [
                ChiTietBomInput(mat_hang_id=line.mat_hang_id, so_luong=line.so_luong)
                for line in record.chi_tiet
            ]
            await self._validate_formula(record.mat_hang_id, components)
            await self._close_current(record.mat_hang_id, actor)
            activated = await self.repository.activate(bom_id)
            await self._audit("sua", activated, actor, record)
        return _detail(activated, request_id)
