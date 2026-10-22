"""Employee API contract v2, exercised against an isolated in-memory database."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.modules.nhan_vien.models import Role, User


@pytest.fixture
async def users_client():
    from app.main import app

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda conn: Base.metadata.create_all(conn, tables=[Role.__table__, User.__table__])
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                Role(id=1, ma_vai_tro="quan_tri_vien"),
                Role(id=2, ma_vai_tro="quan_ly"),
                Role(id=3, ma_vai_tro="nhan_vien"),
            ]
        )
        for user_id, role_id, state in [
            (1, 1, "hoat_dong"),
            (2, 2, "hoat_dong"),
            (3, 3, "hoat_dong"),
            (4, 3, "bi_khoa"),
        ]:
            session.add(
                User(
                    id=user_id,
                    vai_tro_id=role_id,
                    ma_nhan_vien=f"NV00{user_id}",
                    ten_dang_nhap=f"user{user_id}",
                    mat_khau="private-hash",
                    tai_khoan_id=123,
                    ho_ten="Same name",
                    email=f"user{user_id}@example.com",
                    he_so_luong=Decimal("1.25"),
                    trang_thai=state,
                )
            )
        await session.commit()

        async def override_db():
            yield session

        previous = app.dependency_overrides.copy()
        app.dependency_overrides[get_db] = override_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, session
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous)
    await engine.dispose()


def auth(user_id):
    # Permissions must come from the DB, even when JWT claims say admin.
    return {"Authorization": f"Bearer {create_access_token(user_id, ['quan_tri_vien'])}"}


async def test_admin_profile_and_detail_etag(users_client):
    client, session = users_client
    response = await client.get("/api/v1/nhan_vien/3", headers=auth(1))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"data", "meta"}
    assert body["meta"]["request_id"]
    assert body["data"]["he_so_luong"] == "1.25"
    assert body["data"]["ma_vai_tro"] == "nhan_vien"
    assert body["data"]["email"] == "user3@example.com"
    assert not {"mat_khau", "tai_khoan_id", "loai_nhan_vien", "is_active"} & body["data"].keys()
    etag = response.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"') and not etag.startswith("W/")
    again = await client.get("/api/v1/nhan_vien/3", headers=auth(1))
    assert again.headers["etag"] == etag
    user = await session.get(User, 3)
    user.ho_ten = "Changed"
    await session.commit()
    assert (await client.get("/api/v1/nhan_vien/3", headers=auth(1))).headers["etag"] != etag


async def test_manager_projection_and_own_profile(users_client):
    client, _ = users_client
    allowed = {"id", "ma_nhan_vien", "ho_ten", "vai_tro_id", "ma_vai_tro", "trang_thai"}
    listing = await client.get("/api/v1/nhan_vien", headers=auth(2))
    assert listing.status_code == 200
    assert all(set(item) == allowed for item in listing.json()["data"])
    detail = await client.get("/api/v1/nhan_vien/3", headers=auth(2))
    assert set(detail.json()["data"]) == allowed
    own = await client.get("/api/v1/nhan_vien/2", headers=auth(2))
    assert own.json()["data"]["email"] == "user2@example.com"


async def test_full_profile_keeps_nullable_fields(users_client):
    client, _ = users_client
    for path, actor_id in [
        ("/api/v1/nhan_vien", 1),
        ("/api/v1/nhan_vien/3", 1),
        ("/api/v1/nhan_vien/2", 2),
        ("/api/v1/nhan_vien/3", 3),
    ]:
        response = await client.get(path, headers=auth(actor_id))
        assert response.status_code == 200
        data = response.json()["data"]
        profiles = data if isinstance(data, list) else [data]
        for profile in profiles:
            assert profile["ngay_sinh"] is None
            assert profile["so_dien_thoai"] is None
            assert profile["ngay_vao_lam"] is None


async def test_hidden_profile_changes_do_not_change_manager_etag(users_client):
    client, session = users_client
    path = "/api/v1/nhan_vien/3"
    manager_before = await client.get(path, headers=auth(2))
    admin_before = await client.get(path, headers=auth(1))
    user = await session.get(User, 3)
    user.email = "changed@example.com"
    user.he_so_luong = Decimal("2.50")
    await session.commit()
    manager_after = await client.get(path, headers=auth(2))
    admin_after = await client.get(path, headers=auth(1))
    assert manager_after.headers["etag"] == manager_before.headers["etag"]
    assert manager_after.json()["data"] == manager_before.json()["data"]
    assert admin_after.headers["etag"] != admin_before.headers["etag"]
    assert admin_after.json()["data"]["email"] == "changed@example.com"


async def test_employee_scope_and_missing_id(users_client):
    client, _ = users_client
    assert (await client.get("/api/v1/nhan_vien", headers=auth(3))).status_code == 403
    assert (await client.get("/api/v1/nhan_vien/2", headers=auth(3))).status_code == 403
    assert (await client.get("/api/v1/nhan_vien/999", headers=auth(3))).status_code == 404
    own = await client.get("/api/v1/nhan_vien/3", headers=auth(3))
    assert own.status_code == 200 and own.json()["data"]["email"] == "user3@example.com"


async def test_large_positive_integers_do_not_overflow_database(users_client):
    client, _ = users_client
    for employee_id in [2**31, 2**100]:
        assert (
            await client.get(f"/api/v1/nhan_vien/{employee_id}", headers=auth(1))
        ).status_code == 404
    for query in [f"vai_tro_id={2**100}", f"page={2**100}"]:
        response = await client.get(f"/api/v1/nhan_vien?{query}", headers=auth(1))
        assert response.status_code == 200
        assert response.json()["data"] == []


async def test_current_database_role_overrides_old_token(users_client):
    client, session = users_client
    headers = auth(3)
    assert (await client.get("/api/v1/nhan_vien", headers=headers)).status_code == 403
    user = await session.get(User, 3)
    user.vai_tro_id = 2
    user.role = await session.get(Role, 2)
    await session.commit()
    listing = await client.get("/api/v1/nhan_vien", headers=headers)
    assert listing.status_code == 200
    assert all("email" not in row for row in listing.json()["data"])
    full = await client.get("/api/v1/nhan_vien/1", headers=auth(1))
    projection = await client.get("/api/v1/nhan_vien/1", headers=headers)
    assert full.headers["etag"] != projection.headers["etag"]


async def test_list_filters_sort_and_pagination(users_client):
    client, _ = users_client
    response = await client.get(
        "/api/v1/nhan_vien?vai_tro_id=3&trang_thai=hoat_dong&q=NV003", headers=auth(1)
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [3]
    response = await client.get("/api/v1/nhan_vien?page=2&page_size=2&sort=-id", headers=auth(1))
    assert [item["id"] for item in response.json()["data"]] == [2, 1]
    assert {k: v for k, v in response.json()["meta"].items() if k != "request_id"} == {
        "page": 2,
        "page_size": 2,
        "total": 4,
        "total_pages": 2,
    }
    response = await client.get("/api/v1/nhan_vien?sort=ho_ten&page_size=2&page=2", headers=auth(1))
    assert [item["id"] for item in response.json()["data"]] == [3, 4]
    response = await client.get("/api/v1/nhan_vien?q=missing", headers=auth(1))
    assert response.json()["data"] == []
    assert response.json()["meta"]["total_pages"] == 0
    response = await client.get("/api/v1/nhan_vien?q=%27%20OR%201=1--", headers=auth(1))
    assert response.json()["data"] == []


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=101",
        "page_size=0",
        "trang_thai=invalid",
        "sort=mat_khau",
        "sort=created_at",
        "search=NV",
        "extra=1",
        "vai_tro_id=0",
        "sort=id&sort=-id",
    ],
)
async def test_invalid_query_is_422(users_client, query):
    client, _ = users_client
    response = await client.get(f"/api/v1/nhan_vien?{query}", headers=auth(1))
    assert response.status_code == 422


@pytest.mark.parametrize("path", ["0", "-1", "abc", "3?extra=1"])
async def test_invalid_detail_request_is_422(users_client, path):
    client, _ = users_client
    assert (await client.get(f"/api/v1/nhan_vien/{path}", headers=auth(1))).status_code == 422


@pytest.mark.parametrize("state", ["bi_khoa", None, "invalid"])
async def test_inactive_account_cannot_use_existing_token(users_client, state):
    client, session = users_client
    user = await session.get(User, 1)
    user.trang_thai = state
    await session.commit()
    for path in ["/api/v1/nhan_vien", "/api/v1/nhan_vien/1"]:
        assert (await client.get(path, headers=auth(1))).status_code == 403


async def test_missing_role_has_no_fallback_permissions(users_client):
    client, session = users_client
    user = await session.get(User, 3)
    user.vai_tro_id = None
    user.role = None
    await session.commit()
    assert (await client.get("/api/v1/nhan_vien", headers=auth(3))).status_code == 403


async def test_employee_routes_and_auth_required(users_client):
    from app.main import app

    client, _ = users_client
    routes = {
        path: set(methods)
        for path, methods in app.openapi()["paths"].items()
        if "/nhan_vien" in path
    }
    assert routes == {
        "/api/v1/nhan_vien": {"get", "post"},
        "/api/v1/nhan_vien/{id}": {"get", "patch", "delete"},
        "/api/v1/nhan_vien/{id}/vai_tro": {"put"},
        "/api/v1/nhan_vien/{id}/vo_hieu_hoa": {"post"},
    }
    for path in ["/api/v1/nhan_vien", "/api/v1/nhan_vien/{id}"]:
        assert (await client.get(path.replace("{id}", "1"))).status_code == 401
    assert (await client.post("/api/v1/nhan_vien", headers=auth(1), json={})).status_code == 422
    assert (await client.get("/api/v1/nguoi_dung", headers=auth(1))).status_code == 404


def test_openapi_documents_supported_queries_and_etag():
    from app.main import app

    paths = app.openapi()["paths"]
    params = paths["/api/v1/nhan_vien"]["get"]["parameters"]
    assert {param["name"] for param in params} == {
        "page",
        "page_size",
        "q",
        "sort",
        "vai_tro_id",
        "trang_thai",
    }
    assert "ETag" in paths["/api/v1/nhan_vien/{id}"]["get"]["responses"]["200"]["headers"]
