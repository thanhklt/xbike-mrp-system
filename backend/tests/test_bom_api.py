"""UC/AC HTTP contracts using real auth, services and an isolated PostgreSQL v4 DB."""

from datetime import timedelta

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from test_bom_postgres import database as database
from test_bom_postgres import product, scalar

from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.main import app


def headers(user=1, *, roles=None, expired=False, version="test-hash"):
    token = create_access_token(
        user,
        roles=roles or ["quan_ly"],
        credential_version=password_version(version),
        expires_delta=timedelta(seconds=-10) if expired else timedelta(minutes=5),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client(database):
    previous = app.state.mat_hang_cache
    app.state.mat_hang_cache = database.cache

    async def test_db():
        async with database.sessions() as session:
            try:
                yield session
            finally:
                await session.rollback()

    app.dependency_overrides[get_db] = test_db
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.state.mat_hang_cache = previous


@pytest.mark.parametrize("user,status", [(1, 200), (2, 200), (3, 403), (4, 403)])
async def test_uc15_roles_use_database_not_jwt_claims(client, database, user, status):
    await product(database)
    response = await client.get("/api/v1/bom", headers=headers(user, roles=["quan_ly"]))
    assert response.status_code == status, response.text
    if status == 200:
        assert response.json()["meta"]["total"] == 1


@pytest.mark.parametrize(
    "auth",
    [{}, {"Authorization": "Bearer invalid"}, headers(expired=True), headers(version="stale")],
)
async def test_bom_ac01_unauthenticated(client, auth):
    response = await client.get("/api/v1/bom", headers=auth)
    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=101",
        "unexpected=x",
        "sort=start_time",
        "sort=unknown",
        "version=0",
        "is_active=invalid",
        "page=1&page=2",
        "version=99999999999999999999",
        "mat_hang_id=99999999999999999999",
    ],
)
async def test_uc15_ac6_bad_query(client, query):
    response = await client.get("/api/v1/bom?" + query, headers=headers())
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "path,status", [("999", 404), (str(2**70), 404), ("0", 422), ("-1", 422), ("bad", 422)]
)
async def test_uc15_ac6_detail_errors(client, path, status):
    response = await client.get("/api/v1/bom/" + path, headers=headers())
    assert response.status_code == status, response.text


@pytest.mark.parametrize(
    "value,status", [(None, 428), ("", 428), ('"old"', 412), ("*", 412), ('W/"current"', 412)]
)
async def test_bom_ac07_write_preconditions(client, database, value, status):
    _, bom = await product(database)
    auth = headers()
    if value is not None:
        auth["If-Match"] = value
    response = await client.delete(f"/api/v1/bom/{bom}", headers=auth)
    assert response.status_code == status, response.text
    assert set(response.json()) == {"error", "meta"}
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2


@pytest.mark.parametrize("second", ["same", '"stale"', "*", ""])
@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("POST", "/phien_ban", {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 3}]}),
        ("POST", "/kich_hoat", {}),
        ("DELETE", "", None),
    ],
)
async def test_bom_ac07_repeated_if_match_rejected_without_writes(
    client, database, method, suffix, body, second
):
    """UC-17/18/19, T06/T07/T09: multiple physical headers are multiple validators."""
    _, bom = await product(database)
    path = f"/api/v1/bom/{bom}"
    if suffix == "/kich_hoat":
        current = await client.get(path, headers=headers())
        stopped = await client.delete(
            path, headers={**headers(), "If-Match": current.headers["etag"]}
        )
        assert stopped.status_code == 204, stopped.text

    async def snapshot():
        return [
            await scalar(database, f'SELECT jsonb_agg(to_jsonb(t)) FROM "{name}" t')
            for name in ("Bom", "ChiTietBom", "MatHang", "LichSuThaoTac")
        ]

    current = await client.get(path, headers=headers())
    assert current.status_code == 200, current.text
    tag = current.headers["etag"]
    before, cached = await snapshot(), database.cache.snapshot()
    auth = list(headers().items()) + [
        ("If-Match", tag),
        ("If-Match", tag if second == "same" else second),
    ]
    response = await client.request(method, path + suffix, headers=auth, json=body)

    assert response.status_code == 412, response.text
    assert set(response.json()) == {"error", "meta"}
    assert await snapshot() == before
    assert database.cache.snapshot() is cached
    after = await client.get(path, headers=headers())
    assert after.headers["etag"] == tag


