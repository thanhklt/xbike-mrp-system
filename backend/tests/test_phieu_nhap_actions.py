"""Receipt mutations and stock posting against isolated PostgreSQL transactions."""

import asyncio
from typing import Annotated

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import await_only

from app.core.database import Base, get_db
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_receiving_service
from app.main import app
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.catalog.models import Part
from app.modules.inventory.models import StockLevel, StockMovement
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.phieu_nhap.models import GoodsReceiptNote, ReceiptItem
from app.modules.phieu_nhap.repository import SqlAlchemyReceivingRepository
from app.modules.phieu_nhap.service import ReceivingService
from app.modules.users.models import User
from tests.test_auth_api import auth_context as auth_context
from tests.test_auth_api import login
from tests.test_phieu_nhap_api import BASE, BODY
from tests.test_phieu_nhap_api import concurrent_receipt_context as concurrent_receipt_context
from tests.test_phieu_nhap_api import receipt_context as receipt_context
from tests.test_supplier_writes import concurrent_write_context as concurrent_write_context


@pytest.fixture
async def action_context(receipt_context):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync))
        await db.commit()
    created = await client.post(BASE, headers=headers, json=BODY)
    assert created.status_code == 201, created.text
    yield client, sessions, headers, created.json()["data"], created.headers["etag"]


async def test_patch_replaces_items_and_delete_preserves_audit(action_context):
    client, sessions, headers, before, etag = action_context
    path = f"{BASE}/{before['id']}"
    patched = await client.patch(
        path,
        headers={**headers, "If-Match": etag},
        json={"ncc_id": None, "chi_tiet": [{"mat_hang_id": 2, "so_luong": 4, "don_gia_thuc": 10}]},
    )
    assert patched.status_code == 200, patched.text
    after = patched.json()["data"]
    assert after["ncc_id"] is None
    assert after["tong_tien"] == 40
    assert after["ma_phieu_nhap"] == before["ma_phieu_nhap"]
    assert after["chi_tiet"][0]["id"] > before["chi_tiet"][0]["id"]
    deleted = await client.delete(path, headers={**headers, "If-Match": patched.headers["etag"]})
    assert deleted.status_code == 204 and not deleted.content
    assert (await client.get(path, headers=headers)).status_code == 404
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(ReceiptItem)) == 0
        audits = (await db.scalars(select(AuditTrailLog).order_by(AuditTrailLog.id))).all()
        assert [a.thao_tac for a in audits] == ["tao", "sua", "xoa_nhap"]
        assert audits[1].du_lieu_truoc == before
        assert audits[1].du_lieu_sau == audits[2].du_lieu_truoc == after
        assert audits[2].du_lieu_sau is None
        assert await db.scalar(select(func.count()).select_from(StockLevel)) == 0
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == 0


async def test_complete_posts_once_and_returns_existing_result_on_retry(action_context):
    client, sessions, headers, before, etag = action_context
    path = f"{BASE}/{before['id']}"
    completed = await client.post(
        f"{path}/hoan_tat", headers={**headers, "If-Match": etag}, json={}
    )
    assert completed.status_code == 200, completed.text
    record = completed.json()["data"]
    assert record["trang_thai"] == "hoan_thanh"
    assert record["da_ghi_so_truoc_do"] is False
    assert len(record["giao_dich_kho_ids"]) == 1
    retry = await client.post(f"{path}/hoan_tat", headers={**headers, "If-Match": etag}, json={})
    assert retry.status_code == 200
    assert retry.json()["data"] == {**record, "da_ghi_so_truoc_do": True}
    assert retry.headers["etag"] == completed.headers["etag"]
    detail = await client.get(path, headers=headers)
    assert detail.headers["etag"] == completed.headers["etag"]
    for method in ("patch", "delete"):
        result = await client.request(
            method,
            path,
            headers={**headers, "If-Match": completed.headers["etag"]},
            **({"json": {}} if method == "patch" else {}),
        )
        assert result.status_code == 409
    async with sessions() as db:
        stock = (await db.scalars(select(StockLevel))).one()
        movement = (await db.scalars(select(StockMovement))).one()
        assert stock.so_luong == movement.so_luong_bien_dong == 3
        assert movement.chi_tiet_phieu_nhap_id == before["chi_tiet"][0]["id"]
        assert movement.loai_giao_dich == "nhap_vat_tu"
        assert movement.nhan_vien_id == 2
        assert (
            movement.chi_tiet_phieu_xuat_id
            is movement.chung_tu_hoan_thanh_sx_id
            is movement.chi_tiet_phieu_dieu_chinh_id
            is None
        )
        assert (await db.scalars(select(GoodsReceiptNote.trang_thai))).one() == "hoan_thanh"
        audits = (await db.scalars(select(AuditTrailLog).order_by(AuditTrailLog.id))).all()
        assert [a.thao_tac for a in audits] == ["tao", "hoan_tat"]


