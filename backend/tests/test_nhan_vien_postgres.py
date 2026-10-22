"""PostgreSQL account concurrency checks using an isolated test database."""

import asyncio
import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.modules.audit.models import AuditTrailLog
from app.modules.nhan_vien.models import Role, User

URL = os.getenv("EMPLOYEE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="Set EMPLOYEE_TEST_DATABASE_URL to a dedicated test database"
)


async def test_same_etag_concurrent_updates_allow_one_writer_and_preserve_last_admin():
    assert URL and make_url(URL).database.startswith("xbike_employee_test_")
    from app.main import app

    namespace = "employee_run_" + uuid4().hex
    setup_engine = create_async_engine(URL, hide_parameters=True)
    async with setup_engine.begin() as connection:
        await connection.execute(text(f"CREATE SCHEMA {namespace}"))
    await setup_engine.dispose()
    engine = create_async_engine(
        URL, hide_parameters=True, connect_args={"server_settings": {"search_path": namespace}}
    )
    # Separate committed setup is required for real competing connections. This
    # dedicated test DB keeps its small fixture; no existing database is reset.
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda conn: Base.metadata.create_all(
                conn, tables=[Role.__table__, User.__table__, AuditTrailLog.__table__]
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 0
        session.add_all(
            [
                Role(id=1, ma_vai_tro="quan_tri_vien", ten_vai_tro="Admin"),
                Role(id=2, ma_vai_tro="nhan_vien", ten_vai_tro="Employee"),
            ]
        )
        session.add_all(
            [
                User(
                    id=i,
                    vai_tro_id=1,
                    ten_dang_nhap=f"test{i}",
                    mat_khau="test-only",
                    ma_nhan_vien=f"TEST{i}",
                    trang_thai="hoat_dong",
                )
                for i in (1, 2)
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
            auth = {"Authorization": f"Bearer {create_access_token(1)}"}
            detail = await client.get("/api/v1/nhan_vien/2", headers=auth)
            conditional = {**auth, "If-Match": detail.headers["etag"]}
            first, second = await asyncio.gather(
                *[
                    client.patch("/api/v1/nhan_vien/2", headers=conditional, json={"ho_ten": value})
                    for value in ("First", "Second")
                ]
            )
            assert sorted([first.status_code, second.status_code]) == [200, 412]
            # Two admins concurrently demote themselves. The common policy lock
            # must leave exactly one administrator, even though the targets differ.
            tokens = [{"Authorization": f"Bearer {create_access_token(i)}"} for i in (1, 2)]
            details = [
                await client.get(f"/api/v1/nhan_vien/{i}", headers=tokens[i - 1]) for i in (1, 2)
            ]
            results = await asyncio.gather(
                *[
                    client.put(
                        f"/api/v1/nhan_vien/{i}/vai_tro",
                        headers={**tokens[i - 1], "If-Match": details[i - 1].headers["etag"]},
                        json={"vai_tro_id": 2},
                    )
                    for i in (1, 2)
                ]
            )
            assert sorted(result.status_code for result in results) == [200, 409]
            async with sessions() as session:
                admin_id = await session.scalar(select(User.id).where(User.vai_tro_id == 1))
            creator = {"Authorization": f"Bearer {create_access_token(admin_id)}"}
            created = await asyncio.gather(
                *[
                    client.post(
                        "/api/v1/nhan_vien",
                        headers=creator,
                        json={
                            "ten_dang_nhap": f"created-{suffix}",
                            "ma_nhan_vien": f"NEW-{suffix}",
                            "vai_tro_id": 2,
                            "mat_khau": "TestPassword2026",
                        },
                    )
                    for suffix in ("a", "b")
                ]
            )
            assert [response.status_code for response in created] == [201, 201]
            assert {response.json()["data"]["id"] for response in created} == {3, 4}
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count()).select_from(User).where(User.vai_tro_id == 1)
                )
                == 1
            )
            assert await session.scalar(select(func.count()).select_from(AuditTrailLog)) == 5
    finally:
        app.dependency_overrides = previous
        await engine.dispose()
