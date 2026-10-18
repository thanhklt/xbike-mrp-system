"""Decisions and explanations; no HTTP or database side effects."""

from dataclasses import dataclass

from .facts import BOMLine


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    mat_hang_id: int | None = None


@dataclass(frozen=True)
class RuleResult:
    vi_pham: tuple[Violation, ...] = ()

    @property
    def hop_le(self) -> bool:
        return not self.vi_pham


@dataclass(frozen=True)
class PlannedOrder:
    ma_tam: str
    ma_cha_tam: str | None
    mat_hang_id: int
    bom_id: int
    bom_version: int
    so_luong: int
    nhu_cau_truc_tiep: tuple[BOMLine, ...]


@dataclass(frozen=True)
class MaterialNeed:
    mat_hang_id: int
    ma_mat_hang: str
    ten_mat_hang: str
    don_vi_tinh: str
    so_luong_can_tu_kho: int
    so_luong_hien_co: int
    so_luong_thieu: int


@dataclass(frozen=True)
class PlanResult:
    so_luong_can_san_xuat: int
    lenh_du_kien: tuple[PlannedOrder, ...] = ()
    vat_tu: tuple[MaterialNeed, ...] = ()
    vi_pham: tuple[Violation, ...] = ()

    @property
    def du_dieu_kien_gui(self) -> bool:
        return not self.vi_pham
