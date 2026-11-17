"""Real UC-04 PostgreSQL tests, isolated from the application database.

Set NHAN_VIEN_CODE_TEST_DATABASE_URL to a dedicated local *_test database on
a test-only server owned by uc04_test. Each case creates/drops only its UUID DB.
"""

import asyncio
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.core.security import create_access_token, get_password_hash, password_version
from app.modules.audit.service import AuditService
from app.modules.auth.router import router as auth_router
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository
from app.modules.nhan_vien.router import router

BOOTSTRAP = Path(__file__).resolve().parents[2] / "infra/postgres/init.sql"


@pytest.fixture
async def empty_database():
    configured = os.environ.get("NHAN_VIEN_CODE_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("UC-04 PostgreSQL not verified: NHAN_VIEN_CODE_TEST_DATABASE_URL is required")
    url = make_url(configured)
    if not (
        url.drivername == "postgresql+asyncpg"
        and url.host in ("127.0.0.1", "localhost")
        and url.username == "uc04_test"
        and url.database
        and url.database.endswith("_test")
    ):
        pytest.fail("Refusing database not identified as a local uc04_test test server")
    name = f"uc04_{uuid4().hex}_test"
    admin = await asyncpg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    connection = None
    created = False
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        connection = await asyncpg.connect(
            url.set(drivername="postgresql", database=name).render_as_string(hide_password=False)
        )
        assert (
            await connection.fetchval(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
            )
            == 0
        )
        await connection.execute(BOOTSTRAP.read_text(encoding="utf-8"))
        yield connection
    finally:
        try:
            if connection is not None:
                await connection.close()
        finally:
            try:
                # Only the UUID database successfully created by this fixture may be dropped.
                assert name.startswith("uc04_") and name.endswith("_test") and len(name) == 42
                if created:
                    await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
            finally:
                await admin.close()


@pytest.fixture
async def database(empty_database):
    await empty_database.execute(
        """INSERT INTO "VaiTro" (id, ma_vai_tro, ten_vai_tro)
           VALUES (1, 'quan_tri_vien', 'Admin')"""
    )
    return empty_database


@pytest.fixture(scope="module")
def admin_hash():
    return get_password_hash("UC04-admin-test-password")


@pytest.fixture
async def api(database, admin_hash):
    url = make_url(os.environ["NHAN_VIEN_CODE_TEST_DATABASE_URL"])
    name = await database.fetchval("SELECT current_database()")
    assert name.startswith("uc04_") and name.endswith("_test") and len(name) == 42
    engine = create_async_engine(url.set(database=name), hide_parameters=True)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    await database.execute(
        """INSERT INTO "VaiTro" (id, ma_vai_tro, ten_vai_tro)
           VALUES (2, 'quan_ly', 'Manager'), (3, 'nhan_vien', 'Employee')"""
    )
    admin_id = await database.fetchval(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'uc04-admin', $1) RETURNING id""",
        admin_hash,
    )

    async def test_db():
        async with sessions() as session:
            try:
                yield session
            finally:
                await session.rollback()

    def headers(actor_id=admin_id):
        token = create_access_token(
            actor_id,
            ["quan_tri_vien"],
            credential_version=password_version(admin_hash),
            session_version=0,
        )
        return {"Authorization": f"Bearer {token}"}

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    # Only DB composition is overridden; JWT, services, repositories and transactions are real.
    app.dependency_overrides[get_db] = test_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield SimpleNamespace(client=client, headers=headers, sessions=sessions)
    finally:
        await engine.dispose()


async def test_patch_duplicate_username_rolls_back_database(database, api, monkeypatch):
    created = []
    for username in ("patch-first", "patch-second"):
        response = await api.client.post(
            "/api/v1/nhan_vien", headers=api.headers(),
            json={"ten_dang_nhap": username, "mat_khau": "123456", "vai_tro_id": 3},
        )
        assert response.status_code == 201, response.text
        created.append(response.json()["data"])
    before = await database.fetch('SELECT id, ten_dang_nhap FROM "NhanVien" ORDER BY id')
    audit_count = await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"')
    path = f"/api/v1/nhan_vien/{created[0]['id']}"
    detail = await api.client.get(path, headers=api.headers())

    async def unchecked(_self, _username):
        return None

    # Bỏ kiểm tra trước để kiểm chứng nhánh unique constraint tại UPDATE.
    monkeypatch.setattr(SqlAlchemyNhanVienRepository, "find_by_username", unchecked)
    response = await api.client.patch(
        path, headers={**api.headers(), "If-Match": detail.headers["etag"]},
        json={"ten_dang_nhap": created[1]["ten_dang_nhap"]},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "ten_dang_nhap_bi_trung"
    assert await database.fetch('SELECT id, ten_dang_nhap FROM "NhanVien" ORDER BY id') == before
    assert await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"') == audit_count


# UC-04 R6: hai INSERT không truyền mã nhận hai mã khác nhau đúng NV- + id sáu chữ số
async def test_insert_without_code_uses_identity(database):
    rows = await database.fetch(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'first', 'test-hash'), (1, 'second', 'test-hash')
           RETURNING id, ma_nhan_vien"""
    )
    assert len(rows) == 2
    assert len({row["ma_nhan_vien"] for row in rows}) == 2
    assert {row["id"] for row in rows} == {1, 2}
    for row in rows:
        assert row["ma_nhan_vien"] == f"NV-{row['id']:06d}"
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 2


