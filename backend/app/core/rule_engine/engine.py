"""MRP policies from SRS FR-07..12 and API contract v2 sections 8..11."""

from .facts import CompletionFacts, IssueFacts, PlanningFacts, StartFacts
from .planning import plan_production
from .results import PlanResult, RuleResult, Violation


class MRPRuleEngine:
    """Pure decisions. The caller owns authentication, locking and posting."""

    def plan(self, facts: PlanningFacts) -> PlanResult:
        return plan_production(facts)

    def check_issue(self, facts: IssueFacts) -> RuleResult:
        errors: list[Violation] = []
        if facts.trang_thai != "cho_duyet" or facts.trang_thai_nguon not in {
            "da_gui",
            "dang_thuc_hien",
        }:
            errors.append(
                Violation(
                    "trang_thai_khong_hop_le", "Phiếu hoặc nguồn không ở trạng thái cho phép xuất."
                )
            )
        seen: set[int] = set()
        for line in facts.chi_tiet:
            key = line.mat_hang_id
            if key in seen:
                errors.append(Violation("du_lieu_khong_hop_le", "Phiếu xuất trùng mặt hàng.", key))
            seen.add(key)
            if line.so_luong > facts.ton_kho.get(key, 0):
                errors.append(Violation("khong_du_ton_kho", "Không đủ tồn kho để xuất.", key))
            if line.so_luong + facts.da_cap.get(key, 0) > facts.nhu_cau.get(key, 0):
                errors.append(
                    Violation(
                        "vuot_nhu_cau", "Xuất vượt nhu cầu hoặc ngoài nhu cầu trực tiếp.", key
                    )
                )
        return RuleResult(tuple(errors))

    def check_start(self, facts: StartFacts) -> RuleResult:
        errors: list[Violation] = []
        if facts.trang_thai != "da_gui":
            errors.append(Violation("trang_thai_khong_hop_le", "Chỉ bắt đầu lệnh đã gửi."))
        errors.extend(
            Violation("chua_du_vat_tu_da_cap", "Vật tư đã cấp chưa đủ để bắt đầu.", key)
            for key, required in sorted(facts.nhu_cau.items())
            if facts.da_cap.get(key, 0) < required
        )
        return RuleResult(tuple(errors))

    def check_completion(self, facts: CompletionFacts) -> RuleResult:
        errors: list[Violation] = []
        if facts.trang_thai != "cho_duyet" or facts.trang_thai_lenh != "dang_thuc_hien":
            errors.append(
                Violation("trang_thai_khong_hop_le", "Phiếu phải chờ duyệt và lệnh đang thực hiện.")
            )
        total = facts.so_luong_da_hoan_thanh + facts.so_luong_hoan_thanh
        if total > facts.so_luong_lenh:
            errors.append(Violation("vuot_so_luong_hoan_thanh", "Tổng đầu ra vượt số lượng lệnh."))
        # Cross multiplication avoids rounding fractional material coverage.
        errors.extend(
            Violation("chua_du_vat_tu_da_cap", "Đầu ra vượt lượng vật tư đã cấp.", key)
            for key, required in sorted(facts.nhu_cau.items())
            if facts.da_cap.get(key, 0) * facts.so_luong_lenh < required * total
        )
        return RuleResult(tuple(errors))
