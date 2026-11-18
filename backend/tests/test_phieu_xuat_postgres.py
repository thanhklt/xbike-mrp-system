"""UC-34..40 / GI-AC: real v4 constraints, locks, reservations and rollback."""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import event, inspect, text
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import PostedProductionDependency
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.phieu_xuat.models import ChiTietPhieuXuat, PhieuXuat
from app.modules.phieu_xuat.repository import SqlAlchemyPhieuXuatRepository
from app.modules.phieu_xuat.service import PhieuXuatService

BASE = "/api/v1/phieu_xuat"
MANAGER = {"sub": "1", "roles": ["quan_ly"]}


async def test_waiting_issue_can_be_sent_then_approved_after_receipt(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending,
):
    scenario = goods_issue_scenario
    source = await scenario.source(production=101, state="cho_bo_sung_linh_kien")
    created, pending, _ = await goods_issue_pending(source=source)
    path = created.headers["location"]
    headers = {**goods_issue_auth(1), "If-Match": pending.headers["etag"]}
    before = await scenario.snapshot()

    rejected = await goods_issue_client.post(path + "/duyet", headers=headers, json={})
    assert rejected.status_code == 409, rejected.text
    assert await scenario.snapshot() == before

    # A real receipt supplies stock; receiving does not approve the pending issue.
    from datetime import date

    receipt = await goods_issue_client.post(
        "/api/v1/phieu_nhap", headers=goods_issue_auth(1), json={
            "ncc_id": 1, "ngay_nhap": date.today().isoformat(),
            "chi_tiet": [{"mat_hang_id": item, "so_luong": 200, "don_gia_thuc": 1}
                      for item in scenario.component_ids],
        },
    )
    assert receipt.status_code == 201, receipt.text
    received = await goods_issue_client.post(
        receipt.headers["location"] + "/hoan_tat",
        headers={**goods_issue_auth(1), "If-Match": receipt.headers["etag"]}, json={},
    )
    assert received.status_code == 200, received.text
    assert await scenario.scalar('SELECT trang_thai FROM "PhieuXuat"') == "cho_duyet"

    approved = await goods_issue_client.post(path + "/duyet", headers=headers, json={})
    assert approved.status_code == 200, approved.text
    assert await scenario.scalar(
        'SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=:id', id=source,
    ) == "dang_thuc_hien"
    assert await scenario.scalar('SELECT sum(so_luong_dang_giu) FROM "MatHang"') == 0
    assert [row["so_luong_ton"] for row in await scenario.sql(
        'SELECT so_luong_ton FROM "MatHang" WHERE loai_mat_hang=\'linh_kien\' ORDER BY id',
    )] == [199, 98]
    replay = await goods_issue_client.post(path + "/duyet", headers=headers, json={})
    assert replay.status_code == 200
    assert replay.json()["data"]["da_ghi_so_truoc_do"] is True


@pytest.fixture
def race_at_source(monkeypatch):
    def synchronize():
        barrier = asyncio.Barrier(2)
        original = SqlAlchemyPhieuXuatRepository.lock_source

        async def lock_source(repository, *args, **kwargs):
            await asyncio.wait_for(barrier.wait(), timeout=10)
            return await original(repository, *args, **kwargs)

        monkeypatch.setattr(SqlAlchemyPhieuXuatRepository, "lock_source", lock_source)

    return synchronize


def issue_service(session):
    return PhieuXuatService(
        SqlAlchemyPhieuXuatRepository(session),
        AuditService(SqlAlchemyAuditRepository(session)),
        SqlAlchemyTransaction(session),
        SqlAlchemyInventoryRepository(session),
    )


async def test_two_waiting_issues_cannot_use_the_same_available_stock(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending, race_at_source,
):
    scenario = goods_issue_scenario
    sources = [await scenario.source(production=40, state="cho_bo_sung_linh_kien") for _ in range(2)]
    issues = [await goods_issue_pending(source=source) for source in sources]
    race_at_source()
    results = await asyncio.gather(*(
        goods_issue_client.post(created.headers["location"] + "/duyet", headers={
            **goods_issue_auth(1), "If-Match": pending.headers["etag"],
        }, json={}) for created, pending, _ in issues
    ))
    assert sorted(result.status_code for result in results) == [200, 409]
    assert await scenario.scalar('SELECT sum(so_luong_dang_giu) FROM "MatHang"') == 0
    assert await scenario.scalar('SELECT count(*) FROM "GiaoDichKho" WHERE chi_tiet_phieu_xuat_id IS NOT NULL') == 2