# UC-04 R6: không sửa được mã hoặc id sau tạo; cập nhật hồ sơ vẫn được phép
@pytest.mark.parametrize("assignment", ["ma_nhan_vien='NV-000002'", "id=2"])
async def test_update_cannot_change_code_or_identity(database, assignment):
    await database.execute(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'employee', 'test-hash')"""
    )
    with pytest.raises(asyncpg.RaiseError, match="Không được sửa mã nhân viên") as caught:
        async with database.transaction():
            await database.execute(f'UPDATE "NhanVien" SET {assignment} WHERE id=1')
    assert caught.value.sqlstate == "P0001"
    row = await database.fetchrow('SELECT id, ma_nhan_vien FROM "NhanVien"')
    assert dict(row) == {"id": 1, "ma_nhan_vien": "NV-000001"}
    assert (
        await database.fetchval(
            """UPDATE "NhanVien" SET ho_ten='Updated profile' WHERE id=1 RETURNING ho_ten"""
        )
        == "Updated profile"
    )


# UC-04 R6: id 999999 còn hợp lệ; id 1000000 báo hết dải và không lưu mã bị lpad cắt
async def test_insert_rejects_exhausted_code_range(database):
    assert (
        await database.fetchval(
            """INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (999999, 1, 'last', 'test-hash') RETURNING ma_nhan_vien"""
        )
        == "NV-999999"
    )
    with pytest.raises(asyncpg.RaiseError, match="Hết dải mã nhân viên NV-NNNNNN") as caught:
        async with database.transaction():
            await database.execute(
                """INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau)
                   VALUES (1000000, 1, 'exhausted', 'test-hash')"""
            )
    assert caught.value.sqlstate == "P0001"
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 1
    assert await database.fetchval('SELECT ma_nhan_vien FROM "NhanVien"') == "NV-999999"


# UC-04 R6: SQL truyền mã tùy ý cũng không thay được quy tắc mã lấy từ id.
async def test_trigger_overrides_supplied_code(database):
    row = await database.fetchrow(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien)
           VALUES (1, 'supplied-code', 'test-hash', 'NV-888888') RETURNING id, ma_nhan_vien"""
    )
    assert row["ma_nhan_vien"] == f"NV-{row['id']:06d}" == "NV-000001"


