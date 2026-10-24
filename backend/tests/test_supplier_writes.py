"""Supplier mutations against PostgreSQL, including atomicity and stale versions."""

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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_suppliers_service
from app.main import app
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.nha_cung_cap.models import Supplier
from app.modules.nha_cung_cap.repository import SqlAlchemySupplierRepository
from app.modules.nha_cung_cap.service import SupplierService
from app.modules.phieu_nhap.models import GoodsReceiptNote
from app.modules.users.models import Role, User
from tests.test_auth_api import PASSWORD, login
from tests.test_auth_api import auth_context as auth_context
from tests.test_suppliers_api import supplier_context as supplier_context

BASE = "/api/v1/nha_cung_cap"


@pytest.fixture
async def write_context(supplier_context):
    client, sessions, _ = supplier_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(lambda sync: GoodsReceiptNote.__table__.create(sync))
        await db.commit()
    token = (await login(client, 2)).json()["data"]["access_token"]
    yield client, sessions, {"Authorization": f"Bearer {token}"}


async def test_create_patch_delete_contract_and_audit(write_context):
    client, sessions, headers = write_context
    created = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": " New supplier "}
    )
    assert created.status_code == 201
    record = created.json()["data"]
    assert record["ten_ncc"] == "New supplier"
    location = f"{BASE}/{record['id']}"
    assert created.headers["location"] == location
    detail = await client.get(location, headers=headers)
    assert detail.headers["etag"] == created.headers["etag"]
    changed = await client.patch(
        location,
        headers={**headers, "If-Match": detail.headers["etag"]},
        json={"dia_chi": "  Hanoi  "},
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["dia_chi"] == "Hanoi"
    assert changed.headers["etag"] != detail.headers["etag"]
    deleted = await client.delete(
        location, headers={**headers, "If-Match": changed.headers["etag"]}
    )
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (await client.get(location, headers=headers)).status_code == 404
    async with sessions() as db:
        entries = (await db.scalars(select(AuditTrailLog).order_by(AuditTrailLog.id))).all()
        assert [entry.thao_tac for entry in entries] == ["tao", "sua", "xoa_nhap"]
        assert all(entry.nhan_vien_id == 2 for entry in entries)
        assert entries[1].du_lieu_truoc == record
        assert entries[1].du_lieu_sau == changed.json()["data"]
        assert entries[2].du_lieu_truoc == changed.json()["data"]
        assert entries[2].du_lieu_sau is None
        assert await db.scalar(
            select(AuditTrailLog.du_lieu_truoc.is_(None)).where(AuditTrailLog.id == entries[0].id)
        )
        assert await db.scalar(
            select(AuditTrailLog.du_lieu_sau.is_(None)).where(AuditTrailLog.id == entries[2].id)
        )


@pytest.mark.parametrize(
    "method,body",
    [
        ("post", {"ma_ncc": "NCC-000004", "ten_ncc": "New"}),
        ("patch", {"ten_ncc": "New"}),
        ("delete", None),
    ],
)
@pytest.mark.parametrize("index", [1, 3])
async def test_only_manager_can_write(write_context, method, body, index):
    client, sessions, _ = write_context
    token = (await login(client, index)).json()["data"]["access_token"]
    response = await client.request(
        method,
        BASE if method == "post" else f"{BASE}/1",
        headers={"Authorization": f"Bearer {token}"},
        **({"json": body} if body is not None else {}),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 3


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize(
    "version,status", [(None, 428), ('"old"', 412), ('W/"old"', 412), ("*", 412), ("", 412)]
)
async def test_if_match_required_and_exact(write_context, method, version, status):
    client, sessions, headers = write_context
    if version is not None:
        headers = {**headers, "If-Match": version}
    response = await client.request(
        method,
        f"{BASE}/1",
        headers=headers,
        **({"json": {"ten_ncc": "New"}} if method == "patch" else {}),
    )
    assert response.status_code == status
    assert response.json()["error"]["code"] == (
        "thieu_if_match" if status == 428 else "du_lieu_da_thay_doi"
    )
    async with sessions() as db:
        assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


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


@pytest.mark.parametrize(
    "body",
    [
        {"ma_ncc": None},
        {"ten_ncc": None},
        {"ten_ncc": " "},
        {"ma_ncc": "NCC-000000"},
        {"ma_ncc": 12},
        {"id": 2},
        {"is_active": False},
        {"chi_tiet": []},
    ],
)
async def test_patch_validation(write_context, body):
    client, _, headers = write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    response = await client.patch(f"{BASE}/1", headers={**headers, "If-Match": etag}, json=body)
    assert response.status_code == 422


async def test_patch_omitted_nullable_and_unchanged_fields(write_context):
    client, sessions, headers = write_context
    before = await client.get(f"{BASE}/1", headers=headers)
    same = await client.patch(
        f"{BASE}/1", headers={**headers, "If-Match": before.headers["etag"]}, json={}
    )
    assert same.status_code == 200
    assert same.headers["etag"] == before.headers["etag"]
    changed = await client.patch(
        f"{BASE}/1",
        headers={**headers, "If-Match": same.headers["etag"]},
        json={"tinh": None, "so_dien_thoai": " 0123 "},
    )
    assert changed.status_code == 200
    assert changed.json()["data"]["tinh"] is None
    assert changed.json()["data"]["phuong"] == "tay_ho"
    assert changed.json()["data"]["so_dien_thoai"] == "0123"
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


@pytest.mark.parametrize("method", ["post", "patch"])
async def test_duplicate_code_is_409_and_rollback(write_context, method):
    client, sessions, headers = write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    response = await client.request(
        method,
        BASE if method == "post" else f"{BASE}/1",
        headers={**headers, "If-Match": etag},
        json={"ma_ncc": "NCC-000002", "ten_ncc": "Changed"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ma_bi_trung"
    async with sessions() as db:
        assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 3
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


@pytest.mark.parametrize("state", ["nhap", "hoan_thanh"])
async def test_referenced_supplier_cannot_delete_or_change_code(write_context, state):
    client, sessions, headers = write_context
    async with sessions() as db:
        db.add(GoodsReceiptNote(id=1, ma_phieu_nhap="PN-202610-000001", ncc_id=1, trang_thai=state))
        await db.commit()
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    for method, body in (("patch", {"ma_ncc": "NCC-000099"}), ("delete", None)):
        response = await client.request(
            method,
            f"{BASE}/1",
            headers={**headers, "If-Match": etag},
            **({"json": body} if body else {}),
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "dang_duoc_tham_chieu"
    allowed = await client.patch(
        f"{BASE}/1",
        headers={**headers, "If-Match": etag},
        json={"ma_ncc": "NCC-000001", "ten_ncc": "Updated name"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["ma_ncc"] == "NCC-000001"


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
async def test_audit_failure_rolls_back_entire_mutation(write_context, method):
    client, sessions, headers = write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]

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
            response = await http.request(
                method,
                BASE if method == "post" else f"{BASE}/1",
                headers={**headers, "If-Match": etag},
                **(
                    {"json": {"ma_ncc": "NCC-000004", "ten_ncc": "New"}}
                    if method != "delete"
                    else {}
                ),
            )
        assert response.status_code == 500
        assert "private" not in response.text
        async with sessions() as db:
            assert await db.scalar(select(func.count()).select_from(Supplier)) == 3
            assert (await db.get(Supplier, 1)).ten_ncc == "Alpha"
            assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0
    finally:
        app.dependency_overrides.pop(get_suppliers_service)


@pytest.mark.parametrize("method", ["post", "patch", "delete"])
async def test_write_auth_and_query_errors(write_context, method):
    client, sessions, headers = write_context
    path = BASE if method == "post" else f"{BASE}/1"
    kwargs = {"json": {"ma_ncc": "NCC-000004", "ten_ncc": "New"}} if method != "delete" else {}
    assert (await client.request(method, path, **kwargs)).status_code == 401
    assert (
        await client.request(method, path + "?q=forbidden", headers=headers, **kwargs)
    ).status_code == 422
    async with sessions() as db:
        await db.execute(text("UPDATE nhan_vien SET trang_thai='bi_khoa' WHERE id=2"))
        await db.commit()
    assert (await client.request(method, path, headers=headers, **kwargs)).status_code == 403


@pytest.mark.parametrize(
    "identifier,status", [(0, 422), (-1, 422), ("abc", 422), (999, 404), (2**63, 404)]
)
@pytest.mark.parametrize("method", ["patch", "delete"])
async def test_mutation_id_errors(write_context, identifier, status, method):
    client, _, headers = write_context
    response = await client.request(
        method,
        f"{BASE}/{identifier}",
        headers={**headers, "If-Match": '"etag"'},
        **({"json": {"ten_ncc": "New"}} if method == "patch" else {}),
    )
    assert response.status_code == status


async def test_deleted_highest_id_is_not_reused(write_context):
    client, _, headers = write_context
    created = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": "First"}
    )
    old_id = created.json()["data"]["id"]
    assert (
        await client.delete(
            f"{BASE}/{old_id}", headers={**headers, "If-Match": created.headers["etag"]}
        )
    ).status_code == 204
    next_created = await client.post(
        BASE, headers=headers, json={"ma_ncc": "NCC-000005", "ten_ncc": "Next"}
    )
    assert next_created.status_code == 201
    assert next_created.json()["data"]["id"] > old_id


def test_openapi_mutations():
    paths = app.openapi()["paths"]
    post = paths[BASE]["post"]
    assert "Location" in post["responses"]["201"]["headers"]
    for method in ("patch", "delete"):
        operation = paths[f"{BASE}/{{id}}"][method]
        assert {"401", "403", "404", "409", "412", "422", "428"} <= set(operation["responses"])
        assert any(p["name"] == "if-match" for p in operation["parameters"])
        assert operation["security"] == [{"OAuth2PasswordBearer": []}]
    assert "content" not in paths[f"{BASE}/{{id}}"]["delete"]["responses"]["204"]


async def test_duplicate_if_match_headers_rejected(write_context):
    client, _, headers = write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    response = await client.patch(
        f"{BASE}/1",
        headers=[*headers.items(), ("If-Match", etag), ("If-Match", etag)],
        json={"ten_ncc": "New"},
    )
    assert response.status_code == 422


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
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


async def test_legacy_create_also_allocates_id_under_lock(write_context):
    client, sessions, headers = write_context
    response = await client.post(
        "/api/v1/suppliers", headers=headers, json={"ma_ncc": "NCC-000004", "ten_ncc": "Legacy"}
    )
    assert response.status_code == 201
    assert response.json()["id"] == 4
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


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
                    Role.__table__,
                    User.__table__,
                    AuditTrailLog.__table__,
                    Supplier.__table__,
                    GoodsReceiptNote.__table__,
                ],
            )
        )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        db.add(Role(id=2, ma_vai_tro="quan_ly", ten_vai_tro="Manager"))
        await db.flush()
        db.add(
            User(
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


@pytest.mark.parametrize("methods", [("patch", "patch"), ("patch", "delete"), ("delete", "delete")])
async def test_concurrent_mutations_use_locked_current_etag(concurrent_write_context, methods):
    client, sessions, headers = concurrent_write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    barrier = asyncio.Barrier(2)

    class RacingRepository(SqlAlchemySupplierRepository):
        async def lock_by_id(self, record_id):
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return await super().lock_by_id(record_id)

    def racing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return SupplierService(
            RacingRepository(db), SqlAlchemyAuditRepository(db), SqlAlchemyTransaction(db)
        )

    app.dependency_overrides[get_suppliers_service] = racing_service
    responses = await asyncio.wait_for(
        asyncio.gather(
            *[
                client.request(
                    method,
                    f"{BASE}/1",
                    headers={**headers, "If-Match": etag},
                    **({"json": {"ten_ncc": f"Winner {index}"}} if method == "patch" else {}),
                )
                for index, method in enumerate(methods)
            ]
        ),
        timeout=20,
    )
    app.dependency_overrides.pop(get_suppliers_service)
    statuses = sorted(r.status_code for r in responses)
    expected = (
        [[200, 412]]
        if methods == ("patch", "patch")
        else ([[204, 404]] if methods == ("delete", "delete") else [[200, 412], [204, 404]])
    )
    assert statuses in expected
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1
        record = await db.get(Supplier, 1)
        if 204 in statuses:
            assert record is None
        else:
            winner = next(r for r in responses if r.status_code == 200)
            assert record.ten_ncc == winner.json()["data"]["ten_ncc"]


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
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == len(created)
        assert await db.scalar(select(func.count()).select_from(Supplier)) == 1 + len(created)


@pytest.mark.parametrize("method", ["patch", "delete"])
async def test_reference_insert_wins_before_mutation_lock(concurrent_write_context, method):
    client, sessions, headers = concurrent_write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    request_pid = asyncio.get_running_loop().create_future()

    async def observed_db():
        async with sessions() as db:
            pid = await db.scalar(select(func.pg_backend_pid()))
            if not request_pid.done():
                request_pid.set_result(pid)
            yield db

    app.dependency_overrides[get_db] = observed_db
    async with sessions() as receipt_db:
        receipt_db.add(
            GoodsReceiptNote(id=1, ma_phieu_nhap="PN-202610-000001", ncc_id=1, trang_thai="nhap")
        )
        await receipt_db.flush()
        task = asyncio.create_task(
            client.request(
                method,
                f"{BASE}/1",
                headers={**headers, "If-Match": etag},
                **({"json": {"ma_ncc": "NCC-000099"}} if method == "patch" else {}),
            )
        )
        try:
            pid = await asyncio.wait_for(request_pid, 5)
            async with sessions() as observer:
                async with asyncio.timeout(5):
                    while not await observer.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                    ):
                        assert not task.done()
                        await asyncio.sleep(0.02)
            await receipt_db.commit()
            response = await asyncio.wait_for(task, 10)
            assert response.status_code == 409
            assert response.json()["error"]["code"] == "dang_duoc_tham_chieu"
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    async with sessions() as db:
        assert (await db.get(Supplier, 1)).ma_ncc == "NCC-000001"
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 0


async def test_delete_wins_before_concurrent_reference_insert(concurrent_write_context):
    client, sessions, headers = concurrent_write_context
    etag = (await client.get(f"{BASE}/1", headers=headers)).headers["etag"]
    deleted = asyncio.Event()
    allow_commit = asyncio.Event()

    class PausedAudit(SqlAlchemyAuditRepository):
        async def append(self, entry):
            await super().append(entry)
            deleted.set()
            await asyncio.wait_for(allow_commit.wait(), 10)

    def paused_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return SupplierService(
            SqlAlchemySupplierRepository(db), PausedAudit(db), SqlAlchemyTransaction(db)
        )

    app.dependency_overrides[get_suppliers_service] = paused_service
    delete_task = asyncio.create_task(
        client.delete(f"{BASE}/1", headers={**headers, "If-Match": etag})
    )
    insert_task = None
    try:
        await asyncio.wait_for(deleted.wait(), 5)
        async with sessions() as receipt_db:
            pid = await receipt_db.scalar(select(func.pg_backend_pid()))
            receipt_db.add(
                GoodsReceiptNote(
                    id=1, ma_phieu_nhap="PN-202610-000001", ncc_id=1, trang_thai="nhap"
                )
            )
            insert_task = asyncio.create_task(receipt_db.flush())
            async with sessions() as observer:
                async with asyncio.timeout(5):
                    while not await observer.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                    ):
                        assert not insert_task.done()
                        await asyncio.sleep(0.02)
            allow_commit.set()
            assert (await asyncio.wait_for(delete_task, 10)).status_code == 204
            with pytest.raises(IntegrityError) as failure:
                await asyncio.wait_for(insert_task, 10)
            assert failure.value.orig.sqlstate == "23503"
            await receipt_db.rollback()
        async with sessions() as db:
            assert await db.get(Supplier, 1) is None
            assert await db.scalar(select(func.count()).select_from(GoodsReceiptNote)) == 0
            assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1
    finally:
        allow_commit.set()
        pending = [task for task in (delete_task, insert_task) if task is not None]
        for task in pending:
            if not task.done():
                task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
