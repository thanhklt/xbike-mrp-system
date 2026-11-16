"""UC-20..22 / GR-AC PostgreSQL locks, atomicity, ledger and actual v4 constraints."""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.phieu_nhap.models import ChiTietPhieuNhap, PhieuNhap
from app.modules.phieu_nhap.repository import SqlAlchemyPhieuNhapRepository
from app.modules.phieu_nhap.service import PhieuNhapService

BASE = "/api/v1/phieu_nhap"
MANAGER = {"sub": "1", "roles": ["quan_ly"]}


def receipt_service(session):
    return PhieuNhapService(
        SqlAlchemyPhieuNhapRepository(session),
        AuditService(SqlAlchemyAuditRepository(session)),
        SqlAlchemyTransaction(session),
        SqlAlchemyInventoryRepository(session),
    )


@pytest.fixture
def receipt_race(monkeypatch):
    def synchronize(owner=SqlAlchemyPhieuNhapRepository, method="lock_receipt"):
        barrier = asyncio.Barrier(2)
        original = getattr(owner, method)

        async def synchronized(repository, *args, **kwargs):
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return await original(repository, *args, **kwargs)

        monkeypatch.setattr(owner, method, synchronized)

    return synchronize


async def test_uc21_gr_ac12_two_completes_post_once(
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
    receipt_race,
):
    created = await goods_receipt_draft()
    receipt_race()
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_receipt_client.post(
                    created.headers["location"] + "/hoan_tat",
                    headers={**goods_receipt_auth(actor), "If-Match": created.headers["etag"]},
                    json={},
                )
                for actor in (1, 2)
            )
        ),
        timeout=20,
    )
    assert [response.status_code for response in responses] == [200, 200]
    assert sorted(response.json()["data"]["da_ghi_so_truoc_do"] for response in responses) == [
        False,
        True,
    ]
    scenario = goods_receipt_scenario
    assert (
        await scenario.scalar(
            'SELECT so_luong_ton FROM "MatHang" WHERE id=:id', id=scenario.items[0]
        )
        == 60
    )
    assert (
        await scenario.scalar(
            'SELECT count(*) FROM "GiaoDichKho" WHERE chi_tiet_phieu_nhap_id=:id',
            id=created.json()["data"]["chi_tiet"][0]["id"],
        )
        == 1
    )
    assert (
        await scenario.scalar("SELECT count(*) FROM \"LichSuThaoTac\" WHERE thao_tac='hoan_tat'")
        == 1
    )


@pytest.mark.parametrize("competitor", ["PATCH", "DELETE"])
async def test_uc20_uc21_gr_ac10_12_complete_vs_mutation(
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
    receipt_race,
    competitor,
):
    created = await goods_receipt_draft()
    path = created.headers["location"]
    headers = {**goods_receipt_auth(), "If-Match": created.headers["etag"]}
    receipt_race()
    complete, mutation = await asyncio.wait_for(
        asyncio.gather(
            goods_receipt_client.post(path + "/hoan_tat", headers=headers, json={}),
            goods_receipt_client.request(
                competitor,
                path,
                headers=headers,
                **({"json": {"ghi_chu": "Racing edit"}} if competitor == "PATCH" else {}),
            ),
        ),
        timeout=20,
    )
    if complete.status_code == 200:
        assert mutation.status_code == 412
        expected_stock, expected_count = 60, 1
    else:
        assert complete.status_code == (412 if competitor == "PATCH" else 404)
        assert mutation.status_code == (200 if competitor == "PATCH" else 204)
        expected_stock, expected_count = 10, 0
    scenario = goods_receipt_scenario
    assert (
        await scenario.scalar(
            'SELECT so_luong_ton FROM "MatHang" WHERE id=:id', id=scenario.items[0]
        )
        == expected_stock
    )
    assert (
        await scenario.scalar("SELECT count(*) FROM \"LichSuThaoTac\" WHERE thao_tac='hoan_tat'")
        == expected_count
    )


async def test_uc20_gr_ac19_concurrent_codes(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, receipt_race
):
    receipt_race(SqlAlchemyPhieuNhapRepository, "lock_parts")
    results = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_receipt_client.post(
                    BASE, headers=goods_receipt_auth(actor), json=goods_receipt_scenario.payload()
                )
                for actor in (1, 2)
            )
        ),
        timeout=20,
    )
    assert [response.status_code for response in results] == [201, 201]
    assert len({response.json()["data"]["id"] for response in results}) == 2
    assert sorted(response.json()["data"]["ma_phieu_nhap"][-6:] for response in results) == [
        "000001",
        "000002",
    ]


