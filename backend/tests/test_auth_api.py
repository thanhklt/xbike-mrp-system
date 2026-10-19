"""HTTP auth contracts against a dedicated PostgreSQL database, rolled back per test."""

import asyncio
import os
from datetime import timedelta
from typing import Annotated
from uuid import uuid4

import bcrypt
import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_auth_service
from app.main import app
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.auth.repository import SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService
from app.modules.users.models import Role, User

PASSWORD = "MatKhauCu-123"
NEW_PASSWORD = "Mật khẩu mới-456"
BASE = "/api/v1/auth"


@pytest.fixture
async def auth_context():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL must point to a dedicated PostgreSQL test database")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Auth tests require a database name ending in _test")
    engine = create_async_engine(url, hide_parameters=True)
    async with engine.connect() as connection:
        outer = await connection.begin()
        schema = "auth_api_" + uuid4().hex
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        await connection.run_sync(
            lambda sync: Base.metadata.create_all(
                sync, tables=[Role.__table__, User.__table__, AuditTrailLog.__table__]
            )
        )
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with sessions() as db:
            for index, role in enumerate(("quan_tri_vien", "quan_ly", "nhan_vien"), 1):
                db.add(Role(id=index, ma_vai_tro=role, ten_vai_tro=role))
            await db.flush()
            hashed = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
            for index in range(1, 4):
                db.add(
                    User(
                        id=index,
                        vai_tro_id=index,
                        ten_dang_nhap=f"user{index}",
                        mat_khau=hashed,
                        ma_nhan_vien=f"NV-{index:06d}",
                        ho_ten=f"Nhân viên {index}",
                        email=f"user{index}@example.test",
                        trang_thai="hoat_dong",
                    )
                )
            await db.commit()

        async def test_db():
            async with sessions() as db:
                yield db

        app.dependency_overrides[get_db] = test_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, sessions
        finally:
            app.dependency_overrides.pop(get_db, None)
            await outer.rollback()
    await engine.dispose()


async def login(client, index=1, password=PASSWORD):
    return await client.post(
        f"{BASE}/dang_nhap",
        json={
            "ten_dang_nhap": f"user{index}",
            "mat_khau": password,
        },
    )


