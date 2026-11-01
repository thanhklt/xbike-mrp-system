"""Real PostgreSQL connections verify employee locking, atomic audit and API contracts."""

import asyncio
import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token, password_version
from app.dependencies import get_audit_service
from app.main import app
from app.modules.audit.models import LichSuThaoTac
from app.modules.nhan_vien.models import NhanVien, VaiTro
from app.modules.nhan_vien.repository import SqlAlchemyNhanVienRepository

TEST_HASH = "isolated-test-credential"


def auth(employee_id=1):
    return {
        "Authorization": f"Bearer {create_access_token(employee_id, credential_version=password_version(TEST_HASH))}"
    }


@pytest.fixture
async def postgres_employees():
    url = os.getenv("EMPLOYEE_TEST_DATABASE_URL") or os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL test database")
    assert (make_url(url).database or "").endswith("_test")
    namespace = "employee_run_" + uuid4().hex
    setup_engine = create_async_engine(url, hide_parameters=True)
    async with setup_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{namespace}"'))
    await setup_engine.dispose()
    engine = create_async_engine(
        url,
        hide_parameters=True,
        connect_args={"server_settings": {"search_path": namespace}},
    )
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda conn: Base.metadata.create_all(
                conn, tables=[VaiTro.__table__, NhanVien.__table__, LichSuThaoTac.__table__]
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                VaiTro(id=i, ma_vai_tro=role, ten_vai_tro=role)
                for i, role in enumerate(("quan_tri_vien", "quan_ly", "nhan_vien"), 1)
            ]
        )
        await session.flush()
        session.add_all(
            [
                NhanVien(
                    vai_tro_id=i,
                    ten_dang_nhap=f"test{i}",
                    mat_khau=TEST_HASH,
                    ma_nhan_vien=f"NV-{i:06d}",
                    ho_ten=f"Employee {i}",
                    trang_thai="hoat_dong",
                )
                for i in range(1, 4)
            ]
        )
        await session.commit()

    async def override_db():
        async with sessions() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client, sessions
    finally:
        app.dependency_overrides = previous
        await engine.dispose()
    # Committed concurrency fixtures remain in this unique schema of the test DB.
    # No application database or existing schema is reset or deleted.


async def conditional(client, employee_id=3):
    response = await client.get(f"/api/v1/nhan_vien/{employee_id}", headers=auth())
    assert response.status_code == 200, response.text
    return {**auth(), "If-Match": response.headers["etag"]}


def account(suffix=1, **changes):
    return {
        "ten_dang_nhap": f"created-{suffix}",
        "ma_nhan_vien": f"NV-{100 + suffix:06d}",
        "vai_tro_id": 3,
        "mat_khau": "TestPassword2026!",
        **changes,
    }


async def test_same_etag_concurrent_updates_allow_one_writer(postgres_employees):
    client, sessions = postgres_employees
    headers = await conditional(client)
    responses = await asyncio.gather(
        *[
            client.patch("/api/v1/nhan_vien/3", headers=headers, json={"ho_ten": name})
            for name in ("First", "Second")
        ]
    )
    assert sorted(result.status_code for result in responses) == [200, 412]
    winner = next(result for result in responses if result.status_code == 200)
    async with sessions() as session:
        assert (await session.get(NhanVien, 3)).ho_ten == winner.json()["data"]["ho_ten"]
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 1


async def test_admin_password_version_is_rechecked_after_waiting_for_lock(
    postgres_employees, monkeypatch
):
    client, sessions = postgres_employees
    headers = await conditional(client)
    reached_lock = asyncio.Event()
    original = SqlAlchemyNhanVienRepository.lock_credentials_by_id

    async def signal_lock(repository, employee_id):
        reached_lock.set()
        return await original(repository, employee_id)

    monkeypatch.setattr(SqlAlchemyNhanVienRepository, "lock_credentials_by_id", signal_lock)
    async with sessions() as blocker:
        await blocker.execute(select(NhanVien).where(NhanVien.id == 1).with_for_update())
        pending = asyncio.create_task(
            client.patch("/api/v1/nhan_vien/3", headers=headers, json={"ho_ten": "Stale actor"})
        )
        try:
            await asyncio.wait_for(reached_lock.wait(), timeout=5)
            await blocker.execute(
                update(NhanVien).where(NhanVien.id == 1).values(mat_khau="changed-test-hash")
            )
            await blocker.commit()
            result = await asyncio.wait_for(pending, timeout=5)
            assert result.status_code == 401
        finally:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
    async with sessions() as session:
        assert (await session.get(NhanVien, 3)).ho_ten == "Employee 3"
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


