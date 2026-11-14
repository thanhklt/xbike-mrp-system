"""Dependent UC-10/12 integration and UC-16 validation/atomicity, not full catalog refactor."""

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from test_bom_api import client as client
from test_bom_api import headers
from test_bom_postgres import FORMULA, MANAGER, product, scalar, services, tag
from test_bom_postgres import database as database

from app.modules.bom.schemas import BomFormula
from app.modules.mat_hang.schemas import MatHangCreate, MatHangPatch

BASE = {
    "ten_mat_hang": "New Bike",
    "sku": "new-bike",
    "loai_mat_hang": "thanh_pham",
    "don_vi_tinh": "chiec",
    "don_gia": 100,
}


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {"chi_tiet": []},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 0}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": True}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 1}, {"mat_hang_id": 1, "so_luong": 2}]},
    ],
)
async def test_uc16_ac1_to4_bad_formula_never_creates_item(client, database, bad):
    response = await client.post("/api/v1/mat_hang", json={**BASE, "bom": bad}, headers=headers())
    assert response.status_code == 422, response.text
    assert await scalar(database, 'SELECT count(*) FROM "MatHang"') == 2
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0


@pytest.mark.parametrize("component,status", [(999, 404), (3, 422)])
async def test_uc16_ac1_wrong_type_or_missing_item_rolls_back(client, database, component, status):
    await product(database)
    response = await client.post(
        "/api/v1/mat_hang",
        json={**BASE, "bom": {"chi_tiet": [{"mat_hang_id": component, "so_luong": 1}]}},
        headers=headers(),
    )
    assert response.status_code == status, response.text
    assert await scalar(database, 'SELECT count(*) FROM "MatHang"') == 3
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 1


async def test_uc10_uc16_create_response_and_reserved_input(client, database):
    response = await client.post(
        "/api/v1/mat_hang", json={**BASE, "bom": FORMULA}, headers=headers()
    )
    assert response.status_code == 201, response.text
    item = response.json()["data"]
    assert item["ma_mat_hang"] == "MH-000003" and item["is_active"] and item["so_luong_ton"] == 0
    get = await client.get(response.headers["location"], headers=headers())
    assert get.headers["etag"] == response.headers["etag"]
    for field, value in [("ma_mat_hang", "MH-000020"), ("so_luong_ton", 100), ("is_active", False)]:
        bad = await client.post(
            "/api/v1/mat_hang", json={**BASE, "bom": FORMULA, field: value}, headers=headers()
        )
        assert bad.status_code == 422


async def test_uc12_reuses_most_recently_activated_not_highest_version(database):
    item, first = await product(database)
    async with services(database) as (boms, catalog, _session):
        await boms.create_version(
            first, BomFormula(**FORMULA), MANAGER, await tag(database, first), "test"
        )
    async with services(database) as (boms, catalog, _session):
        await boms.activate_bom(first, MANAGER, await tag(database, first), "test")
    async with services(database) as (boms, catalog, _session):
        _, item_tag = await boms.item_detail(item)
        await catalog.delete_mat_hang(item, item_tag, MANAGER)
    async with services(database) as (boms, catalog, _session):
        _, item_tag = await boms.item_detail(item)
        await catalog.patch_mat_hang(item, MatHangPatch(is_active=True), item_tag, MANAGER)
    assert await scalar(database, 'SELECT id FROM "Bom" WHERE is_active') == first
    assert database.cache.snapshot().by_id[item].is_active


@pytest.mark.parametrize("point", ["formula", "audit", "commit"])
async def test_uc16_ac6_atomic_create_failure(database, monkeypatch, point):
    async with services(database) as (boms, catalog, session):
        if point == "formula":
            original = boms.repository.add

            async def fail(*args, **kwargs):
                await original(*args, **kwargs)
                raise RuntimeError("after formula insert")

            monkeypatch.setattr(boms.repository, "add", fail)
        elif point == "audit":

            async def fail(*args):
                raise RuntimeError("audit failed")

            monkeypatch.setattr(boms.audit, "append", fail)
        else:

            async def fail():
                raise RuntimeError("commit failed")

            monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError):
            await catalog.create_mat_hang(MatHangCreate(**BASE, bom=FORMULA), MANAGER)
    assert await scalar(database, 'SELECT count(*) FROM "MatHang"') == 2
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 0
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0


async def test_uc12_component_cannot_be_stopped(client):
    read = await client.get("/api/v1/mat_hang/1", headers=headers())
    response = await client.delete(
        "/api/v1/mat_hang/1", headers={**headers(), "If-Match": read.headers["etag"]}
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value", [("ma_mat_hang", "MH-000023"), ("loai_mat_hang", "linh_kien")]
)
def test_uc12_immutable_catalog_input(field, value):
    with pytest.raises(ValidationError):
        MatHangPatch.model_validate({field: value})


async def test_uc10_code_exhaustion_is_conflict_without_partial_write(client, database):
    async with database.sessions() as session:
        await session.execute(
            text("SELECT setval(pg_get_serial_sequence('\"MatHang\"','id'),999999,true)")
        )
        await session.commit()
    response = await client.post(
        "/api/v1/mat_hang", json={**BASE, "loai_mat_hang": "linh_kien"}, headers=headers()
    )
    assert response.status_code == 409, response.text
    assert await scalar(database, 'SELECT count(*) FROM "MatHang"') == 2
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0


async def test_uc10_component_create_and_duplicate_sku(client, database):
    payload = {**BASE, "loai_mat_hang": "linh_kien"}
    first = await client.post("/api/v1/mat_hang", json=payload, headers=headers())
    assert first.status_code == 201, first.text
    duplicate = await client.post("/api/v1/mat_hang", json=payload, headers=headers())
    assert duplicate.status_code == 409
    assert await scalar(database, 'SELECT count(*) FROM "MatHang"') == 3
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 0