async def test_waiting_issue_rolls_back_new_reservations_and_source_on_posting_failure(
    goods_issue_database, goods_issue_scenario, goods_issue_pending, monkeypatch,
):
    scenario = goods_issue_scenario
    source = await scenario.source(state="cho_bo_sung_linh_kien")
    created, pending, _ = await goods_issue_pending(source=source)
    before = await scenario.snapshot()

    async def fail_posting(*args, **kwargs):
        raise RuntimeError("posting failure after reservation")

    monkeypatch.setattr(SqlAlchemyInventoryRepository, "issue_stock", fail_posting)
    async with goods_issue_database.sessions() as session:
        with pytest.raises(RuntimeError, match="posting failure after reservation"):
            await issue_service(session).approve(
                created.json()["data"]["id"], MANAGER, pending.headers["etag"], "rollback-test",
            )
    assert await scenario.snapshot() == before


async def test_uc34_gi_ac04_13_concurrent_create(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, race_at_source
):
    scenario = goods_issue_scenario
    source = await scenario.source()
    payload = {"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source}
    race_at_source()
    results = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_issue_client.post(BASE, headers=goods_issue_auth(), json=payload)
                for _ in range(2)
            )
        ),
        timeout=20,
    )
    assert sorted(result.status_code for result in results) == [201, 409]
    assert await scenario.scalar('SELECT count(*) FROM "PhieuXuat"') == 1
    assert await scenario.scalar('SELECT count(*) FROM "ChiTietPhieuXuat"') == 2
    assert await scenario.scalar('SELECT count(*) FROM "LichSuThaoTac"') == 1


@pytest.mark.parametrize("competitor", ["duyet", "tu_choi"])
async def test_uc35_uc36_gi_ac13_two_sessions_one_posting(
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
    competitor,
    race_at_source,
):
    created, pending, _ = await goods_issue_pending()
    headers = {**goods_issue_auth(1), "If-Match": pending.headers["etag"]}
    path = created.headers["location"]
    race_at_source()
    results = await asyncio.gather(
        goods_issue_client.post(path + "/duyet", headers=headers, json={}),
        goods_issue_client.post(
            path + "/" + competitor,
            headers=headers,
            json={} if competitor == "duyet" else {"ly_do": "Competing rejection"},
        ),
    )
    if competitor == "duyet":
        assert [result.status_code for result in results] == [200, 200]
        assert sorted(result.json()["data"]["da_ghi_so_truoc_do"] for result in results) == [
            False,
            True,
        ]
    else:
        assert sorted(result.status_code for result in results) == [200, 412]
    scenario = goods_issue_scenario
    state = await scenario.scalar('SELECT trang_thai FROM "PhieuXuat"')
    expected_movements = 2 if state == "da_duyet" else 0
    assert (
        await scenario.scalar(
            'SELECT count(*) FROM "GiaoDichKho" WHERE chi_tiet_phieu_xuat_id IS NOT NULL'
        )
        == expected_movements
    )
    assert (
        await scenario.scalar(
            "SELECT count(*) FROM \"LichSuThaoTac\" WHERE thao_tac IN ('duyet','tu_choi')"
        )
        == 1
    )