@pytest.mark.parametrize("user", [2, 3, 4])
@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("post", "/phien_ban", {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 1}]}),
        ("post", "/kich_hoat", {}),
        ("delete", "", None),
    ],
)
async def test_bom_ac01_all_mutations_denied(client, database, user, method, suffix, body):
    _, bom = await product(database)
    response = await client.request(
        method, f"/api/v1/bom/{bom}{suffix}", json=body, headers=headers(user)
    )
    assert response.status_code == 403, response.text
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 1


async def test_uc17_uc18_uc19_http_lifecycle(client, database):
    item, first = await product(database)
    read = await client.get(f"/api/v1/bom/{first}", headers=headers(2))
    assert read.status_code == 200
    assert {"created_at", "kich_hoat_gan_nhat_at"} <= read.json()["data"].keys()
    assert "start_time" not in read.json()["data"]
    original = read.json()["data"]
    new = await client.post(
        f"/api/v1/bom/{first}/phien_ban",
        json={"chi_tiet": [{"mat_hang_id": 2, "so_luong": 4}]},
        headers={**headers(), "If-Match": read.headers["etag"]},
    )
    assert new.status_code == 201, new.text
    second = new.json()["data"]["id"]
    assert new.headers["location"] == f"/api/v1/bom/{second}"
    old = await client.get(f"/api/v1/bom/{first}", headers=headers())
    assert old.headers["etag"] != read.headers["etag"]
    assert old.json()["data"]["chi_tiet"] == original["chi_tiet"]
    reused = await client.post(
        f"/api/v1/bom/{first}/kich_hoat",
        json={},
        headers={**headers(), "If-Match": old.headers["etag"]},
    )
    assert reused.status_code == 200, reused.text
    assert reused.json()["data"]["created_at"] == original["created_at"]
    assert reused.json()["data"]["kich_hoat_gan_nhat_at"] > original["kich_hoat_gan_nhat_at"]
    repeated = await client.post(
        f"/api/v1/bom/{first}/kich_hoat",
        json={},
        headers={**headers(), "If-Match": reused.headers["etag"]},
    )
    assert repeated.status_code == 409, repeated.text
    archived = await client.get(f"/api/v1/bom/{second}", headers=headers())
    wrong_stop = await client.delete(
        f"/api/v1/bom/{second}", headers={**headers(), "If-Match": archived.headers["etag"]}
    )
    assert wrong_stop.status_code == 409, wrong_stop.text
    assert (await client.get(f"/api/v1/bom/{first}", headers=headers())).json()["data"]["is_active"]
    stopped = await client.delete(
        f"/api/v1/bom/{first}", headers={**headers(), "If-Match": reused.headers["etag"]}
    )
    assert stopped.status_code == 204 and not stopped.content
    tree = await client.get(f"/api/v1/bom/{first}/cau_truc", headers=headers(2))
    assert tree.status_code == 200
    assert tree.json()["data"]["children"][0]["children"] == []
    assert not database.cache.snapshot().by_id[item].is_active
    audit = await client.get("/api/v1/audit", headers=headers())
    assert audit.status_code == 200, audit.text
    assert "tao_phien_ban" in audit.text and "dung_lai_phien_ban" in audit.text


async def test_uc17_old_post_removed_and_openapi_trace(client):
    assert (await client.post("/api/v1/bom", json={}, headers=headers())).status_code == 405
    paths = app.openapi()["paths"]
    assert "post" not in paths["/api/v1/bom"]
    assert "post" in paths["/api/v1/bom/{id}/phien_ban"]