async def test_concurrent_duplicate_creation_is_conflict_and_atomic(postgres_employees):
    client, sessions = postgres_employees
    responses = await asyncio.gather(
        *[client.post("/api/v1/nhan_vien", headers=auth(), json=account()) for _ in range(2)]
    )
    assert sorted(result.status_code for result in responses) == [201, 409]
    failure = next(result for result in responses if result.status_code == 409)
    assert failure.json()["error"]["code"] == "ma_bi_trung"
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(NhanVien)) == 4
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 1


async def test_parallel_creations_have_distinct_server_ids(postgres_employees):
    client, sessions = postgres_employees
    responses = await asyncio.gather(
        *[client.post("/api/v1/nhan_vien", headers=auth(), json=account(i)) for i in (1, 2)]
    )
    assert [result.status_code for result in responses] == [201, 201]
    assert len({result.json()["data"]["id"] for result in responses}) == 2
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 2


async def test_concurrent_status_changes_write_one_audit_per_transition(postgres_employees):
    client, sessions = postgres_employees
    headers = await conditional(client)
    deletes = await asyncio.gather(
        *[
            client.request(
                "DELETE", "/api/v1/nhan_vien/3", headers=headers, json={"ly_do": "Leave"}
            )
            for _ in range(2)
        ]
    )
    assert sorted(result.status_code for result in deletes) == [204, 412]
    assert (await client.get("/api/v1/nhan_vien/3", headers=auth(3))).status_code == 403
    headers = await conditional(client)
    unlocks = await asyncio.gather(
        *[
            client.post("/api/v1/nhan_vien/3/mo_khoa", headers=headers, json={"ly_do": "Return"})
            for _ in range(2)
        ]
    )
    assert sorted(result.status_code for result in unlocks) == [200, 412]
    assert (await client.get("/api/v1/nhan_vien/3", headers=auth(3))).status_code == 200
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 2


async def test_admin_invariant_survives_parallel_requests(postgres_employees):
    client, sessions = postgres_employees
    responses = await asyncio.gather(
        client.post("/api/v1/nhan_vien", headers=auth(), json=account(vai_tro_id=1)),
        client.put(
            "/api/v1/nhan_vien/3/vai_tro", headers=await conditional(client), json={"vai_tro_id": 1}
        ),
        client.put(
            "/api/v1/nhan_vien/1/vai_tro",
            headers=await conditional(client, 1),
            json={"vai_tro_id": 3},
        ),
        client.request(
            "DELETE",
            "/api/v1/nhan_vien/1",
            headers=await conditional(client, 1),
            json={"ly_do": "Leave"},
        ),
    )
    assert [result.status_code for result in responses] == [409] * 4
    async with sessions() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(NhanVien).where(NhanVien.vai_tro_id == 1)
            )
            == 1
        )
        assert (await session.get(NhanVien, 1)).trang_thai == "hoat_dong"
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


@pytest.mark.parametrize("operation", ["create", "patch", "role", "delete", "unlock"])
async def test_audit_failure_rolls_back_every_account_mutation(postgres_employees, operation):
    client, sessions = postgres_employees
    if operation == "unlock":
        blocked = await client.request(
            "DELETE",
            "/api/v1/nhan_vien/3",
            headers=await conditional(client),
            json={"ly_do": "Leave"},
        )
        assert blocked.status_code == 204
    headers = await conditional(client)

    class UnavailableAudit:
        async def append(self, entry):
            raise RuntimeError("Audit unavailable")

    app.dependency_overrides[get_audit_service] = lambda: UnavailableAudit()
    requests = {
        "create": ("POST", "/api/v1/nhan_vien", account()),
        "patch": ("PATCH", "/api/v1/nhan_vien/3", {"ho_ten": "Do not save"}),
        "role": ("PUT", "/api/v1/nhan_vien/3/vai_tro", {"vai_tro_id": 2}),
        "delete": ("DELETE", "/api/v1/nhan_vien/3", {"ly_do": "Leave"}),
        "unlock": ("POST", "/api/v1/nhan_vien/3/mo_khoa", {"ly_do": "Return"}),
    }
    method, path, body = requests[operation]
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        await client.request(method, path, headers=headers, json=body)
    async with sessions() as session:
        employee = await session.get(NhanVien, 3)
        assert employee.ho_ten == "Employee 3" and employee.vai_tro_id == 3
        assert employee.trang_thai == ("bi_khoa" if operation == "unlock" else "hoat_dong")
        assert await session.scalar(select(func.count()).select_from(NhanVien)) == 3
        assert await session.scalar(select(func.count()).select_from(LichSuThaoTac)) == (
            1 if operation == "unlock" else 0
        )