@pytest.mark.parametrize("method,suffix", [("patch", ""), ("delete", ""), ("post", "/hoan_tat")])
@pytest.mark.parametrize(
    "if_match,status", [(None, 428), ('"stale"', 412), ("*", 412), ('W/"weak"', 412)]
)
async def test_preconditions(action_context, method, suffix, if_match, status):
    client, _, headers, record, _ = action_context
    if if_match is not None:
        headers = {**headers, "If-Match": if_match}
    response = await client.request(
        method,
        f"{BASE}/{record['id']}{suffix}",
        headers=headers,
        **({"json": {}} if method != "delete" else {}),
    )
    assert response.status_code == status, response.text


@pytest.mark.parametrize("role", [1, 3])
@pytest.mark.parametrize("method,suffix", [("patch", ""), ("delete", ""), ("post", "/hoan_tat")])
async def test_actions_are_manager_only(action_context, role, method, suffix):
    client, _, _, record, etag = action_context
    token = (await login(client, role)).json()["data"]["access_token"]
    result = await client.request(
        method,
        f"{BASE}/{record['id']}{suffix}",
        headers={"Authorization": f"Bearer {token}", "If-Match": etag},
        **({"json": {}} if method != "delete" else {}),
    )
    assert result.status_code == 403


def test_openapi_actions():
    paths = app.openapi()["paths"]
    patch_schema = app.openapi()["components"]["schemas"]["PhieuNhapPatch"]
    assert patch_schema["properties"]["chi_tiet"]["type"] == "array"
    assert patch_schema["properties"]["chi_tiet"]["minItems"] == 1
    assert "chi_tiet" not in patch_schema.get("required", [])
    for method, suffix, status in (
        ("patch", "", "200"),
        ("delete", "", "204"),
        ("post", "/hoan_tat", "200"),
    ):
        operation = paths[f"{BASE}/{{id}}{suffix}"][method]
        assert {status, "401", "403", "404", "409", "412", "422", "428", "500"} <= operation[
            "responses"
        ].keys()
        assert any(p["name"] == "if-match" for p in operation["parameters"])
        assert operation["security"]


@pytest.mark.parametrize(
    "body",
    [
        {"chi_tiet": None},
        {"chi_tiet": []},
        {"chi_tiet": BODY["chi_tiet"] * 2},
        {"tong_tien": 1},
        {"trang_thai": "hoan_thanh"},
        {"ma_phieu_nhap": "PN-202610-000001"},
        {"nhan_vien_id": 1},
        {"ncc_id": -1},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 1.5, "don_gia_thuc": 0}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 2, "don_gia_thuc": 2147483647}]},
    ],
)
async def test_patch_validation(action_context, body):
    client, _, headers, record, etag = action_context
    result = await client.patch(
        f"{BASE}/{record['id']}", headers={**headers, "If-Match": etag}, json=body
    )
    assert result.status_code == 422


@pytest.mark.parametrize("body", [None, [], {"force": True}])
async def test_complete_requires_empty_json_object(action_context, body):
    client, _, headers, record, etag = action_context
    result = await client.post(
        f"{BASE}/{record['id']}/hoan_tat", headers={**headers, "If-Match": etag}, json=body
    )
    assert result.status_code == 422


async def test_noop_patch_preserves_etag_ids_and_audit(action_context):
    client, sessions, headers, record, etag = action_context
    for body in ({}, BODY, {"ncc_id": 1}):
        response = await client.patch(
            f"{BASE}/{record['id']}", headers={**headers, "If-Match": etag}, json=body
        )
        assert response.status_code == 200
        assert response.json()["data"] == record
        assert response.headers["etag"] == etag
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


