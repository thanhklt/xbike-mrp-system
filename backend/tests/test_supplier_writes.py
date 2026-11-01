"""Supplier mutations against PostgreSQL, including atomicity and concurrent creation."""

import asyncio
import os
from typing import Annotated
from uuid import uuid4

import bcrypt
import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_suppliers_service
from app.main import app
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.nha_cung_cap.models import Supplier
from app.modules.nha_cung_cap.repository import SqlAlchemySupplierRepository
from app.modules.nha_cung_cap.service import SupplierService
from app.modules.nhan_vien.models import NhanVien, VaiTro
from tests.test_auth_api import PASSWORD, login
from tests.test_auth_api import auth_context as auth_context
from tests.test_suppliers_api import supplier_context as supplier_context

BASE = "/api/v1/nha_cung_cap"


@pytest.fixture
async def write_context(supplier_context):
    client, sessions, _ = supplier_context
    token = (await login(client, 2)).json()["data"]["access_token"]
    yield client, sessions, {"Authorization": f"Bearer {token}"}


async def test_create_contract_and_audit(write_context):
    client, sessions, headers = write_context
    created = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": " New supplier "}
    )
    assert created.status_code == 201
    record = created.json()["data"]
    assert record["ten_ncc"] == "New supplier"
    location = f"{BASE}/{record['id']}"
    assert created.headers["location"] == location
    assert "etag" not in created.headers
    assert created.json()["meta"]["request_id"]
    detail = await client.get(location, headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"] == record
    assert "etag" not in detail.headers
    async with sessions() as db:
        entries = (await db.scalars(select(LichSuThaoTac).order_by(LichSuThaoTac.id))).all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry.thao_tac == "tao"
        assert entry.nhan_vien_id == 2
        assert entry.loai_doi_tuong == "nha_cung_cap"
        assert entry.doi_tuong_id == record["id"]
        assert entry.du_lieu_sau == record
        assert entry.du_lieu_truoc is None
        assert await db.scalar(
            select(LichSuThaoTac.du_lieu_truoc.is_(None)).where(LichSuThaoTac.id == entry.id)
        )


@pytest.mark.parametrize("index", [1, 3])
async def test_only_manager_can_write(write_context, index):
    client, sessions, _ = write_context
    token = (await login(client, index)).json()["data"]["access_token"]
    response = await client.post(
        BASE,
        headers={"Authorization": f"Bearer {token}"},
        json={"ma_ncc": "NCC-000004", "ten_ncc": "New"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 3


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"ten_ncc": "Missing code"},
        {"ma_ncc": "NCC-000004"},
        {"ma_ncc": "bad", "ten_ncc": "New"},
        {"ma_ncc": "NCC-000000", "ten_ncc": "New"},
        {"ma_ncc": "NCC-000004", "ten_ncc": None},
        {"ma_ncc": "NCC-000004", "ten_ncc": " "},
        {"ma_ncc": "NCC-000004", "ten_ncc": "New", "id": 4},
    ],
)
async def test_create_validation(write_context, body):
    client, _, headers = write_context
    response = await client.post(BASE, headers=headers, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"


async def test_duplicate_code_is_409_and_rollback(write_context):
    client, sessions, headers = write_context
    response = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000002", "ten_ncc": "Changed"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ma_bi_trung"
    assert response.json()["error"]["message"] == "Mã nhà cung cấp đã tồn tại"
    async with sessions() as db:
        assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 3
        assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


async def test_audit_failure_rolls_back_entire_mutation(write_context):
    client, sessions, headers = write_context

    class FailingAudit:
        async def append(self, entry):
            raise RuntimeError("private audit failure")

    def failing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return SupplierService(
            SqlAlchemySupplierRepository(db), FailingAudit(), SqlAlchemyTransaction(db)
        )

    app.dependency_overrides[get_suppliers_service] = failing_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as http:
            response = await http.post(
                BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": "New"}
            )
        assert response.status_code == 500
        assert "private" not in response.text
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Supplier)) == 3
            assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
            assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0
    finally:
        app.dependency_overrides.pop(get_suppliers_service)


async def test_write_auth_and_query_errors(write_context):
    client, sessions, headers = write_context
    body = {"ma_ncc": "NCC-000004", "ten_ncc": "New"}
    assert (await client.post(BASE, json=body)).status_code == 401
    assert (await client.post(BASE + "?q=forbidden", headers=headers, json=body)).status_code == 422
    async with sessions() as db:
        await db.execute(text("UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=2"))
        await db.commit()
    assert (await client.post(BASE, headers=headers, json=body)).status_code == 403