# UC-04 AC-1/AC-2/AC-5, R6: API/ORM nhận mã trigger thật; tài khoản đăng nhập được đúng vai trò.
@pytest.mark.parametrize(
    "role_id,role_code", [(1, "quan_tri_vien"), (2, "quan_ly"), (3, "nhan_vien")]
)
async def test_api_returns_database_code_and_account_can_login(database, api, role_id, role_code):
    payload = {
        "ten_dang_nhap": "uc04-created",
        "mat_khau": "123456",
        "vai_tro_id": role_id,
        "ly_do": "UC-04 integration test",
    }
    response = await api.client.post("/api/v1/nhan_vien", headers=api.headers(), json=payload)
    assert response.status_code == 201, response.text
    employee = response.json()["data"]
    assert employee["ma_nhan_vien"] == f"NV-{employee['id']:06d}"
    assert employee["ma_vai_tro"] == role_code
    assert response.headers["Location"] == f"/api/v1/nhan_vien/{employee['id']}"
    detail = await api.client.get(response.headers["Location"], headers=api.headers())
    assert detail.status_code == 200
    assert detail.headers["ETag"] == response.headers["ETag"]
    audit = await database.fetchrow(
        """SELECT nhan_vien_id, doi_tuong_id, du_lieu_sau, ly_do FROM "LichSuThaoTac"
           WHERE loai_doi_tuong='nhan_vien' AND thao_tac='tao'"""
    )
    assert audit["nhan_vien_id"] == 1 and audit["doi_tuong_id"] == employee["id"]
    assert json.loads(audit["du_lieu_sau"])["ma_nhan_vien"] == employee["ma_nhan_vien"]
    assert audit["ly_do"] == payload["ly_do"]
    assert not {"mat_khau", "password_hash"}.intersection(employee)
    assert not {"mat_khau", "password_hash"}.intersection(json.loads(audit["du_lieu_sau"]))
    login = await api.client.post(
        "/api/v1/auth/dang_nhap",
        json={key: payload[key] for key in ("ten_dang_nhap", "mat_khau")},
    )
    assert login.status_code == 200
    assert login.json()["data"]["nhan_vien"]["ma_vai_tro"] == role_code