@pytest.mark.parametrize("method,suffix", [("patch", ""), ("delete", ""), ("post", "/hoan_tat")])
async def test_action_auth_queries_and_duplicate_headers(action_context, method, suffix):
    client, sessions, headers, record, etag = action_context
    path = f"{BASE}/{record['id']}{suffix}"
    options = {"json": {}} if method != "delete" else {}
    assert (await client.request(method, path, **options)).status_code == 401
    assert (
        await client.request(
            method, path + "?x=1", headers={**headers, "If-Match": etag}, **options
        )
    ).status_code == 422
    duplicate = list(headers.items()) + [("If-Match", etag), ("If-Match", etag)]
    assert (await client.request(method, path, headers=duplicate, **options)).status_code == 422
    async with sessions() as db:
        await db.execute(update(User).where(User.id == 2).values(trang_thai="bi_khoa"))
        await db.commit()
    assert (
        await client.request(method, path, headers={**headers, "If-Match": etag}, **options)
    ).status_code == 403


@pytest.mark.parametrize("method,suffix", [("patch", ""), ("delete", ""), ("post", "/hoan_tat")])
@pytest.mark.parametrize("record_id,status", [(0, 422), ("bad", 422), (999, 404), (10**30, 404)])
async def test_action_ids(action_context, method, suffix, record_id, status):
    client, _, headers, _, etag = action_context
    response = await client.request(
        method,
        f"{BASE}/{record_id}{suffix}",
        headers={**headers, "If-Match": etag},
        **({"json": {}} if method != "delete" else {}),
    )
    assert response.status_code == status


@pytest.mark.parametrize(
    "problem", ["null_price", "wrong_total", "inactive", "wrong_type", "empty"]
)
async def test_complete_rechecks_persisted_draft(action_context, problem):
    client, sessions, headers, record, _ = action_context
    async with sessions() as db:
        if problem == "null_price":
            await db.execute(update(ReceiptItem).values(don_gia_thuc=None))
        elif problem == "wrong_total":
            await db.execute(update(GoodsReceiptNote).values(tong_tien=1))
        elif problem == "inactive":
            await db.execute(update(Part).where(Part.id == 1).values(is_active=False))
        elif problem == "wrong_type":
            await db.execute(update(Part).where(Part.id == 1).values(loai_mat_hang="thanh_pham"))
        else:
            await db.execute(text("DELETE FROM chi_tiet_phieu_nhap"))
        await db.commit()
    path = f"{BASE}/{record['id']}"
    etag = (await client.get(path, headers=headers)).headers["etag"]
    response = await client.post(path + "/hoan_tat", headers={**headers, "If-Match": etag}, json={})
    assert response.status_code == 409
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == 0
        assert await db.scalar(select(func.count()).select_from(StockLevel)) == 0
        assert await db.scalar(select(GoodsReceiptNote.trang_thai)) == "nhap"


