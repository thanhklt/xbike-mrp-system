"""Receipt API contract and transaction tests against isolated PostgreSQL data."""

import asyncio
from datetime import datetime
from typing import Annotated

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, get_db
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_receiving_service
from app.main import app
from app.modules.audit.models import AuditTrailLog
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.catalog.models import Part
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.nha_cung_cap.models import Supplier
from app.modules.phieu_nhap.models import GoodsReceiptNote, ReceiptItem
from app.modules.phieu_nhap.repository import SqlAlchemyReceivingRepository
from app.modules.phieu_nhap.schemas import GoodsReceiptNoteCreate, ReceiptItemCreate
from app.modules.phieu_nhap.service import ReceivingService
from app.modules.users.models import User
from tests.test_auth_api import auth_context as auth_context
from tests.test_auth_api import login
from tests.test_supplier_writes import concurrent_write_context as concurrent_write_context

BASE = "/api/v1/phieu_nhap"

BODY = {"ncc_id": 1, "chi_tiet": [{"mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": 100}]}


@pytest.fixture
async def receipt_context(auth_context):
    client, sessions = auth_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(
            lambda sync: Base.metadata.create_all(
                sync,
                tables=[
                    Supplier.__table__,
                    Part.__table__,
                    GoodsReceiptNote.__table__,
                    ReceiptItem.__table__,
                ],
            )
        )
        db.add(Supplier(id=1, ma_ncc="NCC-000001", ten_ncc="Test"))
        for index, kind, active in [
            (1, "nguyen_vat_lieu", True),
            (2, "linh_kien", True),
            (3, "thanh_pham", True),
            (4, "ban_thanh_pham", True),
            (5, "linh_kien", False),
            (6, "linh_kien", None),
        ]:
            db.add(
                Part(
                    id=index,
                    ma_mat_hang=f"MH-{index:06d}",
                    sku=f"TEST-{index}",
                    loai_mat_hang=kind,
                    don_vi_tinh="chiec",
                    is_active=active,
                )
            )
        await db.commit()
    token = (await login(client, 2)).json()["data"]["access_token"]
    yield client, sessions, {"Authorization": f"Bearer {token}"}


async def test_create_read_list_and_audit(receipt_context):
    client, sessions, headers = receipt_context
    response = await client.post(BASE, headers=headers, json=BODY)
    assert response.status_code == 201, response.text
    record = response.json()["data"]
    assert record["trang_thai"] == "nhap"
    assert record["nhan_vien_id"] == 2
    assert record["tong_tien"] == 300
    assert record["created_at"].endswith("Z")
    assert record["chi_tiet"] == [
        {"id": 1, "mat_hang_id": 1, "so_luong": 3, "don_gia_thuc": 100, "tong_gia": 300}
    ]
    detail = await client.get(response.headers["location"], headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"] == record
    assert detail.headers["etag"] == response.headers["etag"]
    listing = await client.get(BASE, headers=headers)
    assert listing.json()["data"] == [record]
    assert listing.json()["meta"]["total"] == 1
    async with sessions() as db:
        audit = (
            await db.scalars(
                select(AuditTrailLog).where(AuditTrailLog.loai_doi_tuong == "phieu_nhap")
            )
        ).one()
        assert audit.thao_tac == "tao"
        assert audit.nhan_vien_id == 2
        assert audit.du_lieu_sau == record
        assert audit.du_lieu_truoc is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"chi_tiet": []},
        {**BODY, "ma_phieu_nhap": "PN-202610-000001"},
        {**BODY, "nhan_vien_id": 1},
        {**BODY, "tong_tien": 3},
        {**BODY, "trang_thai": "hoan_thanh"},
        {"chi_tiet": BODY["chi_tiet"] * 2},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 0, "don_gia_thuc": 100}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": -1}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 1.0, "don_gia_thuc": 1}]},
        {"chi_tiet": [{"mat_hang_id": True, "so_luong": 1, "don_gia_thuc": 1}]},
        {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 2147483647, "don_gia_thuc": 2}]},
    ],
)
async def test_create_validation_is_atomic(receipt_context, body):
    client, sessions, headers = receipt_context
    response = await client.post(BASE, headers=headers, json=body)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"
    async with sessions() as db:
        for model in (GoodsReceiptNote, ReceiptItem, AuditTrailLog):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.mark.parametrize("part_id,status", [(3, 409), (4, 409), (5, 409), (6, 409), (99, 404)])