# UC-04 R6/AC-3: hai QTV, hai connection thật cùng qua precheck; mã không trùng, username vẫn unique.
@pytest.mark.parametrize(
    "same_username", [False, True], ids=["distinct-usernames", "same-username"]
)
async def test_two_administrators_create_concurrently(
    database, api, admin_hash, monkeypatch, same_username
):
    second_admin = await database.fetchval(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'uc04-admin-2', $1) RETURNING id""",
        admin_hash,
    )
    barrier = asyncio.Barrier(2)
    connections = set()
    create = SqlAlchemyNhanVienRepository.create

    async def concurrent_create(repository, employee):
        connections.add(await repository.session.scalar(text("SELECT pg_backend_pid()")))
        await barrier.wait()
        return await create(repository, employee)

    monkeypatch.setattr(SqlAlchemyNhanVienRepository, "create", concurrent_create)

    async def submit(actor_id, username):
        return await api.client.post(
            "/api/v1/nhan_vien",
            headers=api.headers(actor_id),
            json={"ten_dang_nhap": username, "mat_khau": "123456", "vai_tro_id": 3},
        )

    async with asyncio.timeout(15), asyncio.TaskGroup() as group:
        first = group.create_task(submit(1, "uc04-parallel-a"))
        second = group.create_task(
            submit(second_admin, "uc04-parallel-a" if same_username else "uc04-parallel-b")
        )
    responses = [first.result(), second.result()]
    assert len(connections) == 2
    assert sorted(response.status_code for response in responses) == (
        [201, 409] if same_username else [201, 201]
    ), [response.text for response in responses]
    created = [response.json()["data"] for response in responses if response.status_code == 201]
    assert len({record["id"] for record in created}) == len(created)
    assert len({record["ma_nhan_vien"] for record in created}) == len(created)
    assert all(record["ma_nhan_vien"] == f"NV-{record['id']:06d}" for record in created)
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 2 + len(created)
    assert await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"') == len(created)
    if same_username:
        conflict = next(response for response in responses if response.status_code == 409)
        assert conflict.json()["error"]["code"] == "ten_dang_nhap_bi_trung"


# UC-04 R6/A7: sequence thật đạt 999999 rồi hết dải -> HTTP 409, rollback và không thêm audit.
async def test_api_identity_exhaustion_rolls_back(database, api):
    await database.execute(
        """SELECT setval(pg_get_serial_sequence('"NhanVien"', 'id'), 999998, true)"""
    )
    payload = {"ten_dang_nhap": "uc04-last", "mat_khau": "123456", "vai_tro_id": 3}
    last = await api.client.post("/api/v1/nhan_vien", headers=api.headers(), json=payload)
    assert last.status_code == 201, last.text
    assert last.json()["data"]["ma_nhan_vien"] == "NV-999999"
    exhausted = await api.client.post(
        "/api/v1/nhan_vien",
        headers=api.headers(),
        json={**payload, "ten_dang_nhap": "uc04-exhausted"},
    )
    assert exhausted.status_code == 409, exhausted.text
    assert exhausted.json()["error"]["code"] == "trang_thai_khong_hop_le"
    assert exhausted.json()["error"]["message"] == "Đã hết mã nhân viên khả dụng"
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 2
    assert await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"') == 1
    assert await database.fetchval('SELECT max(id) FROM "NhanVien"') == 999999


# UC-04 AC-5/A7, R6: lỗi sau INSERT/audit/flush rollback thật; mã đã tiêu thụ không dùng lại.
@pytest.mark.parametrize("failure", ["audit", "commit"])
async def test_create_and_audit_roll_back_together(database, api, monkeypatch, failure):
    payload = {"ten_dang_nhap": "uc04-rollback", "mat_khau": "123456", "vai_tro_id": 3}
    append = AuditService.append

    async def failing_append(service, entry):
        await append(service, entry)
        raise RuntimeError("UC-04 simulated audit failure")

    async def failing_commit(session):
        await session.flush()
        raise RuntimeError("UC-04 simulated commit failure")

    with monkeypatch.context() as patch:
        if failure == "audit":
            patch.setattr(AuditService, "append", failing_append)
        else:
            patch.setattr(AsyncSession, "commit", failing_commit)
        failed = await api.client.post("/api/v1/nhan_vien", headers=api.headers(), json=payload)
    assert failed.status_code == 500
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 1
    assert await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"') == 0
    retried = await api.client.post("/api/v1/nhan_vien", headers=api.headers(), json=payload)
    assert retried.status_code == 201, retried.text
    assert retried.json()["data"]["id"] == 3
    assert retried.json()["data"]["ma_nhan_vien"] == "NV-000003"
    assert await database.fetchval('SELECT count(*) FROM "LichSuThaoTac"') == 1


# UC-04 R6: seed chỉ chạy trên DB test mới/trống; id 1..4 giữ NV-000001..000004, sequence tiếp tục 5.
async def test_fresh_bootstrap_seed_preserves_employee_codes(empty_database):
    assert await empty_database.fetchval('SELECT count(*) FROM "NhanVien"') == 0
    assert await empty_database.fetchval('SELECT count(*) FROM "VaiTro"') == 0
    await empty_database.execute((BOOTSTRAP.parent / "seed.sql").read_text(encoding="utf-8"))
    employees = await empty_database.fetch('SELECT id, ma_nhan_vien FROM "NhanVien" ORDER BY id')
    assert [(row["id"], row["ma_nhan_vien"]) for row in employees] == [
        (index, f"NV-{index:06d}") for index in range(1, 5)
    ]
    assert (
        await empty_database.fetchval(
            """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'uc04-after-seed', 'test-hash') RETURNING ma_nhan_vien"""
        )
        == "NV-000005"
    )