@pytest.mark.parametrize("method,suffix", [("patch", ""), ("delete", ""), ("post", "/hoan_tat")])
async def test_draft_with_ledger_reference_cannot_mutate(action_context, method, suffix):
    client, sessions, headers, record, etag = action_context
    async with sessions() as db:
        db.add(
            StockMovement(
                mat_hang_id=1,
                loai_giao_dich="nhap_vat_tu",
                so_luong_bien_dong=3,
                chi_tiet_phieu_nhap_id=record["chi_tiet"][0]["id"],
                nhan_vien_id=2,
            )
        )
        await db.commit()
    response = await client.request(
        method,
        f"{BASE}/{record['id']}{suffix}",
        headers={**headers, "If-Match": etag},
        **({"json": {}} if method != "delete" else {}),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "dang_duoc_tham_chieu"


@pytest.mark.parametrize("phase", ["balance", "ledger", "status", "audit"])
async def test_completion_failure_rolls_back_every_write(action_context, phase):
    client, sessions, headers, record, etag = action_context
    patch = await client.patch(
        f"{BASE}/{record['id']}",
        headers={**headers, "If-Match": etag},
        json={
            "chi_tiet": [BODY["chi_tiet"][0], {"mat_hang_id": 2, "so_luong": 5, "don_gia_thuc": 2}]
        },
    )
    assert patch.status_code == 200
    etag = patch.headers["etag"]

    class FailingInventory(SqlAlchemyInventoryRepository):
        async def receive_receipt(self, *args):
            result = await super().receive_receipt(*args)
            if phase == "ledger":
                raise RuntimeError("private ledger failure")
            return result

    class FailingRepository(SqlAlchemyReceivingRepository):
        async def mark_completed(self, record_id):
            result = await super().mark_completed(record_id)
            if phase == "status":
                raise RuntimeError("private status failure")
            return result

    class FailingAudit(SqlAlchemyAuditRepository):
        async def append(self, entry):
            await super().append(entry)
            await self.session.flush()
            if phase == "audit":
                raise RuntimeError("private audit failure")

    def failing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            FailingRepository(db), FailingAudit(db), SqlAlchemyTransaction(db), FailingInventory(db)
        )

    async with sessions() as db:
        engine = (await db.connection()).engine.sync_engine

    def fail_ledger_insert(conn, cursor, statement, parameters, context, many):
        if phase == "balance" and statement.lstrip().upper().startswith(
            "INSERT INTO GIAO_DICH_KHO"
        ):
            raise RuntimeError("private failure after balance flush")

    event.listen(engine, "before_cursor_execute", fail_ledger_insert)
    app.dependency_overrides[get_receiving_service] = failing_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as http:
            response = await http.post(
                f"{BASE}/{record['id']}/hoan_tat", headers={**headers, "If-Match": etag}, json={}
            )
        assert response.status_code == 500
        assert "private" not in response.text
    finally:
        event.remove(engine, "before_cursor_execute", fail_ledger_insert)
        app.dependency_overrides.pop(get_receiving_service, None)
    async with sessions() as db:
        assert await db.scalar(select(GoodsReceiptNote.trang_thai)) == "nhap"
        assert await db.scalar(select(func.count()).select_from(StockLevel)) == 0
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == 0
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 2
    retry = await client.post(
        f"{BASE}/{record['id']}/hoan_tat", headers={**headers, "If-Match": etag}, json={}
    )
    assert retry.status_code == 200 and not retry.json()["data"]["da_ghi_so_truoc_do"]


@pytest.mark.parametrize(
    "methods",
    [
        ("patch", "patch"),
        ("patch", "delete"),
        ("delete", "delete"),
        ("complete", "complete"),
        ("complete", "patch"),
        ("complete", "delete"),
    ],
)
async def test_concurrent_actions_use_locked_version(concurrent_receipt_context, methods):
    client, sessions, headers = concurrent_receipt_context
    created = await client.post(BASE, headers=headers, json=BODY)
    path = created.headers["location"]
    etag = created.headers["etag"]
    barrier = asyncio.Barrier(2)

    class RacingRepository(SqlAlchemyReceivingRepository):
        async def lock_receipt(self, record_id):
            await asyncio.wait_for(barrier.wait(), 5)
            return await super().lock_receipt(record_id)

    def racing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            RacingRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyTransaction(db),
            SqlAlchemyInventoryRepository(db),
        )

    async def request(method):
        if method == "complete":
            return await client.post(
                path + "/hoan_tat", headers={**headers, "If-Match": etag}, json={}
            )
        if method == "patch":
            return await client.patch(
                path, headers={**headers, "If-Match": etag}, json={"ncc_id": None}
            )
        return await client.delete(path, headers={**headers, "If-Match": etag})

    app.dependency_overrides[get_receiving_service] = racing_service
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(request(method) for method in methods)), 15
        )
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
    codes = sorted(r.status_code for r in results)
    if methods == ("complete", "complete"):
        assert codes == [200, 200]
        assert sorted(r.json()["data"]["da_ghi_so_truoc_do"] for r in results) == [False, True]
    else:
        assert codes in ([200, 412], [204, 404])
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 2
        posted = any(
            r.status_code == 200 and r.json()["data"].get("da_ghi_so_truoc_do") is False
            for r in results
        )
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == int(posted)
        assert (await db.scalar(select(func.sum(StockLevel.so_luong))) or 0) == (3 if posted else 0)