@pytest.mark.parametrize(
    "failure",
    ["after_prices", "during_ledger", "after_inventory", "after_progress", "after_audit", "commit"],
)
async def test_uc35_uc38_gi_ac16_all_writes_rollback(
    goods_issue_database, goods_issue_scenario, goods_issue_pending, monkeypatch, failure
):
    created, pending, _ = await goods_issue_pending(
        kind="xuat_thanh_pham" if failure == "after_progress" else "xuat_linh_kien",
        production=7,
        available=3 if failure == "after_progress" else 0,
    )
    before = await goods_issue_scenario.snapshot()
    error = RuntimeError("intentional rollback verification")
    if failure == "during_ledger":

        def fail_ledger(_conn, _cursor, statement, _parameters, _context, _many):
            if 'INSERT INTO "GiaoDichKho"' in statement:
                raise error

        event.listen(goods_issue_database.engine.sync_engine, "before_cursor_execute", fail_ledger)
    elif failure == "commit":

        async def fail_commit(session):
            await session.flush()
            raise error

        monkeypatch.setattr(AsyncSession, "commit", fail_commit)
    else:
        owner, name = {
            "after_prices": (SqlAlchemyPhieuXuatRepository, "freeze_prices"),
            "after_inventory": (SqlAlchemyInventoryRepository, "issue_stock"),
            "after_progress": (SqlAlchemyPhieuXuatRepository, "update_progress"),
            "after_audit": (PhieuXuatService, "_audit"),
        }[failure]
        original = getattr(owner, name)

        async def fail_after(self, *args, **kwargs):
            await original(self, *args, **kwargs)
            raise error

        monkeypatch.setattr(owner, name, fail_after)
    try:
        async with goods_issue_database.sessions() as session:
            with pytest.raises(RuntimeError, match="intentional rollback verification"):
                await issue_service(session).approve(
                    created.json()["data"]["id"], MANAGER, pending.headers["etag"], "rollback-test"
                )
    finally:
        if failure == "during_ledger":
            event.remove(
                goods_issue_database.engine.sync_engine, "before_cursor_execute", fail_ledger
            )
        monkeypatch.undo()
    assert await goods_issue_scenario.snapshot() == before


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_hold",
        "held_mismatch",
        "ledger_mismatch",
        "wrong_source",
        "overflow",
        "changed_line",
        "null_price_pair",
    ],
)
async def test_uc35_gi_ac15_17_inconsistent_data_rejected(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending, corruption
):
    scenario = goods_issue_scenario
    created, pending, source = await goods_issue_pending()
    item = scenario.component_ids[0]
    if corruption == "missing_hold":
        await scenario.sql(
            """UPDATE "GiuHang" SET trang_thai='da_tra',ket_thuc_at=now() WHERE yeu_cau_san_xuat_id=:id""",
            id=source,
        )
        await scenario.sql('UPDATE "MatHang" SET so_luong_dang_giu=0')
    elif corruption == "held_mismatch":
        await scenario.sql(
            'UPDATE "MatHang" SET so_luong_dang_giu=so_luong_dang_giu+1 WHERE id=:id', id=item
        )
    elif corruption == "ledger_mismatch":
        await scenario.sql('UPDATE "MatHang" SET so_luong_ton=so_luong_ton+1 WHERE id=:id', id=item)
    elif corruption == "wrong_source":
        other = await scenario.source()
        await scenario.sql(
            'UPDATE "GiuHang" SET yeu_cau_san_xuat_id=:other WHERE yeu_cau_san_xuat_id=:id',
            other=other,
            id=source,
        )
    elif corruption == "overflow":
        await scenario.sql('UPDATE "MatHang" SET don_gia=9223372036854775807 WHERE id=:id', id=item)
    elif corruption == "null_price_pair":
        # SQL three-valued CHECK accepts this pair; the service must reject it.
        await scenario.sql(
            'UPDATE "ChiTietPhieuXuat" SET don_gia_thuc=0 WHERE phieu_xuat_id=:id',
            id=created.json()["data"]["id"],
        )
        pending = await goods_issue_client.get(
            created.headers["location"], headers=goods_issue_auth()
        )
    else:
        await scenario.sql(
            'UPDATE "ChiTietPhieuXuat" SET so_luong=1 WHERE phieu_xuat_id=:id AND mat_hang_id=:item',
            id=created.json()["data"]["id"],
            item=item,
        )
        # Use the current representation so this tests demand policy rather than stale ETag.
        pending = await goods_issue_client.get(
            created.headers["location"], headers=goods_issue_auth()
        )
    before = await scenario.snapshot()
    result = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert result.status_code == 409, result.text
    assert await scenario.snapshot() == before


