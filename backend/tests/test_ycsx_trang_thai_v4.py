"""Trạng thái YeuCauSanXuat v4: mã "linh kiện" khớp giữa schema, ORM và init.sql.

specs/entity_model/data_model_v4.md (chốt 13/11/2026): `cho_bo_sung_vat_tu` → `cho_bo_sung_linh_kien`.
Không cần database: chỉ đối chiếu định nghĩa trong code và DDL.
"""

import re
from pathlib import Path
from typing import get_args

from app.modules.san_xuat.models import YeuCauSanXuat
from app.modules.san_xuat.schemas import YeuCauStatus

V4_STATUSES = {"nhap", "da_gui", "cho_bo_sung_linh_kien", "dang_thuc_hien", "hoan_thanh", "da_huy"}
INIT_SQL = Path(__file__).resolve().parents[2] / "infra" / "postgres" / "init.sql"


def _quoted(text: str) -> set[str]:
    return set(re.findall(r"'([^']+)'", text))


def test_schema_literal_uses_v4_statuses():
    assert set(get_args(YeuCauStatus)) == V4_STATUSES


def test_orm_check_constraint_uses_v4_statuses():
    constraint = next(
        item
        for item in YeuCauSanXuat.__table_args__
        if getattr(item, "name", None) == "ck_yeu_cau_san_xuat_trang_thai"
    )
    assert _quoted(str(constraint.sqltext)) == V4_STATUSES


def test_init_sql_check_constraint_matches_code():
    ddl = INIT_SQL.read_text(encoding="utf-8")
    match = re.search(r'CONSTRAINT "ck_ycsx_trang_thai" CHECK \(trang_thai IN \(([^)]*)\)\)', ddl)
    assert match
    assert _quoted(match.group(1)) == V4_STATUSES


def test_old_vat_tu_status_code_is_gone_from_san_xuat_module():
    module = Path(__file__).resolve().parents[1] / "app" / "modules" / "san_xuat"
    offenders = [
        str(path.relative_to(module))
        for path in module.rglob("*.py")
        if "cho_bo_sung_vat_tu" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