async def test_reject_invalid_part(receipt_context, part_id, status):
    client, _, headers = receipt_context
    body = {"chi_tiet": [{"mat_hang_id": part_id, "so_luong": 1, "don_gia_thuc": 0}]}
    response = await client.post(BASE, headers=headers, json=body)
    assert response.status_code == status


async def test_nullable_legacy_record(receipt_context):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        db.add(
            GoodsReceiptNote(
                id=1, ma_phieu_nhap="PN-202610-000001", created_at=datetime(2026, 10, 1)
            )
        )
        await db.commit()
    response = await client.get(f"{BASE}/1", headers=headers)
    assert response.status_code == 200
    record = response.json()["data"]
    assert record["created_at"] == "2026-10-01T00:00:00Z"
    assert record["tong_tien"] is record["nhan_vien_id"] is None


def test_openapi_receipt_contract():
    paths = app.openapi()["paths"]
    assert set(paths[BASE]) == {"get", "post"}
    assert set(paths[f"{BASE}/{{id}}"]) == {"get", "patch", "delete"}
    for path, method, status in (
        (BASE, "get", "200"),
        (BASE, "post", "201"),
        (f"{BASE}/{{id}}", "get", "200"),
    ):
        operation = paths[path][method]
        assert operation["security"]
        assert {status, "401", "403", "422", "500"} <= operation["responses"].keys()
    assert "Location" in paths[BASE]["post"]["responses"]["201"]["headers"]
    assert "ETag" in paths[f"{BASE}/{{id}}"]["get"]["responses"]["200"]["headers"]


@pytest.mark.parametrize("index", [1, 3])
@pytest.mark.parametrize("method,path", [("get", BASE), ("get", f"{BASE}/1"), ("post", BASE)])
async def test_only_manager_can_access_receipts(auth_context, index, method, path):
    client, _ = auth_context
    token = (await login(client, index)).json()["data"]["access_token"]
    response = await client.request(method, path, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "khong_co_quyen"


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=101",
        "page_size=0",
        "page=abc",
        "sort=tong_tien",
        "sort=id;DROP TABLE phieu_nhap",
        "trang_thai=da_duyet",
        "ncc_id=0",
        "nhan_vien_id=-1",
        "tu_ngay=invalid",
        "tu_ngay=2026-10-22T00:00:00",
        "tu_ngay=0",
        "den_ngay=20261022",
        "tu_ngay=2026-10-23&den_ngay=2026-10-22",
        "den_ngay=9999-12-31",
        "tu_ngay=0001-01-01",
        "unknown=1",
        "page=1&page=2",
    ],
)
async def test_list_query_validation(receipt_context, query):
    client, _, headers = receipt_context
    response = await client.get(f"{BASE}?{query}", headers=headers)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "du_lieu_khong_hop_le"


@pytest.mark.parametrize(
    "record_id,status", [(0, 422), (-1, 422), ("abc", 422), (999, 404), (10**30, 404)]
)
async def test_detail_id_validation(receipt_context, record_id, status):
    client, _, headers = receipt_context
    assert (await client.get(f"{BASE}/{record_id}", headers=headers)).status_code == status