async def test_bom_ac01_changed_role_and_locked_account_take_effect(client, database):
    async with database.sessions() as session:
        await session.execute(text('UPDATE "NhanVien" SET vai_tro_id=3 WHERE id=1'))
        await session.commit()
    assert (await client.get("/api/v1/bom", headers=headers(1))).status_code == 403


@pytest.mark.parametrize(
    "method,path,body",
    [("get", "/api/v1/bom", {}), ("get", "/api/v1/bom/1", {}), ("delete", "/api/v1/bom/1", {})],
)
async def test_bom_ac07_no_body_endpoints_reject_body(client, method, path, body):
    response = await client.request(method, path, json=body, headers=headers())
    assert response.status_code == 422


@pytest.mark.parametrize("body", [None, {"unexpected": 1}])
async def test_uc18_ac6_requires_explicit_empty_body(client, database, body):
    _, bom = await product(database)
    response = await client.post(f"/api/v1/bom/{bom}/kich_hoat", json=body, headers=headers())
    assert response.status_code == 422


@pytest.mark.parametrize("component,status", [(999, 404), (3, 422)])
async def test_uc17_ac7_invalid_formula_preserves_old_version(client, database, component, status):
    _, bom = await product(database)
    read = await client.get(f"/api/v1/bom/{bom}", headers=headers())
    response = await client.post(
        f"/api/v1/bom/{bom}/phien_ban",
        json={"chi_tiet": [{"mat_hang_id": component, "so_luong": 1}]},
        headers={**headers(), "If-Match": read.headers["etag"]},
    )
    assert response.status_code == status
    again = await client.get(f"/api/v1/bom/{bom}", headers=headers())
    assert again.headers["etag"] == read.headers["etag"]


async def test_bom_ac05_catalog_tag_changes_when_only_formula_changes(client, database):
    item, bom = await product(database)
    item_before = await client.get(f"/api/v1/mat_hang/{item}", headers=headers())
    read = await client.get(f"/api/v1/bom/{bom}", headers=headers())
    response = await client.post(
        f"/api/v1/bom/{bom}/phien_ban",
        json={"chi_tiet": [{"mat_hang_id": 1, "so_luong": 9}]},
        headers={**headers(), "If-Match": read.headers["etag"]},
    )
    assert response.status_code == 201
    item_after = await client.get(f"/api/v1/mat_hang/{item}", headers=headers())
    assert item_before.json()["data"] == item_after.json()["data"]
    assert item_before.headers["etag"] != item_after.headers["etag"]
    patch = await client.patch(
        f"/api/v1/mat_hang/{item}",
        json={"is_active": False},
        headers={**headers(), "If-Match": item_before.headers["etag"]},
    )
    assert patch.status_code == 412


async def test_uc15_bom_ac03_reads_do_not_write(client, database):
    _, bom = await product(database)

    async def snapshot():
        return [
            await scalar(database, f'SELECT jsonb_agg(to_jsonb(t)) FROM "{name}" t')
            for name in ("Bom", "ChiTietBom", "MatHang", "LichSuThaoTac")
        ]

    before = await snapshot()
    for suffix in ("", f"/{bom}", f"/{bom}/cau_truc"):
        response = await client.get("/api/v1/bom" + suffix, headers=headers(2))
        assert response.status_code == 200
    assert await snapshot() == before


async def test_bom_ac07_unexpected_failure_returns_safe_500(client, monkeypatch):
    from app.modules.bom.repository import SqlAlchemyBomRepository

    async def fail(*args):
        raise RuntimeError("private-db-details-should-never-leak")

    monkeypatch.setattr(SqlAlchemyBomRepository, "context_for_bom", fail)
    response = await client.get("/api/v1/bom/1", headers=headers())
    assert response.status_code == 500
    assert "private-db-details" not in response.text
    assert set(response.json()) == {"error", "meta"}