async def test_uc35_gi_ac15_other_request_reservations_untouched(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    scenario = goods_issue_scenario
    created, pending, _ = await goods_issue_pending()
    other = await scenario.source(production=2, assigned=3)
    for item, quantity in zip(scenario.component_ids, (2, 4), strict=True):
        await scenario.hold(other, item, quantity)
    held_before = await scenario.sql(
        'SELECT * FROM "GiuHang" WHERE yeu_cau_san_xuat_id=:id ORDER BY id', id=other
    )
    approved = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert approved.status_code == 200, approved.text
    assert (
        await scenario.sql(
            'SELECT * FROM "GiuHang" WHERE yeu_cau_san_xuat_id=:id ORDER BY id', id=other
        )
        == held_before
    )
    assert [
        row["so_luong_dang_giu"]
        for row in await scenario.sql('SELECT * FROM "MatHang" ORDER BY id')
    ] == [2, 4, 0]


@pytest.mark.parametrize("case", ["nhap_kho", "unapproved", "not_started", "no_production"])
async def test_uc34_uc37_gi_ac05_source_eligibility(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, case
):
    scenario = goods_issue_scenario
    source = await scenario.source(
        production=0 if case == "no_production" else 7,
        available=10 if case == "no_production" else 0,
        kind="nhap_kho" if case == "nhap_kho" else "xuat_giao",
        state="da_gui" if case == "not_started" else "dang_thuc_hien",
    )
    if case == "unapproved":
        await scenario.completion(source, 7, state="cho_duyet")
    before = await scenario.snapshot()
    result = await goods_issue_client.post(
        BASE,
        headers=goods_issue_auth(),
        json={
            "loai_phieu": "xuat_linh_kien" if case == "no_production" else "xuat_thanh_pham",
            "yeu_cau_san_xuat_id": source,
        },
    )
    assert result.status_code == 409, result.text
    assert await scenario.snapshot() == before


async def test_uc34_uc35_gi_ac21_22_internal_cancel_ports(
    goods_issue_database,
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
):
    scenario = goods_issue_scenario
    created, pending, source = await goods_issue_pending()
    # UC-28 D2: cổng hủy chỉ nhận yeu_cau_san_xuat_id (bỏ lenh_ids di sản v3).
    async with goods_issue_database.sessions() as session:
        service = issue_service(session)
        assert not await service.co_phieu_da_ghi_so(source)
        await service.huy_phieu_chua_ghi_so(source, "Caller cancellation reason", 1)
        await session.commit()
    data = (
        await goods_issue_client.get(created.headers["location"], headers=goods_issue_auth())
    ).json()["data"]
    assert data["trang_thai"] == "tu_choi" and data["ly_do_tu_choi"] == "Yêu cầu đã hủy"
    await scenario.sql(
        """UPDATE "YeuCauSanXuat" SET trang_thai='da_huy', huy_at=now(),nguoi_huy_id=1,ly_do_huy='Canceled' WHERE id=:id""",
        id=source,
    )
    assert (
        await goods_issue_client.post(
            created.headers["location"] + "/gui",
            headers={
                **goods_issue_auth(),
                "If-Match": (
                    await goods_issue_client.get(
                        created.headers["location"], headers=goods_issue_auth()
                    )
                ).headers["etag"],
            },
            json={},
        )
    ).status_code == 409
    assert (
        await goods_issue_client.post(
            BASE,
            headers=goods_issue_auth(),
            json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source},
        )
    ).status_code == 409
    # A separate draft can be deleted internally; its code remains reserved by audit history.
    new_source = await scenario.source()
    draft = await goods_issue_client.post(
        BASE,
        headers=goods_issue_auth(),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": new_source},
    )
    code = draft.json()["data"]["ma_phieu_xuat"]
    async with goods_issue_database.sessions() as session:
        await issue_service(session).huy_phieu_chua_ghi_so(new_source, "Delete draft", 1)
        await session.commit()
    assert (
        await goods_issue_client.get(draft.headers["location"], headers=goods_issue_auth())
    ).status_code == 404
    recreated = await goods_issue_client.post(
        BASE,
        headers=goods_issue_auth(),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": new_source},
    )
    assert recreated.status_code == 201 and recreated.json()["data"]["ma_phieu_xuat"] > code
    approved_created, approved_pending, approved_source = await goods_issue_pending()
    result = await goods_issue_client.post(
        approved_created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": approved_pending.headers["etag"]},
        json={},
    )
    assert result.status_code == 200
    before = await scenario.snapshot()
    async with goods_issue_database.sessions() as session:
        service = issue_service(session)
        assert await service.co_phieu_da_ghi_so(approved_source)
        with pytest.raises(PostedProductionDependency):
            await service.huy_phieu_chua_ghi_so(approved_source, "No cancellation", 1)
        await session.rollback()
    assert await scenario.snapshot() == before