@pytest.mark.parametrize("index", [1, 2, 3])
async def test_login_and_own_profile_for_each_role(auth_context, index):
    client, _ = auth_context
    response = await login(client, index)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    assert data["nhan_vien"]["id"] == index
    assert response.json()["meta"]["request_id"]
    assert response.headers["cache-control"] == "no-store"
    profile = await client.get(
        f"{BASE}/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert profile.status_code == 200
    assert profile.json()["data"] == data["nhan_vien"]
    assert profile.headers["etag"].startswith('"')
    assert profile.json()["meta"]["request_id"] != response.json()["meta"]["request_id"]
    for secret in ("mat_khau", "password_hash", "tai_khoan_id", "loai_nhan_vien", "access_token"):
        assert secret not in profile.json()["data"]


async def test_password_change_revokes_all_old_tokens_and_writes_safe_audit(auth_context):
    client, sessions = auth_context
    tokens = [(await login(client)).json()["data"]["access_token"] for _ in range(2)]
    headers = {"Authorization": f"Bearer {tokens[0]}"}
    response = await client.post(
        f"{BASE}/doi_mat_khau",
        headers=headers,
        json={
            "mat_khau_hien_tai": PASSWORD,
            "mat_khau_moi": NEW_PASSWORD,
        },
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"da_doi": True}
    for token in tokens:
        assert (
            await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 401
        assert (
            await client.get("/api/v1/nhan_vien", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 401
    assert (await login(client)).status_code == 401
    assert (await login(client, password=NEW_PASSWORD)).status_code == 200
    async with sessions() as db:
        user = await db.get(User, 1)
        assert user.mat_khau.startswith("$argon2id$")
        assert (await db.get(User, 2)).mat_khau.startswith("$2")
        audit = (await db.scalars(select(AuditTrailLog))).one()
        assert audit.nhan_vien_id == audit.doi_tuong_id == 1
        assert audit.thao_tac == "sua"
        assert audit.du_lieu_sau == {"da_doi_mat_khau": True}
        assert PASSWORD not in str(audit.du_lieu_sau)
        assert NEW_PASSWORD not in str(audit.du_lieu_sau)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"ten_dang_nhap": "user1"},
        {"ten_dang_nhap": "user1", "mat_khau": None},
        {"ten_dang_nhap": " ", "mat_khau": PASSWORD},
        {"ten_dang_nhap": "user1", "mat_khau": PASSWORD, "vai_tro_id": 1},
    ],
)
async def test_login_validation_never_echoes_password(auth_context, body):
    client, _ = auth_context
    response = await client.post(f"{BASE}/dang_nhap", json=body)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert response.json()["meta"]["request_id"]


async def test_invalid_credentials_and_missing_token(auth_context):
    client, _ = auth_context
    bad = await login(client, password="incorrect")
    missing = await login(client, index=999)
    assert bad.status_code == missing.status_code == 401
    assert bad.json()["error"] == missing.json()["error"]
    response = await client.get(f"{BASE}/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_lock_is_checked_on_login_and_each_request(auth_context):
    client, sessions = auth_context
    token = (await login(client)).json()["data"]["access_token"]
    async with sessions() as db:
        await db.execute(text("UPDATE nhan_vien SET trang_thai='bi_khoa' WHERE id=1"))
        await db.commit()
    assert (await login(client)).status_code == 403
    assert (
        await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 403


@pytest.mark.parametrize("token", ["invalid", "", "a.b.c"])
async def test_malformed_token(auth_context, token):
    client, _ = auth_context
    response = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_expired_token(auth_context):
    client, _ = auth_context
    token = create_access_token(1, expires_delta=timedelta(seconds=-10))
    response = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": "short"},
        {"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": None},
        {"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": "x" * 1025},
        {"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD, "id": 2},
    ],
)
async def test_change_validation_keeps_credentials_unchanged(auth_context, body):
    client, sessions = auth_context
    token = (await login(client)).json()["data"]["access_token"]
    response = await client.post(
        f"{BASE}/doi_mat_khau", json=body, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 422
    assert PASSWORD not in response.text and NEW_PASSWORD not in response.text
    assert (await login(client)).status_code == 200
    async with sessions() as db:
        assert (await db.scalars(select(AuditTrailLog))).all() == []


async def test_wrong_current_password_rolls_back(auth_context):
    client, sessions = auth_context
    token = (await login(client)).json()["data"]["access_token"]
    response = await client.post(
        f"{BASE}/doi_mat_khau",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mat_khau_hien_tai": "not-the-current-password",
            "mat_khau_moi": NEW_PASSWORD,
        },
    )
    assert response.status_code == 401
    assert (await login(client)).status_code == 200
    assert (await login(client, password=NEW_PASSWORD)).status_code == 401
    async with sessions() as db:
        assert (await db.scalars(select(AuditTrailLog))).all() == []


async def test_legacy_login_endpoints_issue_revocable_tokens(auth_context):
    client, _ = auth_context
    json_login = await client.post(
        f"{BASE}/login", json={"email": "user1@example.test", "password": PASSWORD}
    )
    form_login = await client.post(
        f"{BASE}/token", data={"username": "user1", "password": PASSWORD}
    )
    for response in (json_login, form_login):
        assert response.status_code == 200
        assert "data" not in response.json()
        token = response.json()["access_token"]
        assert (
            await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
        ).status_code == 200


async def test_roles_are_read_from_database_and_query_cannot_select_another_user(auth_context):
    client, sessions = auth_context
    token = (await login(client)).json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    async with sessions() as db:
        await db.execute(text("UPDATE nhan_vien SET vai_tro_id=3 WHERE id=1"))
        await db.commit()
    response = await client.get(f"{BASE}/me", headers=headers)
    assert response.json()["data"]["ma_vai_tro"] == "nhan_vien"
    assert (await client.get("/api/v1/nhan_vien", headers=headers)).status_code == 403
    assert (await client.get(f"{BASE}/me?id=2", headers=headers)).status_code == 422


async def test_missing_account_and_legacy_unversioned_token_are_rejected(auth_context):
    client, sessions = auth_context
    token = (await login(client, index=3)).json()["data"]["access_token"]
    legacy = create_access_token(3)
    assert (
        await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {legacy}"})
    ).status_code == 401
    async with sessions() as db:
        await db.execute(text("DELETE FROM nhan_vien WHERE id=3"))
        await db.commit()
    assert (
        await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401


def test_openapi_has_concrete_auth_contracts():
    schema = app.openapi()
    for path, method, response_model in (
        ("dang_nhap", "post", "LoginResponse"),
        ("me", "get", "MeResponse"),
        ("doi_mat_khau", "post", "PasswordChangeResponse"),
    ):
        operation = schema["paths"][f"{BASE}/{path}"][method]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith(response_model)
        assert "422" in operation["responses"]
    assert "security" not in schema["paths"][f"{BASE}/dang_nhap"]["post"]
    assert schema["paths"][f"{BASE}/me"]["get"]["security"]


async def test_audit_failure_rolls_back_password_and_returns_safe_error(auth_context):
    client, sessions = auth_context
    token = (await login(client)).json()["data"]["access_token"]

    class FailingAudit:
        async def append(self, entry):
            raise RuntimeError("private database details must not reach the response")

    def service_with_failing_audit(db: Annotated[object, Depends(get_db)]):
        return AuthService(SqlAlchemyAuthRepository(db), FailingAudit(), SqlAlchemyTransaction(db))

    app.dependency_overrides[get_auth_service] = service_with_failing_audit
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as errors_client:
            response = await errors_client.post(
                f"{BASE}/doi_mat_khau",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "mat_khau_hien_tai": PASSWORD,
                    "mat_khau_moi": NEW_PASSWORD,
                },
            )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "loi_noi_bo"
        assert "private database" not in response.text
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
    assert (await login(client)).status_code == 200
    assert (await login(client, password=NEW_PASSWORD)).status_code == 401
    assert (
        await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 200
    async with sessions() as db:
        assert (await db.scalars(select(AuditTrailLog))).all() == []


@pytest.mark.parametrize("path,method", [("me", "get"), ("doi_mat_khau", "post")])
async def test_authentication_required(auth_context, path, method):
    client, _ = auth_context
    kwargs = (
        {}
        if method == "get"
        else {"json": {"mat_khau_hien_tai": PASSWORD, "mat_khau_moi": NEW_PASSWORD}}
    )
    response = await client.request(method, f"{BASE}/{path}", **kwargs)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "chua_xac_thuc"


async def test_password_unicode_longer_than_bcrypt_limit_is_preserved(auth_context):
    client, _ = auth_context
    token = (await login(client)).json()["data"]["access_token"]
    password = "  " + "đạp" * 30 + "  "
    response = await client.post(
        f"{BASE}/doi_mat_khau",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mat_khau_hien_tai": PASSWORD,
            "mat_khau_moi": password,
        },
    )
    assert response.status_code == 200
    assert (await login(client, password=password)).status_code == 200
    assert (await login(client, password=password.strip())).status_code == 401


async def test_simultaneous_changes_only_one_commits():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL test database")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Concurrency tests require a database name ending in _test")
    # Independent commits are necessary to test PostgreSQL row locks. All data
    # stays in a unique schema of the disposable test DB; no application tables.
    schema = "auth_concurrency_" + uuid4().hex
    engine = create_async_engine(
        url, hide_parameters=True, execution_options={"schema_translate_map": {None: schema}}
    )
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.run_sync(
            lambda sync: Base.metadata.create_all(
                sync, tables=[Role.__table__, User.__table__, AuditTrailLog.__table__]
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        db.add(Role(id=101, ma_vai_tro="nhan_vien", ten_vai_tro="Nhân viên"))
        await db.flush()
        db.add(
            User(
                id=101,
                vai_tro_id=101,
                ten_dang_nhap="user101",
                ma_nhan_vien="NV-000101",
                trang_thai="hoat_dong",
                mat_khau=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode(),
            )
        )
        await db.commit()

    async def independent_db():
        async with sessions() as db:
            yield db

    barrier = asyncio.Barrier(2)

    class ConcurrentAuthService(AuthService):
        async def current_payload(self, token):
            payload = await super().current_payload(token)
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return payload

    def concurrent_service(db: Annotated[object, Depends(get_db)]):
        return ConcurrentAuthService(
            SqlAlchemyAuthRepository(db), SqlAlchemyAuditRepository(db), SqlAlchemyTransaction(db)
        )

    app.dependency_overrides[get_db] = independent_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = (await login(client, index=101)).json()["data"]["access_token"]
            app.dependency_overrides[get_auth_service] = concurrent_service
            responses = await asyncio.wait_for(
                asyncio.gather(
                    *[
                        client.post(
                            f"{BASE}/doi_mat_khau",
                            headers={"Authorization": f"Bearer {token}"},
                            json={
                                "mat_khau_hien_tai": PASSWORD,
                                "mat_khau_moi": NEW_PASSWORD + str(index),
                            },
                        )
                        for index in range(2)
                    ]
                ),
                timeout=20,
            )
            app.dependency_overrides.pop(get_auth_service, None)
            assert sorted(response.status_code for response in responses) == [200, 401]
            winner = next(
                index for index, response in enumerate(responses) if response.status_code == 200
            )
            assert (await login(client, 101, NEW_PASSWORD + str(winner))).status_code == 200
            assert (await login(client, 101, NEW_PASSWORD + str(1 - winner))).status_code == 401
        async with sessions() as db:
            assert len((await db.scalars(select(AuditTrailLog))).all()) == 1
    finally:
        app.dependency_overrides.pop(get_auth_service, None)
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()
