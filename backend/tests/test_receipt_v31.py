"""Receipt v3.1 contracts and PostgreSQL-only inventory assertions."""

from decimal import Decimal

import pytest
from sqlalchemy import func, inspect, select, text

from app.core.database import Base
from app.main import app
from app.modules.catalog.models import Part
from app.modules.inventory.models import StockMovement
from tests.test_auth_api import auth_context as auth_context
from tests.test_phieu_nhap_api import BASE, BODY
from tests.test_phieu_nhap_api import receipt_context as receipt_context


def test_openapi_money_is_exact_string_or_integer_input_and_string_output():
    schemas = app.openapi()["components"]["schemas"]
    price = schemas["ChiTietPhieuNhapCreate"]["properties"]["don_gia_thuc"]
    assert {choice["type"] for choice in price["anyOf"]} == {"string", "integer"}
    money = schemas["ChiTietPhieuNhapRead"]["properties"]["don_gia_thuc"]
    assert {choice["type"] for choice in money["anyOf"]} == {"string", "null"}


@pytest.mark.parametrize("field", ["ncc_id", "ngay_nhap"])
async def test_required_receipt_fields_cannot_be_missing(receipt_context, field):
    client, _, headers = receipt_context
    body = {**BODY, "ngay_nhap": "2026-11-03"}
    body.pop(field)
    response = await client.post(BASE, headers=headers, json=body)
    assert response.status_code == 422, response.text


async def test_decimal_receipt_posts_to_item_and_inventory_api(receipt_context):
    client, sessions, headers = receipt_context
    body = {
        **BODY,
        "ngay_nhap": "2026-11-03",
        "ghi_chu": "Nhập bổ sung",
        "chi_tiet": [{"mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": "0.10"}],
    }
    created = await client.post(BASE, headers=headers, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["data"]["tong_tien"] == "0.30"
    assert created.json()["data"]["chi_tiet"][0]["don_gia_thuc"] == "0.10"
    async with sessions() as db:
        await (await db.connection()).run_sync(lambda sync: Base.metadata.create_all(sync))
        assert (await db.get(Part, 1)).so_luong_ton == 0
        await db.commit()
    done = await client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**headers, "If-Match": created.headers["etag"]},
        json={},
    )
    assert done.status_code == 200, done.text
    async with sessions() as db:
        part = await db.get(Part, 1)
        assert part.so_luong_ton == 3
        assert part.ton_kho_updated_at.tzinfo is not None
        assert await db.scalar(select(func.sum(StockMovement.so_luong_bien_dong))) == 3
        assert (await db.scalar(select(func.count()).select_from(StockMovement))) == 1
        assert Decimal(done.json()["data"]["tong_tien"]) == Decimal("0.30")
    stocks = await client.get("/api/v1/inventory/stock", headers=headers)
    assert stocks.status_code == 200, stocks.text
    stock = next(row for row in stocks.json()["data"] if row["mat_hang_id"] == 1)
    assert stock["id"] == 1 and stock["so_luong"] == 3


@pytest.mark.parametrize(
    "field,value",
    [
        ("ncc_id", None),
        ("ngay_nhap", None),
        ("ngay_nhap", "2026-02-30"),
        ("ngay_nhap", 0),
        ("ngay_nhap", "2026-11-03T00:00:00Z"),
    ],
)
async def test_required_fields_reject_invalid_values(receipt_context, field, value):
    client, _, headers = receipt_context
    result = await client.post(BASE, headers=headers, json={**BODY, field: value})
    assert result.status_code == 422, result.text


@pytest.mark.parametrize(
    "price", ["-0.01", "0.001", "10000000000000000", "NaN", "Infinity", 0.1, True, None]
)
async def test_money_rejects_invalid_precision_or_inexact_input(receipt_context, price):
    client, _, headers = receipt_context
    result = await client.post(
        BASE,
        headers=headers,
        json={
            **BODY,
            "chi_tiet": [{**BODY["chi_tiet"][0], "don_gia_thuc": price}],
        },
    )
    assert result.status_code == 422, result.text


