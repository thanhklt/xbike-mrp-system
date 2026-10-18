"""BOM validation and deterministic allocation within a single preview."""

from collections import defaultdict, deque

from .facts import BOM, BOMLine, Item, PlanningFacts
from .results import MaterialNeed, PlannedOrder, PlanResult, Violation


def _validate_structure(facts: PlanningFacts) -> tuple[Violation, ...]:
    items = {item.id: item for item in facts.mat_hang}
    boms = {bom.mat_hang_id: bom for bom in facts.bom}
    if (
        len(items) != len(facts.mat_hang)
        or len(boms) != len(facts.bom)
        or len({bom.id for bom in facts.bom}) != len(facts.bom)
    ):
        return (Violation("du_lieu_khong_hop_le", "Trùng mặt hàng hoặc BOM trong dữ kiện."),)
    product = items.get(facts.mat_hang_id)
    if product is None or product.loai_mat_hang != "thanh_pham":
        return (Violation("du_lieu_khong_hop_le", "Yêu cầu phải chọn thành phẩm hợp lệ."),)
    if facts.ton_kho.keys() - items.keys():
        return (Violation("du_lieu_khong_hop_le", "Tồn kho chứa mặt hàng chưa khai báo."),)
    edges: dict[int, set[int]] = {key: set() for key in items}
    indegree = dict.fromkeys(items, 0)
    for bom in facts.bom:
        output = items.get(bom.mat_hang_id)
        if output is None or output.loai_mat_hang not in {"thanh_pham", "ban_thanh_pham"}:
            return (Violation("du_lieu_khong_hop_le", "Đầu ra BOM không hợp lệ.", bom.mat_hang_id),)
        for line in bom.chi_tiet:
            if line.mat_hang_id not in items or line.mat_hang_id in edges[bom.mat_hang_id]:
                return (
                    Violation(
                        "du_lieu_khong_hop_le",
                        "Thành phần BOM trùng hoặc không tồn tại.",
                        line.mat_hang_id,
                    ),
                )
            edges[bom.mat_hang_id].add(line.mat_hang_id)
            indegree[line.mat_hang_id] += 1
    ready = deque(key for key, count in indegree.items() if count == 0)
    visited = 0
    while ready:
        visited += 1
        for child in edges[ready.popleft()]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if visited != len(items):
        return (Violation("bom_co_chu_trinh", "BOM chứa tham chiếu vòng."),)
    return ()


def _material_need(item: Item, quantity: int, stock: int) -> MaterialNeed:
    return MaterialNeed(
        item.id,
        item.ma_mat_hang,
        item.ten_mat_hang,
        item.don_vi_tinh,
        quantity,
        stock,
        max(quantity - stock, 0),
    )


def plan_production(facts: PlanningFacts) -> PlanResult:
    """Select current BOMs before calling; consume only a local copy of stock."""
    quantity = max(facts.so_luong - facts.ton_kho.get(facts.mat_hang_id, 0), 0)
    violations = _validate_structure(facts)
    if violations:
        return PlanResult(quantity, vi_pham=violations)
    items = {item.id: item for item in facts.mat_hang}
    boms = {bom.mat_hang_id: bom for bom in facts.bom}
    remaining = dict(facts.ton_kho)
    warehouse: dict[int, int] = defaultdict(int)
    orders: list[PlannedOrder] = []
    errors: list[Violation] = []
    # Explicit stack handles deep valid BOMs without Python recursion limits.
    pending: list[tuple[int, int, str | None]] = []
    if quantity:
        pending.append((facts.mat_hang_id, quantity, None))
    while pending:
        item_id, needed, parent = pending.pop()
        bom: BOM | None = boms.get(item_id)
        if bom is None:
            errors.append(Violation("thieu_bom", "Thiếu BOM để sản xuất phần còn thiếu.", item_id))
            continue
        reference = f"L{len(orders) + 1}"
        direct = tuple(
            BOMLine(mat_hang_id=line.mat_hang_id, so_luong=line.so_luong * needed)
            for line in sorted(bom.chi_tiet, key=lambda line: line.mat_hang_id)
        )
        orders.append(PlannedOrder(reference, parent, item_id, bom.id, bom.version, needed, direct))
        children: list[tuple[int, int, str | None]] = []
        for line in direct:
            child = items[line.mat_hang_id]
            available = remaining.get(child.id, 0)
            allocated = min(available, line.so_luong)
            remaining[child.id] = available - allocated
            if child.loai_mat_hang in {"thanh_pham", "ban_thanh_pham"}:
                warehouse[child.id] += allocated
                if line.so_luong > allocated:
                    children.append((child.id, line.so_luong - allocated, reference))
            else:
                warehouse[child.id] += line.so_luong
        pending.extend(reversed(children))
    materials = tuple(
        _material_need(items[key], needed, facts.ton_kho.get(key, 0))
        for key, needed in sorted(warehouse.items())
        if needed
    )
    errors.extend(
        Violation(
            "thieu_vat_tu",
            f"Còn thiếu {need.so_luong_thieu} {need.don_vi_tinh} {need.ten_mat_hang}.",
            need.mat_hang_id,
        )
        for need in materials
        if need.so_luong_thieu
    )
    return PlanResult(quantity, tuple(orders), materials, tuple(errors))