@pytest.mark.parametrize("method,path", [("get", BASE), ("get", f"{BASE}/1"), ("post", BASE)])
async def test_authentication_required_and_locked_account(receipt_context, method, path):
    client, sessions, headers = receipt_context
    missing = await client.request(method, path)
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json()["error"]["code"] == "chua_xac_thuc"
    async with sessions() as db:
        await db.execute(update(User).where(User.id == 2).values(trang_thai="bi_khoa"))
        await db.commit()
    response = await client.request(method, path, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "tai_khoan_bi_vo_hieu_hoa"


async def test_gets_only_read_and_etag_includes_items(receipt_context):
    client, sessions, headers = receipt_context
    created = await client.post(BASE, headers=headers, json=BODY)
    path = created.headers["location"]
    statements = []
    async with sessions() as db:
        engine = (await db.connection()).engine.sync_engine

    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement.strip().upper())

    event.listen(engine, "before_cursor_execute", capture)
    try:
        listing = await client.get(BASE, headers=headers)
        first = await client.get(path, headers=headers)
        second = await client.get(path, headers=headers)
        assert listing.status_code == first.status_code == second.status_code == 200
        assert first.headers["etag"] == second.headers["etag"]
        assert first.json()["meta"]["request_id"] != second.json()["meta"]["request_id"]
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    assert not any(sql.startswith(("INSERT", "UPDATE", "DELETE")) for sql in statements)
    async with sessions() as db:
        await db.execute(update(ReceiptItem).values(so_luong=4))
        await db.commit()
    assert (await client.get(path, headers=headers)).headers["etag"] != first.headers["etag"]


async def test_list_filters_dates_sort_and_pagination(receipt_context):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        for index, stamp in enumerate(
            [
                datetime(2026, 10, 21, 16, 59, 59),
                datetime(2026, 10, 21, 17),
                datetime(2026, 10, 22, 16, 59, 59),
                datetime(2026, 10, 22, 17),
            ],
            1,
        ):
            db.add(
                GoodsReceiptNote(
                    id=index,
                    ma_phieu_nhap=f"PN-202610-{index:06d}",
                    created_at=stamp,
                    ncc_id=1,
                    nhan_vien_id=2,
                    trang_thai="nhap" if index < 4 else "hoan_thanh",
                )
            )
        await db.commit()
    response = await client.get(
        BASE,
        headers=headers,
        params={
            "tu_ngay": "2026-10-22",
            "den_ngay": "2026-10-22",
            "ncc_id": 1,
            "nhan_vien_id": 2,
            "trang_thai": "nhap",
            "q": "pn-202610",
            "sort": "-created_at",
            "page_size": 1,
        },
    )
    assert response.status_code == 200, response.text
    assert [r["id"] for r in response.json()["data"]] == [3]
    assert response.json()["meta"]["total"] == 2
    assert response.json()["meta"]["total_pages"] == 2
    for query in ({"q": "%"}, {"q": "_"}, {"q": "' OR 1=1 --"}, {"page": 10**30}, {"ncc_id": 99}):
        result = await client.get(BASE, headers=headers, params=query)
        assert result.status_code == 200
        assert result.json()["data"] == []


async def test_create_without_supplier_and_zero_price(receipt_context):
    client, _, headers = receipt_context
    body = {"chi_tiet": [{"mat_hang_id": 2, "so_luong": 2, "don_gia_thuc": 0}]}
    response = await client.post(BASE, headers=headers, json=body)
    assert response.status_code == 201
    assert response.json()["data"]["tong_tien"] == 0
    assert response.json()["data"]["ncc_id"] is None


async def test_missing_supplier_and_query_rejected(receipt_context):
    client, _, headers = receipt_context
    assert (
        await client.post(BASE, headers=headers, json={**BODY, "ncc_id": 99})
    ).status_code == 404
    assert (await client.post(f"{BASE}?x=1", headers=headers, json=BODY)).status_code == 422
    assert (await client.get(f"{BASE}/1?x=1", headers=headers)).status_code == 422


async def test_audit_failure_rolls_back_parent_and_all_items(receipt_context):
    _, sessions, headers = receipt_context

    class FailingAudit(SqlAlchemyAuditRepository):
        async def append(self, entry):
            await super().append(entry)
            await self.session.flush()
            raise RuntimeError("private injected failure")

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
        ) as client:
            response = await client.post(
                BASE,
                headers=headers,
                json={
                    "chi_tiet": [
                        BODY["chi_tiet"][0],
                        {"mat_hang_id": 2, "so_luong": 2, "don_gia_thuc": 50},
                    ]
                },
            )
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "loi_noi_bo"
        assert "private" not in response.text
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
    async with sessions() as db:
        for model in (GoodsReceiptNote, ReceiptItem, AuditTrailLog):
            assert await db.scalar(select(func.count()).select_from(model)) == 0