@pytest.mark.parametrize("quantity", [0, -1])
async def test_quantity_must_be_positive(receipt_context, quantity):
    client, _, headers = receipt_context
    result = await client.post(
        BASE,
        headers=headers,
        json={
            **BODY,
            "chi_tiet": [{**BODY["chi_tiet"][0], "so_luong": quantity}],
        },
    )
    assert result.status_code == 422, result.text


@pytest.mark.parametrize("price", ["2147483648.25", "9999999999999999.99"])
async def test_numeric_money_accepts_values_above_integer_range(receipt_context, price):
    client, _, headers = receipt_context
    result = await client.post(
        BASE,
        headers=headers,
        json={
            **BODY,
            "chi_tiet": [{"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": price}],
        },
    )
    assert result.status_code == 201, result.text
    assert result.json()["data"]["tong_tien"] == price


async def test_database_identity_and_completion_without_legacy_stock_table(receipt_context):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync))
        for table, seed in (("phieu_nhap", 51), ("chi_tiet_phieu_nhap", 71)):
            columns = await connection.run_sync(
                lambda sync, table=table: inspect(sync).get_columns(table)
            )
            assert next(c for c in columns if c["name"] == "id")["identity"]
            await db.execute(
                text("SELECT setval(pg_get_serial_sequence(:table,'id'),:seed,false)"),
                {"table": table, "seed": seed},
            )
        # Only the isolated, rolled-back test schema is touched.
        await db.execute(text("DROP TABLE ton_kho"))
        await db.commit()
    created = await client.post(BASE, headers=headers, json=BODY)
    assert created.status_code == 201, created.text
    assert created.json()["data"]["id"] == 51
    assert created.json()["data"]["chi_tiet"][0]["id"] == 71
    done = await client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**headers, "If-Match": created.headers["etag"]},
        json={},
    )
    assert done.status_code == 200, done.text
    assert (await client.get("/api/v1/inventory/stock", headers=headers)).status_code == 200


async def test_patch_date_note_and_required_fields(receipt_context):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        await (await db.connection()).run_sync(lambda sync: Base.metadata.create_all(sync))
        await db.commit()
    created = await client.post(BASE, headers=headers, json=BODY)
    path = created.headers["location"]
    headers = {**headers, "If-Match": created.headers["etag"]}
    for body in ({"ncc_id": None}, {"ngay_nhap": None}, {"ngay_nhap": "bad"}):
        assert (await client.patch(path, headers=headers, json=body)).status_code == 422
    changed = await client.patch(
        path, headers=headers, json={"ngay_nhap": "2026-11-04", "ghi_chu": "Receipt note"}
    )
    assert changed.status_code == 200, changed.text
    assert changed.headers["etag"] != created.headers["etag"]
    assert changed.json()["data"]["ngay_nhap"] == "2026-11-04"
    cleared = await client.patch(
        path, headers={**headers, "If-Match": changed.headers["etag"]}, json={"ghi_chu": None}
    )
    assert cleared.json()["data"]["ghi_chu"] is None
    assert cleared.json()["data"]["chi_tiet"] == created.json()["data"]["chi_tiet"]


async def test_legacy_create_recalculates_money_and_uses_authenticated_creator(receipt_context):
    client, _, headers = receipt_context
    response = await client.post(
        "/api/v1/receiving",
        headers=headers,
        json={
            "ma_phieu_nhap": "PN-202611-000555",
            "ncc_id": 1,
            "ngay_nhap": "2026-11-03",
            "nhan_vien_id": 1,
            "tong_tien": "999.99",
            "items": [
                {"mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": "0.10", "tong_gia": "999.99"}
            ],
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["nhan_vien_id"] == 2
    assert response.json()["tong_tien"] == response.json()["items"][0]["tong_gia"] == "0.30"
