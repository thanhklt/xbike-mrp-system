"""Catalog UC/AC HTTP tests using database roles and real dependencies."""

import pytest
from test_bom_api import client as client
from test_bom_api import headers
from test_bom_postgres import database as database
from test_catalog_service import SUPPLIER


@pytest.mark.parametrize(
    "user,item_status,supplier_status", [(1, 200, 200), (2, 200, 403), (3, 200, 200), (4, 403, 403)]
)
async def test_cat_ac01_read_roles_from_database(client, user, item_status, supplier_status):
    for path in ["mat_hang", "mat_hang/1", "danh_muc_mat_hang/"]:
        response = await client.get("/api/v1/" + path, headers=headers(user, roles=["quan_ly"]))
        assert response.status_code == item_status, response.text
    response = await client.get("/api/v1/nha_cung_cap", headers=headers(user))
    assert response.status_code == supplier_status, response.text


@pytest.mark.parametrize(
    "auth",
    [{}, {"Authorization": "Bearer invalid"}, headers(expired=True), headers(version="stale")],
)
async def test_cat_ac01_authentication(client, auth):
    for path in ["mat_hang", "nha_cung_cap"]:
        result = await client.get("/api/v1/" + path, headers=auth)
        assert result.status_code == 401 and result.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["mat_hang", "nha_cung_cap"])
@pytest.mark.parametrize(
    "query", ["page=0", "page_size=101", "sort=unknown", "foo=x", "page=1&page=2"]
)
async def test_cat_ac02_invalid_queries(client, path, query):
    result = await client.get(f"/api/v1/{path}?{query}", headers=headers())
    assert result.status_code == 422, result.text


@pytest.mark.parametrize("path", ["mat_hang", "nha_cung_cap"])
@pytest.mark.parametrize(
    "value,status", [("0", 422), ("bad", 422), (str(2**70), 404), ("999", 404)]
)
async def test_cat_ac02_detail_errors(client, path, value, status):
    result = await client.get(f"/api/v1/{path}/{value}", headers=headers())
    assert result.status_code == status, result.text


@pytest.mark.parametrize("path", ["mat_hang", "mat_hang/1", "danh_muc_mat_hang/", "nha_cung_cap"])
async def test_cat_ac07_get_rejects_body(client, path):
    result = await client.request("GET", f"/api/v1/{path}", headers=headers(), json={})
    assert result.status_code == 422, result.text


@pytest.mark.parametrize("user", [2, 3])
async def test_uc14_uc44_cat_ac01_write_roles(client, user):
    created = await client.post("/api/v1/nha_cung_cap", headers=headers(), json=SUPPLIER)
    assert created.status_code == 201, created.text
    for method, path, body in [
        ("POST", "/api/v1/nha_cung_cap", SUPPLIER),
        ("PATCH", created.headers["location"], {"ten_ncc": "New"}),
    ]:
        result = await client.request(
            method, path, headers={**headers(user), "If-Match": created.headers["etag"]}, json=body
        )
        assert result.status_code == 403, result.text


@pytest.mark.parametrize(
    "tag,status",
    [(None, 428), ("", 428), ("*", 412), ('W/"x"', 412), ('"old"', 412), ('"x", "y"', 412)],
)
async def test_uc44_cat_ac05_required_strong_precondition(client, tag, status):
    created = await client.post("/api/v1/nha_cung_cap", headers=headers(), json=SUPPLIER)
    assert created.status_code == 201, created.text
    auth = headers()
    if tag is not None:
        auth["If-Match"] = tag
    result = await client.patch(created.headers["location"], headers=auth, json={})
    assert result.status_code == status, result.text


@pytest.mark.parametrize("body", [{}, {"ma_ncc": "NCC-000002", **SUPPLIER}, {**SUPPLIER, "id": 1}])
async def test_uc14_cat_ac02_post_generated_fields_and_missing_body(client, body):
    result = await client.post("/api/v1/nha_cung_cap", headers=headers(), json=body)
    assert result.status_code == 422, result.text


async def test_uc14_uc44_http_roundtrip_and_unsupported_delete(client):
    created = await client.post("/api/v1/nha_cung_cap", headers=headers(), json=SUPPLIER)
    assert created.status_code == 201, created.text
    assert created.json()["data"] == {**SUPPLIER, "id": 1, "ma_ncc": "NCC-000001"}
    path = created.headers["location"]
    read = await client.get(path, headers=headers(3))
    assert read.headers["etag"] == created.headers["etag"]
    patched = await client.patch(
        path, json={"ten_ncc": "Changed"}, headers={**headers(), "If-Match": read.headers["etag"]}
    )
    assert patched.status_code == 200 and patched.headers["etag"] != read.headers["etag"], (
        patched.text
    )
    unchanged = await client.patch(
        path, json={}, headers={**headers(), "If-Match": patched.headers["etag"]}
    )
    assert unchanged.status_code == 200 and unchanged.headers["etag"] == patched.headers["etag"]
    assert (await client.delete(path, headers=headers())).status_code == 405