@pytest.fixture
async def concurrent_receipt_context(concurrent_write_context):
    client, sessions, headers = concurrent_write_context
    async with sessions() as db:
        connection = await db.connection()
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync))
        db.add(
            Part(
                id=1,
                ma_mat_hang="MH-000001",
                sku="test",
                loai_mat_hang="linh_kien",
                don_vi_tinh="chiec",
                is_active=True,
            )
        )
        await db.commit()
    yield client, sessions, headers


async def test_concurrent_creates_have_unique_codes_ids_and_atomic_audits(
    concurrent_receipt_context,
):
    client, sessions, headers = concurrent_receipt_context
    barrier = asyncio.Barrier(6)

    class RacingRepository(SqlAlchemyReceivingRepository):
        async def _allocate(self, item_count, prefix):
            await asyncio.wait_for(barrier.wait(), 5)
            return await super()._allocate(item_count, prefix)

    def racing_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            RacingRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyTransaction(db),
            SqlAlchemyInventoryRepository(db),
        )

    app.dependency_overrides[get_receiving_service] = racing_service
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(client.post(BASE, headers=headers, json=BODY) for _ in range(6))), 15
        )
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
    assert [r.status_code for r in results] == [201] * 6
    records = [r.json()["data"] for r in results]
    assert len({r["id"] for r in records}) == 6
    assert len({r["ma_phieu_nhap"] for r in records}) == 6
    assert len({r["chi_tiet"][0]["id"] for r in records}) == 6
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 6
        for table in ("ton_kho", "giao_dich_kho"):
            assert (
                await db.scalar(select(func.count()).select_from(Base.metadata.tables[table])) == 0
            )


@pytest.mark.parametrize(
    "stamp,prefix",
    [
        (datetime(2026, 10, 31, 16, 59, 59), "PN-202610-"),
        (datetime(2026, 10, 31, 17), "PN-202611-"),
    ],
)
async def test_monthly_code_uses_vietnam_time_and_audit_history(receipt_context, stamp, prefix):
    _, sessions, _ = receipt_context
    async with sessions() as db:
        db.add(
            AuditTrailLog(
                nhan_vien_id=2,
                loai_doi_tuong="phieu_nhap",
                doi_tuong_id=91,
                thao_tac="xoa_nhap",
                du_lieu_truoc={
                    "id": 91,
                    "ma_phieu_nhap": "PN-202611-000010",
                    "chi_tiet": [{"id": 101}],
                },
                du_lieu_sau=None,
            )
        )
        await db.commit()
        repository = SqlAlchemyReceivingRepository(db)
        record = await repository.add_draft(
            GoodsReceiptNoteCreate(
                ma_phieu_nhap="",
                nhan_vien_id=2,
                tong_tien=1,
                items=[ReceiptItemCreate(mat_hang_id=1, so_luong=1, don_gia_thuc=1, tong_gia=1)],
            ),
            created_at=stamp,
        )
        assert record.id == 92
        assert record.chi_tiet[0].id == 102
        assert record.ma_phieu_nhap == prefix + ("000001" if stamp.hour == 16 else "000011")
        await db.rollback()


@pytest.mark.parametrize("exhausted", ["parent", "item", "code"])
async def test_exhausted_allocation_rolls_back(receipt_context, exhausted):
    client, sessions, headers = receipt_context
    async with sessions() as db:
        month = await db.scalar(
            text("SELECT to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYYMM')")
        )
        db.add(
            AuditTrailLog(
                nhan_vien_id=2,
                loai_doi_tuong="phieu_nhap",
                doi_tuong_id=2147483647 if exhausted == "parent" else 1,
                thao_tac="xoa_nhap",
                du_lieu_truoc={
                    "ma_phieu_nhap": f"PN-{month}-999999"
                    if exhausted == "code"
                    else f"PN-{month}-000001",
                    "items": [{"id": 2147483647 if exhausted == "item" else 1}],
                },
            )
        )
        await db.commit()
    response = await client.post(BASE, headers=headers, json=BODY)
    assert response.status_code == 409
    async with sessions() as db:
        assert await db.scalar(select(func.count()).select_from(GoodsReceiptNote)) == 0
        assert await db.scalar(select(func.count()).select_from(ReceiptItem)) == 0
        assert await db.scalar(select(func.count()).select_from(AuditTrailLog)) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("mat_hang_id", 1.5),
        ("so_luong", "2"),
        ("so_luong", True),
        ("don_gia_thuc", None),
        ("don_gia_thuc", 1.5),
        ("id", 1),
        ("tong_gia", 1),
    ],
)
async def test_item_fields_are_strict(receipt_context, field, value):
    client, _, headers = receipt_context
    item = {**BODY["chi_tiet"][0], field: value}
    response = await client.post(BASE, headers=headers, json={"chi_tiet": [item]})
    assert response.status_code == 422


