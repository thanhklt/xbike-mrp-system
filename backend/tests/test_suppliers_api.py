"""Supplier GET contracts using real JWTs and isolated PostgreSQL transactions."""

import pytest
from sqlalchemy import event, text

from app.main import app
from app.modules.nha_cung_cap.models import Supplier
from tests.test_auth_api import auth_context as auth_context
from tests.test_auth_api import login

BASE = "/api/v1/nha_cung_cap"


@pytest.fixture
async def supplier_context(auth_context):
    client, sessions = auth_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(lambda sync: Supplier.__table__.create(sync))
        db.add_all(
            [
                Supplier(
                    id=1, ma_ncc="NCC-000001", ten_ncc="Alpha", tinh="ha_noi", phuong="tay_ho"
                ),
                Supplier(
                    id=2, ma_ncc="NCC-000002", ten_ncc="Beta", tinh="ha_noi", phuong="ba_dinh"
                ),
                Supplier(
                    id=3, ma_ncc="NCC-000003", ten_ncc="Alpha", tinh="da_nang", phuong="hai_chau"
                ),
            ]
        )
        await db.commit()
    token = (await login(client)).json()["data"]["access_token"]
    yield client, sessions, {"Authorization": f"Bearer {token}"}


async def test_list_contract_and_stable_pagination(supplier_context):
    client, _, headers = supplier_context
    response = await client.get(
        BASE, headers=headers, params={"sort": "ten_ncc", "page_size": 1, "page": 2}
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert [item["id"] for item in body["data"]] == [3]
    assert body["meta"] == {
        "request_id": body["meta"]["request_id"],
        "page": 2,
        "page_size": 1,
        "total": 3,
        "total_pages": 3,
    }
    assert body["meta"]["request_id"]


async def test_detail_contract_has_stable_etag(supplier_context):
    client, _, headers = supplier_context
    first = await client.get(f"{BASE}/1", headers=headers)
    second = await client.get(f"{BASE}/1", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == {
        "id": 1,
        "ma_ncc": "NCC-000001",
        "ten_ncc": "Alpha",
        "so_dien_thoai": None,
        "dia_chi": None,
        "phuong": "tay_ho",
        "tinh": "ha_noi",
    }
    assert first.headers["etag"] == second.headers["etag"]
    assert first.headers["etag"].startswith('"')
    assert first.json()["meta"]["request_id"] != second.json()["meta"]["request_id"]


@pytest.mark.parametrize("index,status", [(1, 200), (2, 200), (3, 403)])
async def test_read_permissions(supplier_context, index, status):
    client, _, _ = supplier_context
    token = (await login(client, index)).json()["data"]["access_token"]
    for path in (BASE, f"{BASE}/1"):
        assert (
            await client.get(path, headers={"Authorization": f"Bearer {token}"})
        ).status_code == status
        assert (await client.get(path)).status_code == 401


@pytest.mark.parametrize(
    "query,ids",
    [
        ({"q": " alpha "}, [1, 3]),
        ({"q": "ncc-000002"}, [2]),
        ({"q": "ha_noi"}, []),
        ({"q": "' OR 1=1 --"}, []),
        ({"q": "%"}, []),
        ({"q": "_"}, []),
        ({"tinh": " ha_noi ", "phuong": "tay_ho"}, [1]),
        ({"q": "alpha", "tinh": "da_nang"}, [3]),
        ({"sort": "-id"}, [3, 2, 1]),
        ({"sort": "-ma_ncc"}, [3, 2, 1]),
        ({"sort": "ma_ncc"}, [1, 2, 3]),
        ({"sort": "-ten_ncc"}, [2, 1, 3]),
    ],
)
async def test_list_filters_sort_and_literal_search(supplier_context, query, ids):
    client, _, headers = supplier_context
    response = await client.get(BASE, headers=headers, params=query)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == ids
    assert response.json()["meta"]["total"] == len(ids)


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=1.5",
        "page_size=0",
        "page_size=101",
        "page_size=abc",
        "sort=dia_chi",
        "sort=id,ma_ncc",
        "search=alpha",
        "tu_ngay=2026-10-01",
        "page=1&page=2",
        "q=a&q=b",
        "tinh=a&tinh=b",
        "phuong=a&phuong=b",
        "sort=id&sort=-id",
        "page_size=1&page_size=2",
    ],
)
async def test_query_validation_contract(supplier_context, query):
    client, _, headers = supplier_context
    response = await client.get(f"{BASE}?{query}", headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    assert all(set(d) == {"field", "reason"} for d in response.json()["error"]["details"])


@pytest.mark.parametrize(
    "identifier,status",
    [("0", 422), ("-1", 422), ("abc", 422), ("1.5", 422), ("999", 404), (str(2**63), 404)],
)
async def test_detail_validation_and_not_found(supplier_context, identifier, status):
    client, _, headers = supplier_context
    response = await client.get(f"{BASE}/{identifier}", headers=headers)
    assert response.status_code == status
    assert response.json()["error"]["code"] == (
        "khong_tim_thay" if status == 404 else "du_lieu_khong_hop_le"
    )


async def test_pagination_boundaries_and_detail_query(supplier_context):
    client, _, headers = supplier_context
    assert (await client.get(f"{BASE}/1?q=ignored", headers=headers)).status_code == 422
    empty = await client.get(BASE, headers=headers, params={"q": "absent"})
    assert empty.json()["data"] == []
    assert empty.json()["meta"]["total_pages"] == 0
    response = await client.get(BASE, headers=headers, params={"page": 10**30})
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == 3


async def test_null_legacy_name_and_etag_change(supplier_context):
    client, sessions, headers = supplier_context
    before = await client.get(f"{BASE}/1", headers=headers)
    async with sessions() as db:
        await db.execute(text("UPDATE nha_cung_cap SET ten_ncc=NULL WHERE id=1"))
        await db.commit()
    after = await client.get(f"{BASE}/1", headers=headers)
    assert after.status_code == 200
    assert after.json()["data"]["ten_ncc"] is None
    assert before.headers["etag"] != after.headers["etag"]


async def test_get_never_writes(supplier_context):
    client, sessions, headers = supplier_context
    statements = []
    connection = sessions.kw["bind"].sync_connection

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement.lstrip().split()[0].upper())

    event.listen(connection, "before_cursor_execute", capture)
    try:
        for path in (BASE, f"{BASE}?q=alpha", f"{BASE}/1", f"{BASE}/999"):
            assert (await client.get(path, headers=headers)).status_code in (200, 404)
    finally:
        event.remove(connection, "before_cursor_execute", capture)
    assert "SELECT" in statements
    assert set(statements) <= {"SELECT", "SAVEPOINT", "RELEASE", "ROLLBACK"}


async def test_legacy_get_compatibility(supplier_context):
    client, _, headers = supplier_context
    response = await client.get("/api/v1/suppliers", headers=headers)
    assert response.status_code == 200
    assert "pagination" in response.json()
    detail = await client.get("/api/v1/suppliers/1", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["ma_ncc"] == "NCC-000001"


def test_read_openapi():
    paths = app.openapi()["paths"]
    listing = paths[BASE]["get"]
    detail = paths[f"{BASE}/{{id}}"]["get"]
    assert {p["name"] for p in listing["parameters"]} == {
        "page",
        "page_size",
        "q",
        "sort",
        "tinh",
        "phuong",
    }
    assert listing["security"] == detail["security"] == [{"OAuth2PasswordBearer": []}]
    assert "ETag" in detail["responses"]["200"]["headers"]