async def test_uc21_gr_ac21_two_receipts_same_item(
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
    receipt_race,
):
    first, second = (
        await goods_receipt_draft(),
        await goods_receipt_draft(goods_receipt_scenario.payload(quantity=20)),
    )
    before = await goods_receipt_scenario.snapshot()
    receipt_race(SqlAlchemyInventoryRepository, "lock_receipt_stock")
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_receipt_client.post(
                    created.headers["location"] + "/hoan_tat",
                    headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
                    json={},
                )
                for created in (first, second)
            )
        ),
        timeout=20,
    )
    assert [response.status_code for response in responses] == [200, 200]
    after = await goods_receipt_scenario.snapshot()
    item = next(row for row in after["MatHang"] if row["id"] == goods_receipt_scenario.items[0])
    assert (item["so_luong_ton"], item["so_luong_dang_giu"], item["so_luong_con_dung"]) == (
        80,
        5,
        75,
    )
    assert (
        after["GiuHang"] == before["GiuHang"] and after["YeuCauSanXuat"] == before["YeuCauSanXuat"]
    )
    assert [row["so_luong_ton_sau"] for row in after["GiaoDichKho"][-2:]] in ([60, 80], [30, 80])


@pytest.mark.parametrize(
    "failure",
    ["after_metadata", "during_second_ledger", "after_inventory", "after_audit", "commit"],
)
async def test_uc21_gr_ac13_every_write_rolls_back(
    goods_receipt_database, goods_receipt_scenario, goods_receipt_draft, monkeypatch, failure
):
    scenario = goods_receipt_scenario
    payload = scenario.payload()
    payload["chi_tiet"].append(
        {"mat_hang_id": scenario.items[1], "so_luong": 4, "don_gia_thuc": 1000}
    )
    created = await goods_receipt_draft(payload)
    before = await scenario.snapshot()
    error = RuntimeError("intentional receipt rollback verification")
    count = 0
    if failure == "during_second_ledger":

        def fail_ledger(_conn, _cursor, statement, _parameters, _context, _many):
            nonlocal count
            if 'INSERT INTO "GiaoDichKho"' in statement:
                count += 1
                if count == 2:
                    raise error

        event.listen(
            goods_receipt_database.engine.sync_engine, "before_cursor_execute", fail_ledger
        )
    elif failure == "commit":

        async def fail_commit(session):
            await session.flush()
            raise error

        monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    else:
        owner, name = {
            "after_metadata": (SqlAlchemyPhieuNhapRepository, "mark_completed"),
            "after_inventory": (SqlAlchemyInventoryRepository, "receive_receipt"),
            "after_audit": (PhieuNhapService, "_audit_change"),
        }[failure]
        original = getattr(owner, name)

        async def fail_after(self, *args, **kwargs):
            await original(self, *args, **kwargs)
            raise error

        monkeypatch.setattr(owner, name, fail_after)
    try:
        async with goods_receipt_database.sessions() as session:
            with pytest.raises(RuntimeError, match="intentional receipt rollback verification"):
                await receipt_service(session).complete_receipt(
                    created.json()["data"]["id"], created.headers["etag"], MANAGER, "rollback-test"
                )
    finally:
        if failure == "during_second_ledger":
            event.remove(
                goods_receipt_database.engine.sync_engine, "before_cursor_execute", fail_ledger
            )
        monkeypatch.undo()
    assert await scenario.snapshot() == before


@pytest.mark.parametrize("action", ["create", "patch", "delete"])
async def test_uc20_gr_ac13_audit_failure_rolls_back_draft_mutation(
    goods_receipt_database, goods_receipt_scenario, goods_receipt_draft, monkeypatch, action
):
    from app.modules.phieu_nhap.schemas import PhieuNhapCreate, PhieuNhapPatch

    created = await goods_receipt_draft()
    before = await goods_receipt_scenario.snapshot()
    original = AuditService.append

    async def fail_audit(service, entry):
        await original(service, entry)
        raise RuntimeError("intentional audit failure")

    monkeypatch.setattr(AuditService, "append", fail_audit)
    async with goods_receipt_database.sessions() as session:
        service = receipt_service(session)
        with pytest.raises(RuntimeError, match="intentional audit failure"):
            if action == "create":
                await service.create_receipt(
                    PhieuNhapCreate.model_validate(goods_receipt_scenario.payload()),
                    MANAGER,
                    "rollback-test",
                )
            elif action == "patch":
                await service.patch_receipt(
                    created.json()["data"]["id"],
                    PhieuNhapPatch(ghi_chu="Edited"),
                    created.headers["etag"],
                    MANAGER,
                    "rollback-test",
                )
            else:
                await service.delete_receipt(
                    created.json()["data"]["id"], created.headers["etag"], MANAGER
                )
    assert await goods_receipt_scenario.snapshot() == before