async def test_full_account_lifecycle_against_bootstrap_schema(bootstrapped_connection):
    sessions = async_sessionmaker(
        bootstrapped_connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )

    async def override_db():
        async with sessions() as session:
            yield session

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            login = await client.post(
                "/api/v1/auth/dang_nhap",
                json={"ten_dang_nhap": "quan_tri", "mat_khau": "DemoXbike2026!"},
            )
            assert login.status_code == 200
            admin = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
            roles = await client.get("/api/v1/vai_tro", headers=admin)
            assert roles.status_code == 200
            role_ids = {role["ma_vai_tro"]: role["id"] for role in roles.json()["data"]}
            payload = account(
                ten_dang_nhap="lifecycle-" + uuid4().hex,
                ma_nhan_vien="NV-899991",
                vai_tro_id=role_ids["nhan_vien"],
                he_so_luong="2",
            )
            created = await client.post("/api/v1/nhan_vien", headers=admin, json=payload)
            assert created.status_code == 201, created.text
            path = created.headers["location"]
            employee_id = created.json()["data"]["id"]
            initial_detail = await client.get(path, headers=admin)
            assert initial_detail.headers["etag"] == created.headers["etag"]
            assert created.json()["data"]["he_so_luong"] == "2.00"
            credentials = {
                "ten_dang_nhap": payload["ten_dang_nhap"],
                "mat_khau": payload["mat_khau"],
            }
            employee_login = await client.post("/api/v1/auth/dang_nhap", json=credentials)
            assert employee_login.status_code == 200
            employee = {"Authorization": f"Bearer {employee_login.json()['data']['access_token']}"}
            listed = await client.get("/api/v1/nhan_vien?q=NV-899991", headers=admin)
            assert [row["id"] for row in listed.json()["data"]] == [employee_id]
            assert (await client.get("/api/v1/nhan_vien", headers=employee)).status_code == 403
            patched = await client.patch(
                path,
                headers={**admin, "If-Match": created.headers["etag"]},
                json={"ho_ten": "Lifecycle", "he_so_luong": "2.50", "ngay_sinh": "2000-01-01"},
            )
            assert patched.status_code == 200, patched.text
            changed = await client.put(
                path + "/vai_tro",
                headers={**admin, "If-Match": patched.headers["etag"]},
                json={"vai_tro_id": role_ids["quan_ly"]},
            )
            assert changed.status_code == 200
            assert (await client.get("/api/v1/nhan_vien", headers=employee)).status_code == 200
            deleted = await client.request(
                "DELETE",
                path,
                headers={**admin, "If-Match": changed.headers["etag"]},
                json={"ly_do": "Leave"},
            )
            assert deleted.status_code == 204
            assert (await client.get(path, headers=employee)).status_code == 403
            detail = await client.get(path, headers=admin)
            assert detail.status_code == 200 and detail.json()["data"]["trang_thai"] == "bi_khoa"
            unlocked = await client.post(
                path + "/mo_khoa",
                headers={**admin, "If-Match": detail.headers["etag"]},
                json={"ly_do": "Return"},
            )
            assert unlocked.status_code == 200
            assert (await client.get(path, headers=employee)).status_code == 200
            assert (
                await client.post("/api/v1/auth/dang_nhap", json=credentials)
            ).status_code == 200
        async with sessions() as session:
            employee_row = await session.get(NhanVien, employee_id)
            assert employee_row.trang_thai == "hoat_dong"
            assert employee_row.vai_tro_id == role_ids["quan_ly"]
            audits = (
                await session.scalars(
                    select(LichSuThaoTac)
                    .where(
                        LichSuThaoTac.loai_doi_tuong == "nhan_vien",
                        LichSuThaoTac.doi_tuong_id == employee_id,
                    )
                    .order_by(LichSuThaoTac.id)
                )
            ).all()
            assert [entry.thao_tac for entry in audits] == [
                "tao",
                "sua",
                "thu_hoi_quyen",
                "cap_quyen",
                "vo_hieu_hoa",
                "sua",
            ]
            assert all("mat_khau" not in str(entry.du_lieu_sau) for entry in audits)
    finally:
        app.dependency_overrides = previous