async def test_distinct_receipts_concurrently_add_to_same_stock(concurrent_receipt_context):
    client, sessions, headers = concurrent_receipt_context
    receipts = [await client.post(BASE, headers=headers, json=BODY) for _ in range(6)]
    barrier = asyncio.Barrier(6)

    class RacingInventory(SqlAlchemyInventoryRepository):
        async def receive_receipt(self, *args):
            await asyncio.wait_for(barrier.wait(), 5)
            return await super().receive_receipt(*args)

    def racing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            SqlAlchemyReceivingRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyTransaction(db),
            RacingInventory(db),
        )

    app.dependency_overrides[get_receiving_service] = racing_service
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *(
                    client.post(
                        r.headers["location"] + "/hoan_tat",
                        headers={**headers, "If-Match": r.headers["etag"]},
                        json={},
                    )
                    for r in receipts
                )
            ),
            15,
        )
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
    assert [r.status_code for r in results] == [200] * 6
    async with sessions() as db:
        assert (await db.scalars(select(StockLevel.so_luong))).one() == 18
        assert await db.scalar(select(func.sum(StockMovement.so_luong_bien_dong))) == 18
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == 6
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 12


@pytest.mark.parametrize("list_request", [False, True])
async def test_get_parent_and_items_are_one_consistent_version(
    concurrent_receipt_context, list_request
):
    client, sessions, headers = concurrent_receipt_context
    created = await client.post(BASE, headers=headers, json=BODY)
    path = created.headers["location"]
    parent_read = asyncio.Event()
    read_children = asyncio.Event()
    write_pid = asyncio.get_running_loop().create_future()

    class ObservedRepository(SqlAlchemyReceivingRepository):
        async def lock_receipt(self, record_id):
            write_pid.set_result(await self.session.scalar(select(func.pg_backend_pid())))
            return await super().lock_receipt(record_id)

    def observed_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            ObservedRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyTransaction(db),
            SqlAlchemyInventoryRepository(db),
        )

    async with sessions() as db:
        engine = (await db.connection()).engine.sync_engine

    def pause_after_parent(conn, cursor, statement, parameters, context, many):
        if statement.startswith("SELECT phieu_nhap.id") and not parent_read.is_set():
            parent_read.set()
            await_only(asyncio.wait_for(read_children.wait(), 10))

    event.listen(engine, "after_cursor_execute", pause_after_parent)
    app.dependency_overrides[get_receiving_service] = observed_service
    reader = asyncio.create_task(client.get(BASE if list_request else path, headers=headers))
    writer = None
    try:
        await asyncio.wait_for(parent_read.wait(), 5)
        writer = asyncio.create_task(
            client.patch(
                path,
                headers={**headers, "If-Match": created.headers["etag"]},
                json={"chi_tiet": [{"mat_hang_id": 1, "so_luong": 7, "don_gia_thuc": 100}]},
            )
        )
        pid = await asyncio.wait_for(write_pid, 5)
        async with sessions() as db:
            async with asyncio.timeout(5):
                while not await db.scalar(
                    text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                ):
                    assert not writer.done(), "PATCH passed while GET was between parent and items"
                    await asyncio.sleep(0.02)
        read_children.set()
        read_result, write_result = await asyncio.wait_for(asyncio.gather(reader, writer), 10)
        assert read_result.status_code == write_result.status_code == 200
        data = read_result.json()["data"]
        record = data[0] if list_request else data
        assert record["tong_tien"] == 300 and record["chi_tiet"][0]["so_luong"] == 3
        assert write_result.json()["data"]["tong_tien"] == 700
    finally:
        read_children.set()
        event.remove(engine, "after_cursor_execute", pause_after_parent)
        app.dependency_overrides.pop(get_receiving_service, None)
        await asyncio.gather(
            *(task for task in (reader, writer) if task is not None), return_exceptions=True
        )


@pytest.mark.parametrize("method", ["patch", "delete"])
async def test_draft_mutation_audit_failure_rolls_back(action_context, method):
    client, sessions, headers, record, etag = action_context

    class FailingAudit(SqlAlchemyAuditRepository):
        async def append(self, entry):
            await super().append(entry)
            await self.session.flush()
            raise RuntimeError("private audit failure")

    def failing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            SqlAlchemyReceivingRepository(db),
            FailingAudit(db),
            SqlAlchemyTransaction(db),
            SqlAlchemyInventoryRepository(db),
        )

    app.dependency_overrides[get_receiving_service] = failing_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as http:
            response = await http.request(
                method,
                f"{BASE}/{record['id']}",
                headers={**headers, "If-Match": etag},
                **(
                    {"json": {"chi_tiet": [{"mat_hang_id": 2, "so_luong": 7, "don_gia_thuc": 2}]}}
                    if method == "patch"
                    else {}
                ),
            )
        assert response.status_code == 500 and "private" not in response.text
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
    detail = await client.get(f"{BASE}/{record['id']}", headers=headers)
    assert detail.json()["data"] == record
    assert detail.headers["etag"] == etag
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