@pytest.mark.parametrize(
    "corruption", ["ledger_balance", "wrong_total", "null_total", "empty_lines"]
)
async def test_uc21_gr_ac14_inconsistent_data_is_not_repaired(
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
    corruption,
):
    scenario = goods_receipt_scenario
    created = await goods_receipt_draft()
    identifier = created.json()["data"]["id"]
    if corruption == "ledger_balance":
        await scenario.sql(
            'UPDATE "MatHang" SET so_luong_ton=11 WHERE id=:id', id=scenario.items[0]
        )
    elif corruption == "wrong_total":
        await scenario.sql('UPDATE "PhieuNhap" SET tong_tien=1 WHERE id=:id', id=identifier)
    elif corruption == "null_total":
        await scenario.sql('UPDATE "PhieuNhap" SET tong_tien=NULL WHERE id=:id', id=identifier)
    else:
        await scenario.sql('DELETE FROM "ChiTietPhieuNhap" WHERE phieu_nhap_id=:id', id=identifier)
    current = await goods_receipt_client.get(
        created.headers["location"], headers=goods_receipt_auth()
    )
    before = await scenario.snapshot()
    response = await goods_receipt_client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": current.headers["etag"]},
        json={},
    )
    assert response.status_code == 409, response.text
    assert await scenario.snapshot() == before