async def test_uc40_gi_ac18_19_filter_dates_ties_and_readonly(
    goods_issue_database,
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
):
    scenario = goods_issue_scenario
    records = []
    for _ in range(3):
        created, _, source = await goods_issue_pending()
        records.append((created.json()["data"]["id"], source))
    tie = datetime(2026, 11, 13, 17, 0, tzinfo=timezone.utc)  # 14/11 00:00 in VN
    await scenario.sql('UPDATE "PhieuXuat" SET created_at=:at', at=tie)
    await scenario.sql(
        'UPDATE "PhieuXuat" SET created_at=:at WHERE id=:id',
        at=datetime(2026, 11, 14, 17, tzinfo=timezone.utc),
        id=records[-1][0],
    )
    writes = []

    def observe(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)

    event.listen(goods_issue_database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        ids = []
        for page in (1, 2):
            response = await goods_issue_client.get(
                BASE
                + f"?tu_ngay=2026-11-14&den_ngay=2026-11-14&page_size=1&page={page}&sort=-created_at",
                headers=goods_issue_auth(1),
            )
            assert response.status_code == 200
            assert response.json()["meta"]["total"] == 2
            ids.extend(row["id"] for row in response.json()["data"])
        assert ids == [record[0] for record in records[:2]]
        filtered = await goods_issue_client.get(
            BASE + f"?yeu_cau_san_xuat_id={records[0][1]}&trang_thai=cho_duyet&nhan_vien_id=2",
            headers=goods_issue_auth(1),
        )
        assert filtered.json()["meta"]["total"] == 1
        assert (await goods_issue_client.get(BASE + "?q=_", headers=goods_issue_auth(1))).json()[
            "data"
        ] == []
        assert (
            await goods_issue_client.get(BASE + f"/{records[0][0]}", headers=goods_issue_auth())
        ).status_code == 200
        assert writes == []
    finally:
        event.remove(goods_issue_database.engine.sync_engine, "before_cursor_execute", observe)


async def test_uc34_gi_ac21_mapping_matches_actual_bootstrap(goods_issue_database):
    def check(connection):
        inspector = inspect(connection)
        for model in (PhieuXuat, ChiTietPhieuXuat, LichSuThaoTac):
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
                    actual = reflected["default"].replace("::character varying", "").strip("()")
                    expected = str(column.server_default.arg).strip("()")
                    assert actual == expected
            assert set(inspector.get_pk_constraint(table.name)["constrained_columns"]) == {
                c.name for c in table.primary_key
            }
            checks = {row["name"] for row in inspector.get_check_constraints(table.name)}
            assert checks == {
                constraint.name
                for constraint in table.constraints
                if constraint.__class__.__name__ == "CheckConstraint"
            }
            indexes = {row["name"]: row for row in inspector.get_indexes(table.name)}
            for index in table.indexes:
                assert indexes[index.name]["unique"] == index.unique
                assert indexes[index.name]["column_names"] == [
                    column.name for column in index.columns
                ]
            fks = inspector.get_foreign_keys(table.name)
            assert len(fks) == len(table.foreign_keys)
            for fk in table.foreign_keys:
                actual = next(row for row in fks if row["constrained_columns"] == [fk.parent.name])
                assert actual["referred_table"] == fk.column.table.name
                assert actual["options"].get("deferrable") is True
                # PostgreSQL omits the default INITIALLY IMMEDIATE from reflected options.
                assert actual["options"].get("initially", "IMMEDIATE") == "IMMEDIATE"

    async with goods_issue_database.engine.connect() as connection:
        await connection.run_sync(check)


async def test_uc34_gi_ac21_code_exhaustion_rollback(
    goods_issue_client, goods_issue_auth, goods_issue_scenario
):
    scenario = goods_issue_scenario
    source = await scenario.source()
    await scenario.sql(
        """INSERT INTO "LichSuThaoTac" (nhan_vien_id,loai_doi_tuong,doi_tuong_id,thao_tac,du_lieu_sau) VALUES (1,'phieu_xuat',999,'tao',jsonb_build_object('ma_phieu_xuat','PX-' || to_char(now() AT TIME ZONE 'Asia/Ho_Chi_Minh','YYYYMM') || '-999999'))"""
    )
    before = await scenario.snapshot()
    result = await goods_issue_client.post(
        BASE,
        headers=goods_issue_auth(),
        json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source},
    )
    assert result.status_code == 409
    assert await scenario.snapshot() == before