async def test_delete_then_create_does_not_reuse_ids_or_code(action_context):
    client, _, headers, record, etag = action_context
    assert (
        await client.delete(f"{BASE}/{record['id']}", headers={**headers, "If-Match": etag})
    ).status_code == 204
    new = await client.post(BASE, headers=headers, json=BODY)
    assert new.status_code == 201
    new_record = new.json()["data"]
    assert new_record["id"] > record["id"]
    assert new_record["chi_tiet"][0]["id"] > record["chi_tiet"][0]["id"]
    assert new_record["ma_phieu_nhap"] != record["ma_phieu_nhap"]


@pytest.mark.parametrize("problem", ["overflow", "drift", "stock_id_exhausted"])
async def test_stock_invariants_abort_entire_receipt(action_context, problem):
    client, sessions, headers, record, etag = action_context
    if problem == "overflow":
        large = await client.post(
            BASE,
            headers=headers,
            json={"chi_tiet": [{"mat_hang_id": 1, "so_luong": 2147483647, "don_gia_thuc": 0}]},
        )
        assert large.status_code == 201
        done = await client.post(
            large.headers["location"] + "/hoan_tat",
            headers={**headers, "If-Match": large.headers["etag"]},
            json={},
        )
        assert done.status_code == 200
    else:
        async with sessions() as db:
            db.add(
                StockLevel(
                    id=2147483647 if problem == "stock_id_exhausted" else 1,
                    mat_hang_id=2 if problem == "stock_id_exhausted" else 1,
                    so_luong=0 if problem == "stock_id_exhausted" else 10,
                )
            )
            await db.commit()
    response = await client.post(
        f"{BASE}/{record['id']}/hoan_tat", headers={**headers, "If-Match": etag}, json={}
    )
    assert response.status_code == 409
    async with sessions() as db:
        assert (await db.get(GoodsReceiptNote, record["id"])).trang_thai == "nhap"
        assert await db.scalar(select(func.count()).select_from(StockMovement)) == (
            1 if problem == "overflow" else 0
        )
        assert (
            await db.scalar(
                select(func.count())
                .select_from(AuditTrailLog)
                .where(AuditTrailLog.doi_tuong_id == record["id"])
            )
            == 1
        )


async def test_retry_still_requires_header_and_valid_posted_sources(action_context):
    client, sessions, headers, record, etag = action_context
    path = f"{BASE}/{record['id']}/hoan_tat"
    # A status flag alone is not evidence of a successful posting.
    async with sessions() as db:
        await db.execute(
            update(GoodsReceiptNote)
            .where(GoodsReceiptNote.id == record["id"])
            .values(trang_thai="hoan_thanh")
        )
        await db.commit()
    assert (
        await client.post(path, headers={**headers, "If-Match": etag}, json={})
    ).status_code == 409
    assert (await client.post(path, headers=headers, json={})).status_code == 428


async def test_patch_preserves_omitted_items_and_validates_new_references(action_context):
    client, _, headers, record, etag = action_context
    path = f"{BASE}/{record['id']}"
    for body, status in (
        ({"ncc_id": 999}, 404),
        ({"chi_tiet": [{"mat_hang_id": 999, "so_luong": 1, "don_gia_thuc": 0}]}, 404),
        ({"chi_tiet": [{"mat_hang_id": 3, "so_luong": 1, "don_gia_thuc": 0}]}, 409),
    ):
        response = await client.patch(path, headers={**headers, "If-Match": etag}, json=body)
        assert response.status_code == status
    changed = await client.patch(path, headers={**headers, "If-Match": etag}, json={"ncc_id": None})
    assert changed.status_code == 200
    assert changed.json()["data"]["chi_tiet"] == record["chi_tiet"]
    assert changed.json()["data"]["tong_tien"] == record["tong_tien"]