async def test_uc21_gr_ac14_integer_stock_overflow_with_valid_ledger(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    scenario = goods_receipt_scenario
    old = await scenario.scalar(
        """INSERT INTO "PhieuNhap" (ma_phieu_nhap,nhan_vien_id,ncc_id,ngay_nhap) VALUES ('PN-200001-999999',1,:ncc,'2000-01-01') RETURNING id""",
        ncc=scenario.suppliers[0],
    )
    line = await scenario.scalar(
        'INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia) VALUES (:old,:item,2147483637,0,0) RETURNING id',
        old=old,
        item=scenario.items[0],
    )
    await scenario.sql(
        """UPDATE "PhieuNhap" SET trang_thai='hoan_thanh',tong_tien=0,hoan_thanh_at=now(),nguoi_hoan_thanh_id=1 WHERE id=:id""",
        id=old,
    )
    await scenario.sql(
        """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chi_tiet_phieu_nhap_id,nhan_vien_id) VALUES (:item,'nhap_linh_kien',2147483637,2147483647,:line,1)""",
        item=scenario.items[0],
        line=line,
    )
    await scenario.sql(
        'UPDATE "MatHang" SET so_luong_ton=2147483647 WHERE id=:id', id=scenario.items[0]
    )
    created = await goods_receipt_draft()
    before = await scenario.snapshot()
    response = await goods_receipt_client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert response.status_code == 409, response.text
    assert await scenario.snapshot() == before


async def test_uc21_gr_ac11_replay_header_and_sql_no_writes(
    goods_receipt_database,
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
):
    created = await goods_receipt_draft()
    path = created.headers["location"] + "/hoan_tat"
    approved = await goods_receipt_client.post(
        path, headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]}, json={}
    )
    assert approved.status_code == 200
    # Valid subsequent catalog/stock changes must not invalidate the previous result.
    await goods_receipt_scenario.sql(
        'UPDATE "MatHang" SET don_gia=1 WHERE id=:id', id=goods_receipt_scenario.items[0]
    )
    before = await goods_receipt_scenario.snapshot()
    writes = []

    def observe(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)

    event.listen(goods_receipt_database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        for tag, status in (
            (None, 428),
            (" ", 428),
            ("*", 412),
            ("W/" + created.headers["etag"], 412),
            (created.headers["etag"] + "," + approved.headers["etag"], 412),
            (created.headers["etag"], 200),
        ):
            response = await goods_receipt_client.post(
                path,
                headers={**goods_receipt_auth(), **({"If-Match": tag} if tag is not None else {})},
                json={},
            )
            assert response.status_code == status, response.text
        assert writes == []
    finally:
        event.remove(goods_receipt_database.engine.sync_engine, "before_cursor_execute", observe)
    assert await goods_receipt_scenario.snapshot() == before


async def test_uc21_gr_ac11_incomplete_posting_no_repair(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    created = await goods_receipt_draft()
    await goods_receipt_scenario.sql(
        """UPDATE "PhieuNhap" SET trang_thai='hoan_thanh',hoan_thanh_at=now(),nguoi_hoan_thanh_id=1 WHERE id=:id""",
        id=created.json()["data"]["id"],
    )
    before = await goods_receipt_scenario.snapshot()
    result = await goods_receipt_client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert result.status_code == 409
    assert await goods_receipt_scenario.snapshot() == before


async def test_uc21_gr_ac10_conditional_update_rejects_changed_version(
    goods_receipt_database, goods_receipt_scenario, goods_receipt_draft
):
    created = await goods_receipt_draft()
    before = await goods_receipt_scenario.snapshot()
    async with goods_receipt_database.sessions() as session:
        result = await SqlAlchemyPhieuNhapRepository(session).mark_completed(
            created.json()["data"]["id"],
            expected_version=99,
            actor_id=1,
            completed_at=datetime.now(timezone.utc),
        )
        assert result is None
        await session.commit()
    assert await goods_receipt_scenario.snapshot() == before


async def test_uc22_gr_ac15_16_readonly_filters_dates_ties(
    goods_receipt_database,
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
):
    created = [await goods_receipt_draft() for _ in range(3)]
    ids = [response.json()["data"]["id"] for response in created]
    scenario = goods_receipt_scenario
    at = datetime(2026, 11, 13, 17, tzinfo=timezone.utc)
    for identifier in ids[:2]:
        await scenario.sql(
            'UPDATE "PhieuNhap" SET created_at=:at WHERE id=:id', at=at, id=identifier
        )
    await scenario.sql(
        'UPDATE "PhieuNhap" SET created_at=:at WHERE id=:id',
        at=datetime(2026, 11, 14, 17, tzinfo=timezone.utc),
        id=ids[-1],
    )
    before = await scenario.snapshot()
    writes = []

    def observe(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)

    event.listen(goods_receipt_database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        actual = []
        for page in (1, 2):
            response = await goods_receipt_client.get(
                BASE
                + f"?tu_ngay=2026-11-14&den_ngay=2026-11-14&trang_thai=nhap&ncc_id={scenario.suppliers[0]}&nhan_vien_id=1&sort=created_at&page_size=1&page={page}",
                headers=goods_receipt_auth(),
            )
            assert response.status_code == 200 and response.json()["meta"]["total"] == 2
            actual.extend(row["id"] for row in response.json()["data"])
        assert actual == ids[:2]
        for q in ("_", "%25"):
            assert (
                await goods_receipt_client.get(BASE + "?q=" + q, headers=goods_receipt_auth())
            ).json()["data"] == []
        assert (
            await goods_receipt_client.get(
                BASE + "?page=99999999999999999999", headers=goods_receipt_auth()
            )
        ).json()["data"] == []
        detail = await goods_receipt_client.get(
            created[0].headers["location"], headers=goods_receipt_auth()
        )
        listing = await goods_receipt_client.get(
            BASE + "?q=" + detail.json()["data"]["ma_phieu_nhap"].lower(),
            headers=goods_receipt_auth(),
        )
        assert listing.json()["data"] == [detail.json()["data"]]
        assert writes == []
    finally:
        event.remove(goods_receipt_database.engine.sync_engine, "before_cursor_execute", observe)
    assert await scenario.snapshot() == before


async def test_uc20_gr_ac19_mapping_reflects_bootstrap(goods_receipt_database):
    def check(connection):
        inspector = inspect(connection)
        for model in (PhieuNhap, ChiTietPhieuNhap, LichSuThaoTac):
            table = model.__table__
            columns = {column["name"]: column for column in inspector.get_columns(table.name)}
            assert set(columns) == set(table.columns.keys())
            for column in table.columns:
                reflected = columns[column.name]
                assert reflected["nullable"] == column.nullable
                assert str(reflected["type"].compile(dialect=dialect())) == str(
                    column.type.compile(dialect=dialect())
                )
                if column.identity:
                    assert reflected["identity"]["always"] == column.identity.always
                elif column.server_default:
                    assert reflected["default"].replace("::character varying", "").strip(
                        "()"
                    ) == str(column.server_default.arg).strip("()")
            assert set(inspector.get_pk_constraint(table.name)["constrained_columns"]) == {
                column.name for column in table.primary_key
            }
            assert {
                constraint["name"] for constraint in inspector.get_check_constraints(table.name)
            } == {
                constraint.name
                for constraint in table.constraints
                if constraint.__class__.__name__ == "CheckConstraint"
            }
            indexes = {index["name"]: index for index in inspector.get_indexes(table.name)}
            for index in table.indexes:
                assert indexes[index.name]["unique"] == index.unique
                assert indexes[index.name]["column_names"] == [
                    column.name for column in index.columns
                ]
            fks = inspector.get_foreign_keys(table.name)
            assert len(fks) == len(table.foreign_keys)
            for fk in table.foreign_keys:
                reflected = next(
                    row for row in fks if row["constrained_columns"] == [fk.parent.name]
                )
                assert reflected["referred_table"] == fk.column.table.name
                assert reflected["options"].get("deferrable") is True
                assert reflected["options"].get("initially", "IMMEDIATE") == "IMMEDIATE"

    async with goods_receipt_database.engine.connect() as connection:
        await connection.run_sync(check)


async def test_uc20_uc21_gr_ac19_posted_data_immutable(
    goods_receipt_database,
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
):
    created = await goods_receipt_draft()
    result = await goods_receipt_client.post(
        created.headers["location"] + "/hoan_tat",
        headers={**goods_receipt_auth(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert result.status_code == 200
    before = await goods_receipt_scenario.snapshot()
    for statement in (
        'UPDATE "PhieuNhap" SET tong_tien=0',
        'DELETE FROM "ChiTietPhieuNhap"',
        'UPDATE "GiaoDichKho" SET so_luong_ton_sau=0',
        'DELETE FROM "LichSuThaoTac"',
    ):
        async with goods_receipt_database.sessions() as session:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement))
            await session.rollback()
    assert await goods_receipt_scenario.snapshot() == before


async def test_uc20_gr_ac19_code_exhaustion_is_atomic(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario
):
    scenario = goods_receipt_scenario
    await scenario.sql(
        """INSERT INTO "LichSuThaoTac" (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_sau) VALUES (1,'phieu_nhap',999,'tao',jsonb_build_object('ma_phieu_nhap','PN-' || to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh','YYYYMM') || '-999999'))"""
    )
    before = await scenario.snapshot()
    result = await goods_receipt_client.post(
        BASE, headers=goods_receipt_auth(), json=scenario.payload()
    )
    assert result.status_code == 409
    assert await scenario.snapshot() == before


async def test_uc22_gr_ac20_supplier_is_live_reference(
    goods_receipt_client, goods_receipt_auth, goods_receipt_scenario, goods_receipt_draft
):
    created = await goods_receipt_draft()
    await goods_receipt_scenario.sql(
        "UPDATE \"NhaCungCap\" SET ten_ncc='Updated supplier' WHERE id=:id",
        id=goods_receipt_scenario.suppliers[0],
    )
    response = await goods_receipt_client.get(
        created.headers["location"], headers=goods_receipt_auth()
    )
    assert response.status_code == 200 and response.json()["data"] == created.json()["data"]
    assert response.headers["etag"] == created.headers["etag"]
    assert (
        await goods_receipt_scenario.scalar(
            'SELECT ten_ncc FROM "NhaCungCap" WHERE id=:id', id=response.json()["data"]["ncc_id"]
        )
        == "Updated supplier"
    )


async def test_uc22_gr_ac15_count_and_page_share_snapshot_during_insert(
    goods_receipt_client,
    goods_receipt_auth,
    goods_receipt_scenario,
    goods_receipt_draft,
    monkeypatch,
):
    await goods_receipt_draft()
    counted, release = asyncio.Event(), asyncio.Event()
    original = AsyncSession.scalar

    async def pause_after_count(session, statement, *args, **kwargs):
        result = await original(session, statement, *args, **kwargs)
        if (
            not counted.is_set()
            and "count(*)" in str(statement).lower()
            and "PhieuNhap" in str(statement)
        ):
            counted.set()
            await asyncio.wait_for(release.wait(), timeout=10)
        return result

    monkeypatch.setattr(AsyncSession, "scalar", pause_after_count)
    reading = asyncio.create_task(goods_receipt_client.get(BASE, headers=goods_receipt_auth()))
    try:
        await asyncio.wait_for(counted.wait(), timeout=10)
        inserted = await goods_receipt_draft()
    finally:
        release.set()
    response = await asyncio.wait_for(reading, timeout=10)
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 2 and len(response.json()["data"]) == 2
    assert inserted.json()["data"]["id"] not in {row["id"] for row in response.json()["data"]}
    latest = await goods_receipt_client.get(BASE, headers=goods_receipt_auth())
    assert latest.json()["meta"]["total"] == 3