def test_openapi_mutations():
    paths = app.openapi()["paths"]
    assert set(paths[BASE]) == {"get", "post"}
    assert set(paths[f"{BASE}/{{id}}"]) == {"get"}
    post = paths[BASE]["post"]
    assert set(post["responses"]["201"]["headers"]) == {"Location"}
    assert {"401", "403", "409", "422", "500"} <= set(post["responses"])
    assert post["security"] == [{"OAuth2PasswordBearer": []}]
    assert not any(path.startswith("/api/v1/suppliers") for path in paths)


async def test_id_exhaustion_is_conflict_without_writes(write_context):
    client, sessions, headers = write_context
    async with sessions() as db:
        db.add(Supplier(id=2**31 - 1, ma_ncc="NCC-999999", ten_ncc="Last ID"))
        await db.commit()
    response = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": "New"}
    )
    assert response.status_code == 409
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


@pytest.fixture
async def concurrent_write_context():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires dedicated PostgreSQL test database")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Concurrency tests require database name ending in _test")
    schema = "supplier_race_" + uuid4().hex
    engine = create_async_engine(
        url,
        hide_parameters=True,
        connect_args={
            "server_settings": {
                "search_path": schema,
                "lock_timeout": "10000",
                "statement_timeout": "15000",
            }
        },
    )
    async with engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.run_sync(
            lambda sync: Base.metadata.create_all(
                sync,
                tables=[
                    VaiTro.__table__,
                    NhanVien.__table__,
                    LichSuThaoTac.__table__,
                    Supplier.__table__,
                ],
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        db.add(VaiTro(id=2, ma_vai_tro="quan_ly", ten_vai_tro="Manager"))
        await db.flush()
        db.add(
            NhanVien(
                id=2,
                vai_tro_id=2,
                ten_dang_nhap="user2",
                ma_nhan_vien="NV-000002",
                trang_thai="hoat_dong",
                mat_khau=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode(),
            )
        )
        db.add(Supplier(id=1, ma_ncc="NCC-000001", ten_ncc="Initial"))
        await db.commit()

    async def independent_db():
        async with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = independent_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            token = (await login(client, 2)).json()["data"]["access_token"]
            yield client, sessions, {"Authorization": f"Bearer {token}"}
    finally:
        app.dependency_overrides.pop(get_suppliers_service, None)
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest.mark.parametrize("same_code", [False, True])
async def test_concurrent_creates_allocate_distinct_ids(concurrent_write_context, same_code):
    client, sessions, headers = concurrent_write_context
    count = 6
    barrier = asyncio.Barrier(count)

    class RacingRepository(SqlAlchemySupplierRepository):
        async def add(self, payload):
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return await super().add(payload)

    def racing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return SupplierService(
            RacingRepository(db), SqlAlchemyAuditRepository(db), SqlAlchemyTransaction(db)
        )

    app.dependency_overrides[get_suppliers_service] = racing_service
    responses = await asyncio.wait_for(
        asyncio.gather(
            *[
                client.post(
                    BASE,
                    headers=headers,
                    json={
                        "ma_ncc": f"NCC-{100 if same_code else 100 + index:06d}",
                        "ten_ncc": "Concurrent",
                    },
                )
                for index in range(count)
            ]
        ),
        timeout=20,
    )
    created = [r for r in responses if r.status_code == 201]
    assert len(created) == (1 if same_code else count)
    assert len({r.json()["data"]["id"] for r in created}) == len(created)
    for response in responses:
        if response.status_code != 201:
            assert response.status_code == 409
            assert response.json()["error"]["code"] == "ma_bi_trung"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == len(created)
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 1 + len(created)


@pytest.mark.parametrize("method", ["patch", "delete"])
async def test_removed_mutations_do_not_write(write_context, method):
    client, sessions, headers = write_context
    response = await client.request(
        method,
        f"{BASE}/1",
        headers=headers,
        **({"json": {"ten_ncc": "Changed"}} if method == "patch" else {}),
    )
    assert response.status_code == 405
    async with sessions() as db:
        assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 3
        assert await db.scalar(select(func.count()).select_from(LichSuThaoTac)) == 0


async def test_creation_does_not_reuse_historical_audit_id(write_context):
    client, sessions, headers = write_context
    historical_id = 50
    async with sessions() as db:
        db.add(
            LichSuThaoTac(
                nhan_vien_id=2,
                loai_doi_tuong="nha_cung_cap",
                doi_tuong_id=historical_id,
                thao_tac="tao",
                du_lieu_sau={"id": historical_id},
            )
        )
        await db.commit()
    response = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": "New"}
    )
    assert response.status_code == 201
    assert response.json()["data"]["id"] == historical_id + 1
