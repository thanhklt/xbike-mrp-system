"""Order startup, ownership inside san_xuat and request boundaries without a database."""

import importlib.util
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers

from app import models  # noqa: F401
from app.core.database import Base
from app.main import app
from app.modules.san_xuat import router as san_xuat_router_module
from app.modules.san_xuat.models import ChiTietLenhSanXuat, LenhSanXuat
from app.modules.san_xuat.router import lenh_sx_router as router
from app.modules.san_xuat.schemas import (
    KeHoachRead,
    LenhEmptyInput,
    LenhPatch,
    LenhQuery,
    LenhRead,
    LenhResponse,
    LyDoInput,
)


def test_order_models_register_once_and_resolve_their_foreign_keys():
    configure_mappers()
    for model in (LenhSanXuat, ChiTietLenhSanXuat):
        assert model.__module__ == "app.modules.san_xuat.models"
        assert Base.metadata.tables[model.__tablename__] is model.__table__
        registered = [
            mapper
            for mapper in Base.registry.mappers
            if mapper.local_table.name == model.__tablename__
        ]
        assert len(registered) == 1
        for foreign_key in model.__table__.foreign_keys:
            assert foreign_key.column.table is Base.metadata.tables[foreign_key.column.table.name]
    assert LenhSanXuat.chi_tiet.property.mapper.class_ is ChiTietLenhSanXuat


def test_all_order_endpoints_live_in_san_xuat_router():
    operations = router.routes
    assert len(operations) == 7
    assert all(route.endpoint.__module__ == "app.modules.san_xuat.router" for route in operations)
    paths = app.openapi()["paths"]
    assert (
        sum(
            len(methods)
            for path, methods in paths.items()
            if path.startswith("/api/v1/lenh_san_xuat")
        )
        == 7
    )
    for action in ("gui", "bat_dau"):
        schema = paths[f"/api/v1/lenh_san_xuat/{{id}}/{action}"]["post"]["requestBody"]["content"][
            "application/json"
        ]["schema"]
        assert schema["$ref"].endswith("LenhEmptyInput")


def test_san_xuat_router_exposes_three_named_routers():
    expected = {
        "yeu_cau_sx_router": ("/yeu_cau_san_xuat", 9),
        "lenh_sx_router": ("/lenh_san_xuat", 7),
        "chung_tu_router": ("/chung_tu_hoan_thanh_sx", 9),
    }
    for name, (prefix, count) in expected.items():
        named_router = getattr(san_xuat_router_module, name)
        assert named_router.prefix == prefix
        assert len(named_router.routes) == count
    assert not hasattr(san_xuat_router_module, "router")
    assert not hasattr(san_xuat_router_module, "hoan_thanh_router")


def test_lenh_module_is_merged_into_san_xuat():
    assert importlib.util.find_spec("app.modules.lenh_san_xuat") is None
    assert LenhResponse.model_fields["data"].annotation is LenhRead
    assert KeHoachRead.model_fields["lenh"].annotation == list[LenhRead]
    components = app.openapi()["components"]["schemas"]
    assert not [name for name in components if "app__modules__" in name]
    assert components["LenhRead"]["properties"]["trang_thai"]["enum"] == [
        "nhap",
        "da_gui",
        "dang_thuc_hien",
        "hoan_thanh",
        "da_huy",
    ]


@pytest.mark.parametrize("employee", [True, False, "3", 1.5, 0, -1, 2**31])
def test_assignment_requires_a_positive_int32_or_null(employee):
    with pytest.raises(ValidationError):
        LenhPatch.model_validate({"nhan_vien_id": employee})


def test_assignment_null_is_explicit_and_other_order_fields_are_immutable():
    assert LenhPatch(nhan_vien_id=None).model_fields_set == {"nhan_vien_id"}
    for body in ({}, {"bom_id": 1}, {"nhan_vien_id": 3, "so_luong": 2}):
        with pytest.raises(ValidationError):
            LenhPatch.model_validate(body)


@pytest.mark.parametrize(
    "day",
    [
        True,
        1793746800,
        "20261104",
        "2026-W45-3",
        "2026-02-30",
        "2026-11-04T00:00:00Z",
        datetime(2026, 11, 4, tzinfo=timezone.utc),
    ],
)
def test_list_dates_are_exact_calendar_days(day):
    with pytest.raises(ValidationError):
        LenhQuery.model_validate({"tu_ngay": day})


def test_query_accepts_date_objects_and_rejects_reverse_or_unbounded_end():
    assert LenhQuery(tu_ngay=date(2026, 11, 4)).tu_ngay == date(2026, 11, 4)
    for query in (
        {"tu_ngay": "2026-11-05", "den_ngay": "2026-11-04"},
        {"den_ngay": "9999-12-31"},
        {"page_size": 101},
        {"sort": "bom_id"},
        {"warehouse_id": 1},
    ):
        with pytest.raises(ValidationError):
            LenhQuery.model_validate(query)


def test_actions_accept_only_empty_object_or_nonempty_trimmed_reason():
    assert LenhEmptyInput.model_validate({}).model_dump() == {}
    for body in ({"nhan_vien_id": 3}, [], None):
        with pytest.raises(ValidationError):
            LenhEmptyInput.model_validate(body)
    assert LyDoInput(ly_do="  Không còn nhu cầu  ").ly_do == "Không còn nhu cầu"
    for body in ({}, {"ly_do": " "}, {"ly_do": None}, {"ly_do": "Hủy", "trang_thai": "da_huy"}):
        with pytest.raises(ValidationError):
            LyDoInput.model_validate(body)