async def test_multi_item_total_overflow(receipt_context):
    client, _, headers = receipt_context
    response = await client.post(
        BASE,
        headers=headers,
        json={
            "chi_tiet": [
                {"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": 2147483647},
                {"mat_hang_id": 2, "so_luong": 1, "don_gia_thuc": 1},
            ]
        },
    )
    assert response.status_code == 422


async def test_legacy_receiving_route_shares_allocator_and_preserves_shape(receipt_context):
    client, _, headers = receipt_context
    legacy = await client.post(
        "/api/v1/receiving",
        headers=headers,
        json={"ma_phieu_nhap": "PN-202610-000555", "items": [{"mat_hang_id": 1, "so_luong": 1}]},
    )
    assert legacy.status_code == 201
    assert "items" in legacy.json()
    assert legacy.json()["nhan_vien_id"] == 2
    canonical = await client.post(BASE, headers=headers, json=BODY)
    assert canonical.status_code == 201
    assert canonical.json()["data"]["id"] == legacy.json()["id"] + 1
    assert canonical.json()["data"]["chi_tiet"][0]["id"] == legacy.json()["items"][0]["id"] + 1
    assert (
        await client.get(f"/api/v1/receiving/{legacy.json()['id']}", headers=headers)
    ).status_code == 200


@pytest.mark.parametrize("target", ["supplier_delete", "part_deactivate"])
async def test_references_changed_before_create_are_rechecked_under_lock(
    concurrent_receipt_context, target
):
    client, sessions, headers = concurrent_receipt_context
    request_pid = asyncio.get_running_loop().create_future()

    class ObservedRepository(SqlAlchemyReceivingRepository):
        async def lock_supplier(self, record_id):
            if target == "supplier_delete":
                request_pid.set_result(await self.session.scalar(select(func.pg_backend_pid())))
            return await super().lock_supplier(record_id)

        async def lock_parts(self, ids):
            if target == "part_deactivate":
                request_pid.set_result(await self.session.scalar(select(func.pg_backend_pid())))
            return await super().lock_parts(ids)

    def observed_service(db: Annotated[AsyncSession, Depends(get_db)]):
        return ReceivingService(
            ObservedRepository(db),
            SqlAlchemyAuditRepository(db),
            SqlAlchemyTransaction(db),
            SqlAlchemyInventoryRepository(db),
        )

    app.dependency_overrides[get_receiving_service] = observed_service
    task = None
    try:
        async with sessions() as changer:
            if target == "supplier_delete":
                await changer.execute(text("DELETE FROM nha_cung_cap WHERE id=1"))
            else:
                await changer.execute(update(Part).where(Part.id == 1).values(is_active=False))
            task = asyncio.create_task(client.post(BASE, headers=headers, json=BODY))
            pid = await asyncio.wait_for(request_pid, 5)
            async with sessions() as observer:
                async with asyncio.timeout(5):
                    while not await observer.scalar(
                        text("SELECT cardinality(pg_blocking_pids(:pid)) > 0"), {"pid": pid}
                    ):
                        assert not task.done()
                        await asyncio.sleep(0.02)
            await changer.commit()
            response = await asyncio.wait_for(task, 10)
        assert response.status_code == (404 if target == "supplier_delete" else 409)
        async with sessions() as db:
            for model in (GoodsReceiptNote, ReceiptItem, AuditTrailLog):
                assert await db.scalar(select(func.count()).select_from(model)) == 0
    finally:
        app.dependency_overrides.pop(get_receiving_service, None)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