async def test_uc35_gi_ac13_two_sources_share_items(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending, race_at_source
):
    first = await goods_issue_pending(production=25)
    second = await goods_issue_pending(production=25)
    race_at_source()
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_issue_client.post(
                    created.headers["location"] + "/duyet",
                    headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
                    json={},
                )
                for created, pending, _ in (first, second)
            )
        ),
        timeout=20,
    )
    assert [response.status_code for response in responses] == [200, 200]
    scenario = goods_issue_scenario
    assert [
        (row["so_luong_ton"], row["so_luong_dang_giu"])
        for row in await scenario.sql('SELECT * FROM "MatHang" ORDER BY id')
    ] == [(50, 0), (0, 0), (100, 0)]
    assert (
        await scenario.scalar(
            'SELECT count(*) FROM "GiaoDichKho" WHERE chi_tiet_phieu_xuat_id IS NOT NULL'
        )
        == 4
    )


async def test_uc35_gi_ac14_replay_validates_format_and_performs_no_write(
    goods_issue_database,
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
):
    created, pending, _ = await goods_issue_pending()
    path = created.headers["location"] + "/duyet"
    approved = await goods_issue_client.post(
        path, headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]}, json={}
    )
    assert approved.status_code == 200
    writes = []

    def observe(_conn, _cursor, statement, _params, _context, _many):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement)

    event.listen(goods_issue_database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        for tag, expected in (
            (None, 428),
            ("*", 412),
            ("W/" + pending.headers["etag"], 412),
            (created.headers["etag"], 200),
        ):
            response = await goods_issue_client.post(
                path, headers={**goods_issue_auth(1), **({"If-Match": tag} if tag else {})}, json={}
            )
            assert response.status_code == expected
        assert writes == []
    finally:
        event.remove(goods_issue_database.engine.sync_engine, "before_cursor_execute", observe)


async def test_uc35_gi_ac14_incomplete_posting_is_not_repaired(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    created, pending, _ = await goods_issue_pending()
    scenario = goods_issue_scenario
    issue_id = created.json()["data"]["id"]
    # Valid SQL constraints do not imply a complete posting. Simulate an old broken write.
    await scenario.sql(
        'UPDATE "ChiTietPhieuXuat" SET don_gia_thuc=1,tong_gia=so_luong WHERE phieu_xuat_id=:id',
        id=issue_id,
    )
    await scenario.sql(
        """UPDATE "PhieuXuat" SET trang_thai='da_duyet',tong_tien=21,nguoi_xu_ly_id=1,xu_ly_at=now() WHERE id=:id""",
        id=issue_id,
    )
    before = await scenario.snapshot()
    response = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert response.status_code == 409
    assert await scenario.snapshot() == before


async def test_uc37_gi_ac20_inactive_output_before_creation(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    scenario = goods_issue_scenario
    source = await scenario.source(production=0, available=10)
    await scenario.hold(source, scenario.output_id, 10, "thanh_pham_co_san")
    await scenario.sql('UPDATE "MatHang" SET is_active=false WHERE id=:id', id=scenario.output_id)
    created, pending, _ = await goods_issue_pending(kind="xuat_thanh_pham", source=source)
    response = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert response.status_code == 200, response.text


async def test_uc34_gi_ac21_concurrent_codes_different_sources(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, race_at_source
):
    scenario = goods_issue_scenario
    sources = [await scenario.source(), await scenario.source()]
    race_at_source()
    responses = await asyncio.wait_for(
        asyncio.gather(
            *(
                goods_issue_client.post(
                    BASE,
                    headers=goods_issue_auth(),
                    json={"loai_phieu": "xuat_linh_kien", "yeu_cau_san_xuat_id": source},
                )
                for source in sources
            )
        ),
        timeout=20,
    )
    assert [response.status_code for response in responses] == [201, 201]
    assert len({response.json()["data"]["id"] for response in responses}) == 2
    codes = sorted(response.json()["data"]["ma_phieu_xuat"] for response in responses)
    assert [code[-6:] for code in codes] == ["000001", "000002"]


async def test_uc37_gi_ac15_wrong_completion_reservation_rollback(
    goods_issue_client, goods_issue_auth, goods_issue_scenario, goods_issue_pending
):
    scenario = goods_issue_scenario
    created, pending, source = await goods_issue_pending(
        kind="xuat_thanh_pham", production=7, available=3
    )
    other = await scenario.source(production=7)
    completion = await scenario.completion(other, 7)
    await scenario.sql(
        """UPDATE "GiuHang" SET chung_tu_hoan_thanh_sx_id=:completion WHERE yeu_cau_san_xuat_id=:id AND loai_giu='thanh_pham_san_xuat' """,
        completion=completion,
        id=source,
    )
    before = await scenario.snapshot()
    response = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert response.status_code == 409, response.text
    assert await scenario.snapshot() == before


@pytest.mark.parametrize("other_action", ["gui", "replay"])
async def test_uc36_gi_ac13_reject_vs_submit_or_replay(
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
    race_at_source,
    other_action,
):
    created, pending, _ = await goods_issue_pending()
    path = created.headers["location"]
    if other_action == "replay":
        approved = await goods_issue_client.post(
            path + "/duyet",
            headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
            json={},
        )
        assert approved.status_code == 200
        tag = approved.headers["etag"]
    else:
        tag = pending.headers["etag"]
    before = await goods_issue_scenario.snapshot()
    race_at_source()
    reject, other = await asyncio.wait_for(
        asyncio.gather(
            goods_issue_client.post(
                path + "/tu_choi",
                headers={**goods_issue_auth(1), "If-Match": tag},
                json={"ly_do": "Race"},
            ),
            goods_issue_client.post(
                path + ("/gui" if other_action == "gui" else "/duyet"),
                headers={**goods_issue_auth(2 if other_action == "gui" else 1), "If-Match": tag},
                json={},
            ),
        ),
        timeout=20,
    )
    if other_action == "gui":
        assert reject.status_code == 200 and other.status_code in {409, 412}
    else:
        assert reject.status_code == 409 and other.status_code == 200
        assert await goods_issue_scenario.snapshot() == before


async def test_uc35_gi_ac21_posted_rows_and_history_immutable(
    goods_issue_database,
    goods_issue_client,
    goods_issue_auth,
    goods_issue_scenario,
    goods_issue_pending,
):
    from sqlalchemy.exc import DBAPIError

    created, pending, source = await goods_issue_pending()
    approved = await goods_issue_client.post(
        created.headers["location"] + "/duyet",
        headers={**goods_issue_auth(1), "If-Match": pending.headers["etag"]},
        json={},
    )
    assert approved.status_code == 200
    before = await goods_issue_scenario.snapshot()
    for statement in (
        'UPDATE "PhieuXuat" SET tong_tien=0',
        'DELETE FROM "ChiTietPhieuXuat"',
        'UPDATE "GiaoDichKho" SET so_luong_ton_sau=0',
        'DELETE FROM "LichSuThaoTac"',
        'UPDATE "NhuCauLinhKien" SET so_luong_can=1',
        'UPDATE "MatHang" SET so_luong_ton=0,so_luong_dang_giu=1',
    ):
        async with goods_issue_database.sessions() as session:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement))
            await session.rollback()
    assert await goods_issue_scenario.snapshot() == before


async def test_uc35_gi_ac22_internal_cancel_joins_parent_rollback(
    goods_issue_database, goods_issue_scenario, goods_issue_pending
):
    _, _, source = await goods_issue_pending()
    before = await goods_issue_scenario.snapshot()
    async with goods_issue_database.sessions() as session:
        await issue_service(session).huy_phieu_chua_ghi_so(source, "Parent rollback", 1)
        await session.flush()
        await session.rollback()
    assert await goods_issue_scenario.snapshot() == before