async def test_uc13_ac06_partial_address_filters_over_http(client):
    for tinh, phuong in [
        ("Thành phố Hà Nội", "Phường Đống Đa"),
        ("THÀNH PHỐ HÀ NỘI", "PHƯỜNG ĐỐNG ĐA"),
        ("Thành phố Hồ Chí Minh", "Phường Đống Đa"),
    ]:
        created = await client.post(
            "/api/v1/nha_cung_cap",
            headers=headers(),
            json={**SUPPLIER, "tinh": tinh, "phuong": phuong},
        )
        assert created.status_code == 201, created.text

    found = []
    for page in [1, 2, 3]:
        response = await client.get(
            "/api/v1/nha_cung_cap",
            headers=headers(3),
            params={"tinh": " HA NOI ", "phuong": "dong da", "page_size": 1, "page": page},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["meta"]["total"] == 2 and body["meta"]["total_pages"] == 2
        assert body["meta"]["request_id"]
        found.extend(row["id"] for row in body["data"])
        if page == 1:
            assert body["data"][0]["tinh"] == "Thành phố Hà Nội"
    assert found == [1, 2]

    response = await client.get(
        "/api/v1/nha_cung_cap",
        headers=headers(),
        params={"tinh": "ha noi", "phuong": "minh hoa"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == [] and response.json()["meta"]["total"] == 0


@pytest.mark.parametrize("path", ["mat_hang/1", "nha_cung_cap/1"])
async def test_cat_ac05_repeated_if_match_is_rejected(client, path):
    if path.startswith("nha"):
        await client.post("/api/v1/nha_cung_cap", headers=headers(), json=SUPPLIER)
    current = await client.get("/api/v1/" + path, headers=headers())
    auth = list(headers().items()) + [("If-Match", current.headers["etag"])] * 2
    result = await client.patch("/api/v1/" + path, headers=auth, json={})
    assert result.status_code == 412, result.text


@pytest.mark.parametrize(
    "query", ["don_gia_min=200&don_gia_max=1", "is_active=true&loai_mat_hang=linh_kien"]
)
async def test_uc09_cat_ac02_invalid_filter_combination(client, query):
    response = await client.get("/api/v1/mat_hang?" + query, headers=headers())
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", 5),
        ("ma_mat_hang", "MH-000009"),
        ("loai_mat_hang", "thanh_pham"),
        ("so_luong_ton", 100),
        ("so_luong_dang_giu", 1),
        ("so_luong_con_dung", 2),
        ("sku", "  "),
        ("don_gia", 1.5),
        ("don_gia", True),
    ],
)
async def test_uc11_cat_ac02_immutable_and_structural_fields(client, field, value):
    current = await client.get("/api/v1/mat_hang/1", headers=headers())
    response = await client.patch(
        "/api/v1/mat_hang/1",
        headers={**headers(), "If-Match": current.headers["etag"]},
        json={field: value},
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("user", [2, 3])
async def test_uc10_uc11_uc12_cat_ac01_item_write_roles(client, user):
    current = await client.get("/api/v1/mat_hang/1", headers=headers())
    auth = {**headers(user), "If-Match": current.headers["etag"]}
    payload = {
        "ten_mat_hang": "Part",
        "sku": "new",
        "loai_mat_hang": "linh_kien",
        "don_vi_tinh": "chiec",
        "don_gia": 1,
    }
    for method, path, body in [
        ("POST", "/api/v1/mat_hang", payload),
        ("PATCH", "/api/v1/mat_hang/1", {}),
    ]:
        result = await client.request(method, path, headers=auth, json=body)
        assert result.status_code == 403, result.text
    result = await client.delete("/api/v1/mat_hang/1", headers=auth)
    assert result.status_code == 403, result.text


def test_cat_ac07_openapi_matches_catalog_contract():
    from app.main import app

    schema = app.openapi()
    paths = schema["paths"]
    assert set(paths["/api/v1/nha_cung_cap/{id}"]) == {"get", "patch"}
    assert "ETag" in paths["/api/v1/nha_cung_cap/{id}"]["get"]["responses"]["200"]["headers"]
    assert {"412", "428"} <= paths["/api/v1/nha_cung_cap/{id}"]["patch"]["responses"].keys()
    assert "UC-44" in paths["/api/v1/nha_cung_cap/{id}"]["patch"]["description"]
    assert "ma_ncc" not in schema["components"]["schemas"]["NhaCungCapCreate"]["properties"]
    assert "nha_cung_cap" in schema["components"]["schemas"]["PhieuNhapRead"]["required"]


@pytest.mark.parametrize(
    "body", [{"ma_ncc": "NCC-000999"}, {"dia_chi": None}, {"dia_chi": " \t "}, {"unknown": 1}]
)
async def test_uc44_ac02_ac03_reject_bad_patch_without_changes(client, body):
    created = await client.post("/api/v1/nha_cung_cap", headers=headers(), json=SUPPLIER)
    path = created.headers["location"]
    response = await client.patch(
        path, headers={**headers(), "If-Match": created.headers["etag"]}, json=body
    )
    assert response.status_code == 422, response.text
    after = await client.get(path, headers=headers())
    assert (
        after.headers["etag"] == created.headers["etag"]
        and after.json()["data"] == created.json()["data"]
    )


async def test_cat_ac07_internal_error_does_not_leak_database_details(client):
    from unittest.mock import AsyncMock

    from app.dependencies import get_suppliers_service
    from app.main import app

    service = AsyncMock()
    service.list_suppliers.side_effect = RuntimeError("private_connection_secret")
    app.dependency_overrides[get_suppliers_service] = lambda: service
    try:
        response = await client.get("/api/v1/nha_cung_cap", headers=headers())
        assert response.status_code == 500
        assert "private_connection_secret" not in response.text
        assert response.json()["meta"]["request_id"]
    finally:
        app.dependency_overrides.pop(get_suppliers_service, None)
