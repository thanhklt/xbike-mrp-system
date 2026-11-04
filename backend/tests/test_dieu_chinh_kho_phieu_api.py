"""Warehouse adjustment contract v3 on real bootstrap/seed in disposable PostgreSQL schemas."""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.main import app
from app.modules.dieu_chinh_kho.models import ChiTietPhieuDieuChinhKho, PhieuDieuChinhKho
from app.modules.dieu_chinh_kho.repository import SqlAlchemyPhieuDieuChinhRepository
from app.modules.dieu_chinh_kho.service import PhieuDieuChinhKhoService

BASE = "/api/v1/phieu_dieu_chinh_kho"


@pytest.fixture
async def adjustment_context():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL TEST_DATABASE_URL")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must end in _test")
    schema = "adjustment_api_" + uuid4().hex
    engine = create_async_engine(
        url,
        hide_parameters=True,
        connect_args={
            "server_settings": {
                "search_path": schema + ",pg_catalog",
                "lock_timeout": "5000",
                "statement_timeout": "10000",
            }
        },
    )
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    previous_overrides = dict(app.dependency_overrides)
    try:
        async with engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            raw = await connection.get_raw_connection()
            for name in ("init.sql", "seed.sql"):
                source = (Path(__file__).resolve().parents[2] / "infra/postgres" / name).read_text(
                    encoding="utf-8"
                )
                source = (
                    source.replace("BEGIN;", "", 1)
                    .rsplit("COMMIT;", 1)[0]
                    .replace("public", schema)
                )
                await raw.driver_connection.execute(source)
            await connection.execute(
                text("""INSERT INTO "NhanVien"
                    (id,vai_tro_id,ten_dang_nhap,ma_nhan_vien,mat_khau)
                    SELECT 4,2,'ticket_manager2','NV-000004',mat_khau
                    FROM "NhanVien" WHERE id=2""")
            )
            password_hash = await connection.scalar(
                text('SELECT mat_khau FROM "NhanVien" WHERE id=2')
            )

        async def test_db():
            async with sessions() as session:
                yield session

        app.dependency_overrides[get_db] = test_db

        def headers(employee=2, roles=None, *, expires_delta=None):
            current_role = {1: "quan_tri_vien", 2: "quan_ly", 3: "nhan_vien", 4: "quan_ly"}.get(
                employee, "quan_ly"
            )
            token = create_access_token(
                employee,
                roles=roles or [current_role],
                expires_delta=expires_delta,
                credential_version=password_version(password_hash),
            )
            return {"Authorization": "Bearer " + token}

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            yield client, sessions, headers, engine
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


def proposal(quantity=900, **changes):
    return {
        "phieu_nhap_id": 1,
        "ly_do": "Đối chiếu lại số lượng",
        "chi_tiet": [{"giao_dich_goc_id": 12, "so_luong_dung": quantity}],
        **changes,
    }


async def create_phieu(context, quantity=900, **changes):
    client, _, headers, _ = context
    response = await client.post(BASE, headers=headers(), json=proposal(quantity, **changes))
    assert response.status_code == 201, response.text
    return response


async def confirm(context, created, **changes):
    client, _, headers, _ = context
    return await client.post(
        f"{BASE}/{created.json()['data']['id']}/xac_nhan",
        headers={**headers(), "If-Match": created.headers["etag"], **changes},
        json={},
    )


async def snapshot(sessions):
    async with sessions() as db:
        return {
            table: await db.scalar(
                text(f'SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM "{table}" r')
            )
            for table in (
                "MatHang",
                "GiaoDichKho",
                "TicketLoiDieuChinh",
                "ChiTietTicketLoiDieuChinh",
            )
        }


async def audits(sessions, phieu_id):
    async with sessions() as db:
        return (
            await db.execute(
                text("""SELECT thao_tac, du_lieu_truoc, du_lieu_sau FROM "LichSuThaoTac"
            WHERE loai_doi_tuong='phieu_dieu_chinh_kho' AND doi_tuong_id=:id ORDER BY id"""),
                {"id": phieu_id},
            )
        ).all()


def test_openapi_six_adjustment_operations():
    paths = app.openapi()["paths"]
    actual = {
        (method, path)
        for path, operations in paths.items()
        if path.startswith(BASE)
        for method in operations
    }
    assert actual == {
        ("get", BASE),
        ("post", BASE),
        ("get", BASE + "/{id}"),
        ("patch", BASE + "/{id}"),
        ("delete", BASE + "/{id}"),
        ("post", BASE + "/{id}/xac_nhan"),
    }
    assert (
        sum(
            len(operations)
            for path, operations in paths.items()
            if path.startswith("/api/v1/ticket_loi_dieu_chinh")
        )
        == 4
    )


async def test_create_computes_effective_quantity_and_delta(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    baseline = await snapshot(sessions)
    created = await create_phieu(adjustment_context, ly_do="  Đối chiếu  ")
    record = created.json()["data"]
    assert record["trang_thai"] == "nhap" and record["confirmed_at"] is None
    assert record["ly_do"] == "Đối chiếu" and record["nhan_vien_id"] == 2
    assert record["ma_phieu"].startswith("DCK-") and record["ma_phieu"].endswith(
        f"-{record['id']:06d}"
    )
    assert record["created_at"].endswith("Z")
    assert created.headers["location"] == f"{BASE}/{record['id']}"
    assert record["chi_tiet"][0] == {
        "id": record["chi_tiet"][0]["id"],
        "giao_dich_goc_id": 12,
        "mat_hang_id": 17,
        "so_luong_hieu_luc_truoc": 985,
        "so_luong_dung": 900,
        "so_luong_bien_dong": -85,
    }
    read = await client.get(created.headers["location"], headers=headers())
    assert read.status_code == 200 and read.headers["etag"] == created.headers["etag"]
    assert await snapshot(sessions) == baseline
    assert [row[0] for row in await audits(sessions, record["id"])] == ["tao"]


@pytest.mark.parametrize(
    "body,status",
    [
        ({}, 422),
        (proposal(ly_do=""), 422),
        (proposal(ly_do="   "), 422),
        (proposal(chi_tiet=[]), 422),
        (proposal(chi_tiet=[{"giao_dich_goc_id": 12, "so_luong_dung": 900}] * 2), 422),
        *[(proposal(quantity), 422) for quantity in (-1, 1.0, "1", True, 2**31, None)],
        (proposal(extra=1), 422),
        (proposal(985), 422),
        (proposal(chi_tiet=[{"giao_dich_goc_id": 13, "so_luong_dung": 900}]), 422),
        (proposal(chi_tiet=[{"giao_dich_goc_id": 999, "so_luong_dung": 900}]), 422),
        (proposal(phieu_nhap_id=999), 404),
        (proposal(phieu_nhap_id=2), 409),
        (proposal(phieu_nhap_id="1"), 422),
        (proposal(phieu_nhap_id=True), 422),
        (proposal(chi_tiet=[{"giao_dich_goc_id": True, "so_luong_dung": 900}]), 422),
        (
            proposal(chi_tiet=[{"giao_dich_goc_id": 12, "so_luong_dung": 900, "mat_hang_id": 17}]),
            422,
        ),
    ],
)
async def test_create_validation(adjustment_context, body, status):
    client, sessions, headers, _ = adjustment_context
    before = await snapshot(sessions)
    response = await client.post(BASE, headers=headers(), json=body)
    assert response.status_code == status, response.text
    assert "error" in response.json()
    assert await snapshot(sessions) == before
    if body == proposal(985):
        assert response.json()["error"]["details"][0]["field"] == "chi_tiet[0].so_luong_dung"


async def test_patch_delete_only_draft_with_if_match(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    url = created.headers["location"]
    initial = created.headers["etag"]
    for token, status in [(None, 428), ("", 428), ("*", 412), ('W/"x"', 412), ('"old"', 412)]:
        request_headers = {**headers(), **({"If-Match": token} if token is not None else {})}
        for method, kwargs in [("patch", {"json": {}}), ("delete", {}), ("post", {"json": {}})]:
            response = await client.request(
                method,
                url + ("/xac_nhan" if method == "post" else ""),
                headers=request_headers,
                **kwargs,
            )
            assert response.status_code == status, response.text
    for payload in ({"phieu_nhap_id": 1}, {"ly_do": None}, {"chi_tiet": None}, {"chi_tiet": []}):
        response = await client.patch(url, headers={**headers(), "If-Match": initial}, json=payload)
        assert response.status_code == 422, response.text
    noop = await client.patch(url, headers={**headers(), "If-Match": initial}, json={})
    assert noop.status_code == 200 and noop.headers["etag"] == initial
    assert len(await audits(sessions, created.json()["data"]["id"])) == 1
    patched = await client.patch(
        url,
        headers={**headers(), "If-Match": initial},
        json={"ly_do": "Sửa", "chi_tiet": [{"giao_dich_goc_id": 12, "so_luong_dung": 910}]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["chi_tiet"][0]["so_luong_bien_dong"] == -75
    assert patched.headers["etag"] != initial
    stale = await client.delete(url, headers={**headers(), "If-Match": initial})
    assert stale.status_code == 412
    deleted = await client.delete(url, headers={**headers(), "If-Match": patched.headers["etag"]})
    assert deleted.status_code == 204 and deleted.content == b""
    assert (await client.get(url, headers=headers())).status_code == 404
    assert [row[0] for row in await audits(sessions, created.json()["data"]["id"])] == [
        "tao",
        "sua",
        "xoa_nhap",
    ]


async def test_confirm_posts_ledger_and_balance(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    posted = await confirm(adjustment_context, created)
    assert posted.status_code == 200, posted.text
    record = posted.json()["data"]
    assert record["trang_thai"] == "da_xac_nhan" and record["confirmed_at"].endswith("Z")
    assert record["da_ghi_so_truoc_do"] is False and len(record["giao_dich_kho_ids"]) == 1
    async with sessions() as db:
        assert await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=17')) == 180
        assert (
            await db.scalar(
                text('SELECT sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id=17')
            )
            == 180
        )
        movement = (
            await db.execute(
                text(
                    'SELECT loai_giao_dich, so_luong_bien_dong, nhan_vien_id FROM "GiaoDichKho" WHERE id=:id'
                ),
                {"id": record["giao_dich_kho_ids"][0]},
            )
        ).one()
        assert tuple(movement) == ("dieu_chinh_ton_kho", -85, 2)
    assert [row[0] for row in await audits(sessions, record["id"])] == ["tao", "xac_nhan"]
    next_phieu = await create_phieu(adjustment_context, 910)
    assert next_phieu.json()["data"]["chi_tiet"][0]["so_luong_hieu_luc_truoc"] == 900
    read = await client.get(created.headers["location"], headers=headers())
    assert read.headers["etag"] == posted.headers["etag"]
    for method in ("patch", "delete"):
        denied = await client.request(
            method,
            created.headers["location"],
            headers={**headers(), "If-Match": posted.headers["etag"]},
            **({"json": {}} if method == "patch" else {}),
        )
        assert denied.status_code == 409


@pytest.mark.parametrize("token", [None, "", "*", 'W/"x"', '"old"'])
async def test_confirm_replay_ignores_if_match(adjustment_context, token):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    posted = await confirm(adjustment_context, created)
    assert posted.status_code == 200, posted.text
    baseline = await snapshot(sessions)
    history = await audits(sessions, created.json()["data"]["id"])
    replay = await client.post(
        created.headers["location"] + "/xac_nhan",
        headers={**headers(), **({"If-Match": token} if token is not None else {})},
        json={},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["da_ghi_so_truoc_do"] is True
    assert replay.json()["data"]["giao_dich_kho_ids"] == posted.json()["data"]["giao_dich_kho_ids"]
    assert replay.headers["etag"] == posted.headers["etag"]
    assert await snapshot(sessions) == baseline
    assert await audits(sessions, created.json()["data"]["id"]) == history


async def test_confirm_stock_shortage_marks_loi_and_creates_one_ticket(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context, 200)
    baseline = await snapshot(sessions)
    response = await confirm(adjustment_context, created)
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "dieu_chinh_khong_hop_le"
    assert error["details"] == [
        {"mat_hang_id": 17, "so_luong_bien_dong": -785, "ton_hien_tai": 265}
    ]
    phieu_id = created.json()["data"]["id"]
    assert error["phieu_dieu_chinh_kho_id"] == phieu_id
    assert error["trang_thai_phieu"] == "loi" and error["ticket_da_luu"] is True
    after = await snapshot(sessions)
    for table in ("MatHang", "GiaoDichKho"):
        assert after[table] == baseline[table]
    assert len(after["TicketLoiDieuChinh"]) == len(baseline["TicketLoiDieuChinh"]) + 1
    ticket = await client.get(
        f"/api/v1/ticket_loi_dieu_chinh/{error['ticket_id']}", headers=headers()
    )
    assert ticket.status_code == 200, ticket.text
    value = ticket.json()["data"]
    assert (
        value["trang_thai"] == "cho_xu_ly"
        and value["phieu_nhap_id"] == 1
        and value["nguoi_tao_id"] == 2
    )
    assert value["ma_ticket"].endswith(f"-{value['id']:06d}")
    assert (
        value["chi_tiet"][0]["so_luong_de_nghi"] == 200
        and value["chi_tiet"][0]["ton_kho_tai_thoi_diem"] == 265
    )
    assert [row[0] for row in await audits(sessions, phieu_id)] == ["tao", "ghi_nhan_loi"]
    async with sessions() as db:
        assert (
            await db.scalar(
                text(
                    """SELECT count(*) FROM "LichSuThaoTac" WHERE loai_doi_tuong='ticket_loi_dieu_chinh' AND doi_tuong_id=:id AND thao_tac='ghi_nhan_loi' """
                ),
                {"id": value["id"]},
            )
            == 1
        )
    failed = await client.get(created.headers["location"], headers=headers())
    assert (
        failed.json()["data"]["trang_thai"] == "loi"
        and failed.json()["data"]["confirmed_at"] is None
    )
    for method in ("post", "patch", "delete"):
        retry = await client.request(
            method,
            created.headers["location"] + ("/xac_nhan" if method == "post" else ""),
            headers={**headers(), "If-Match": failed.headers["etag"]},
            **({"json": {}} if method != "delete" else {}),
        )
        assert (
            retry.status_code == 409 and retry.json()["error"]["code"] == "trang_thai_khong_hop_le"
        ), retry.text
    assert await snapshot(sessions) == after


async def test_non_shortage_failures_create_no_ticket(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    first = await create_phieu(adjustment_context)
    second = await create_phieu(adjustment_context)
    assert (await confirm(adjustment_context, first)).status_code == 200
    baseline = await snapshot(sessions)
    failure = await confirm(adjustment_context, second)
    assert failure.status_code == 422, failure.text
    assert await snapshot(sessions) == baseline
    current = await client.get(second.headers["location"], headers=headers())
    assert (
        current.json()["data"]["trang_thai"] == "nhap"
        and current.headers["etag"] == second.headers["etag"]
    )


@pytest.mark.parametrize("second_quantity", [900, 910])
async def test_concurrent_confirms_same_source_serialize(adjustment_context, second_quantity):
    _, sessions, _, _ = adjustment_context
    first = await create_phieu(adjustment_context)
    second = await create_phieu(adjustment_context, second_quantity)
    results = await asyncio.gather(
        confirm(adjustment_context, first), confirm(adjustment_context, second)
    )
    assert sorted(result.status_code for result in results) == (
        [200, 422] if second_quantity == 900 else [200, 200]
    ), [r.text for r in results]
    async with sessions() as db:
        balance = await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=17'))
        assert balance >= 0 and balance == await db.scalar(
            text('SELECT sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id=17')
        )


async def test_reads_do_not_wait_for_confirm_lock(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    async with sessions() as locking:
        try:
            await locking.execute(text('SELECT id FROM "PhieuNhap" WHERE id=1 FOR UPDATE'))
            await locking.execute(
                text('SELECT id FROM "PhieuDieuChinhKho" WHERE id=:id FOR UPDATE'),
                {"id": created.json()["data"]["id"]},
            )
            for url in (created.headers["location"], BASE):
                read = await asyncio.wait_for(client.get(url, headers=headers()), 3)
                assert read.status_code == 200, read.text
        finally:
            await locking.rollback()


async def test_list_filters_sort_and_single_line_query(adjustment_context):
    client, _, headers, engine = adjustment_context
    first = await create_phieu(adjustment_context, ly_do="100%_sửa")
    await create_phieu(adjustment_context, 910)
    statements = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if '"ChiTietPhieuDieuChinhKho"' in statement:
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        listing = await client.get(
            BASE,
            headers=headers(),
            params={"trang_thai": "nhap", "phieu_nhap_id": 1, "nhan_vien_id": 2, "sort": "-id"},
        )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)
    assert listing.status_code == 200, listing.text
    assert len(statements) == 1 and "FOR SHARE" not in statements[0]
    ids = [r["id"] for r in listing.json()["data"]]
    assert ids == sorted(ids, reverse=True) and len(ids) == 2
    searched = await client.get(BASE, headers=headers(), params={"q": "%_"})
    assert [r["id"] for r in searched.json()["data"]] == [first.json()["data"]["id"]]
    day = datetime.fromisoformat(
        first.json()["data"]["created_at"].replace("Z", "+00:00")
    ) + timedelta(hours=7)
    dated = await client.get(
        BASE,
        headers=headers(),
        params={"tu_ngay": day.date().isoformat(), "den_ngay": day.date().isoformat()},
    )
    assert dated.status_code == 200 and len(dated.json()["data"]) == 2
    empty = await client.get(BASE, headers=headers(), params={"page": 99999999999999999999})
    assert empty.status_code == 200 and empty.json()["data"] == []
    for query in (
        "page=1&page=2",
        "x=1",
        "sort=ly_do",
        "trang_thai=da_duyet",
        "tu_ngay=2026-11-05&den_ngay=2026-11-01",
        "tu_ngay=2026-11-01T00:00:00",
        "den_ngay=9999-12-31",
    ):
        bad = await client.get(BASE + "?" + query, headers=headers())
        assert bad.status_code == 422, bad.text


@pytest.mark.parametrize("employee,status", [(None, 401), (1, 403), (3, 403)])
async def test_roles(adjustment_context, employee, status):
    client, _, headers, _ = adjustment_context
    auth = headers(employee) if employee is not None else {}
    for method, url, body in [
        ("get", BASE, None),
        ("get", BASE + "/1", None),
        ("post", BASE, proposal()),
        ("patch", BASE + "/1", {}),
        ("delete", BASE + "/1", None),
        ("post", BASE + "/1/xac_nhan", {}),
    ]:
        response = await client.request(
            method, url, headers=auth, **({"json": body} if body is not None else {})
        )
        assert response.status_code == status, response.text


async def test_locked_account_is_forbidden(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    async with sessions.begin() as db:
        await db.execute(text("""UPDATE "NhanVien" SET trang_thai='bi_khoa' WHERE id=2"""))
    for method, url, body in [
        ("get", BASE, None),
        ("get", BASE + "/1", None),
        ("post", BASE, proposal()),
        ("patch", BASE + "/1", {}),
        ("delete", BASE + "/1", None),
        ("post", BASE + "/1/xac_nhan", {}),
    ]:
        response = await client.request(
            method, url, headers=headers(), **({"json": body} if body is not None else {})
        )
        assert response.status_code == 403, response.text


async def test_failure_in_ticket_transaction_does_not_claim_ticket(adjustment_context):
    client, sessions, headers, engine = adjustment_context
    created = await create_phieu(adjustment_context, 200)
    baseline = await snapshot(sessions)

    def fail_ticket(conn, cursor, statement, parameters, context, executemany):
        if 'INSERT INTO "TicketLoiDieuChinh"' in statement:
            raise RuntimeError("Injected ticket database failure")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_ticket)
    try:
        response = await confirm(adjustment_context, created)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail_ticket)
    assert response.status_code == 500, response.text
    assert response.json()["error"]["code"] == "loi_noi_bo"
    assert response.json()["error"].get("ticket_da_luu") is not True
    assert await snapshot(sessions) == baseline
    read = await client.get(created.headers["location"], headers=headers())
    assert (
        read.json()["data"]["trang_thai"] == "nhap"
        and read.headers["etag"] == created.headers["etag"]
    )


async def test_shortage_snapshots_every_line_and_recomputed_effective_quantity(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    failing = await create_phieu(
        adjustment_context,
        chi_tiet=[
            {"giao_dich_goc_id": 12, "so_luong_dung": 200},
            {"giao_dich_goc_id": 1, "so_luong_dung": 1001},
        ],
    )
    successful = await create_phieu(adjustment_context)
    assert (await confirm(adjustment_context, successful)).status_code == 200
    baseline = await snapshot(sessions)
    failure = await confirm(adjustment_context, failing)
    assert failure.status_code == 409, failure.text
    error = failure.json()["error"]
    assert error["details"] == [
        {"mat_hang_id": 17, "so_luong_bien_dong": -700, "ton_hien_tai": 180}
    ]
    after = await snapshot(sessions)
    assert (
        after["MatHang"] == baseline["MatHang"] and after["GiaoDichKho"] == baseline["GiaoDichKho"]
    )
    ticket = await client.get(
        f"/api/v1/ticket_loi_dieu_chinh/{error['ticket_id']}", headers=headers()
    )
    lines = ticket.json()["data"]["chi_tiet"]
    assert len(lines) == 2
    assert lines[0]["so_luong_hieu_luc_truoc"] == 900 and lines[0]["so_luong_bien_dong"] == -700
    assert lines[1]["so_luong_de_nghi"] == 1001
    async with sessions() as db:
        assert lines[1]["ton_kho_tai_thoi_diem"] == await db.scalar(
            text('SELECT so_luong_ton FROM "MatHang" WHERE id=:id'), {"id": lines[1]["mat_hang_id"]}
        )
    record = (await client.get(failing.headers["location"], headers=headers())).json()["data"]
    assert record["chi_tiet"][0]["so_luong_hieu_luc_truoc"] == 900


@pytest.mark.parametrize("intervening_confirmation", [False, True])
async def test_interleaving_between_inventory_rollback_and_ticket_transaction(
    adjustment_context, monkeypatch, intervening_confirmation
):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context, 200)
    baseline = await snapshot(sessions)
    original = PhieuDieuChinhKhoService._ghi_nhan_loi

    async def intervene(self, phieu_id, actor, checked_etag, lines, shortage, request_id):
        patch = (
            {"chi_tiet": [{"giao_dich_goc_id": 12, "so_luong_dung": 900}]}
            if intervening_confirmation
            else {"ly_do": "Đã sửa trong lúc rollback"}
        )
        patched = await client.patch(
            created.headers["location"],
            headers={**headers(), "If-Match": created.headers["etag"]},
            json=patch,
        )
        assert patched.status_code == 200, patched.text
        if intervening_confirmation:
            posted = await client.post(
                created.headers["location"] + "/xac_nhan",
                headers={**headers(), "If-Match": patched.headers["etag"]},
                json={},
            )
            assert posted.status_code == 200, posted.text
        return await original(self, phieu_id, actor, checked_etag, lines, shortage, request_id)

    monkeypatch.setattr(PhieuDieuChinhKhoService, "_ghi_nhan_loi", intervene)
    response = await confirm(adjustment_context, created)
    assert response.status_code == (200 if intervening_confirmation else 412), response.text
    if intervening_confirmation:
        assert response.json()["data"]["da_ghi_so_truoc_do"] is True
    after = await snapshot(sessions)
    assert after["TicketLoiDieuChinh"] == baseline["TicketLoiDieuChinh"]


async def test_concurrent_shortages_create_only_one_ticket(adjustment_context):
    _, sessions, _, _ = adjustment_context
    created = await create_phieu(adjustment_context, 200)
    baseline = await snapshot(sessions)
    results = await asyncio.gather(
        confirm(adjustment_context, created), confirm(adjustment_context, created)
    )
    assert all(result.status_code in (409, 412) for result in results), [r.text for r in results]
    assert sum(r.json()["error"].get("ticket_da_luu", False) for r in results) == 1
    after = await snapshot(sessions)
    assert len(after["TicketLoiDieuChinh"]) == len(baseline["TicketLoiDieuChinh"]) + 1
    assert (
        after["MatHang"] == baseline["MatHang"] and after["GiaoDichKho"] == baseline["GiaoDichKho"]
    )


async def test_inactive_item_can_be_adjusted(adjustment_context):
    _, sessions, _, _ = adjustment_context
    async with sessions.begin() as db:
        await db.execute(text('UPDATE "MatHang" SET is_active=false WHERE id=17'))
    created = await create_phieu(adjustment_context)
    posted = await confirm(adjustment_context, created)
    assert posted.status_code == 200, posted.text


async def test_source_from_another_receipt_is_rejected(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    async with sessions.begin() as db:
        await db.execute(text("""UPDATE "PhieuNhap" SET trang_thai='hoan_thanh' WHERE id=2"""))
    response = await client.post(BASE, headers=headers(), json=proposal(phieu_nhap_id=2))
    assert response.status_code == 422, response.text
    assert response.json()["error"]["details"][0]["field"] == "chi_tiet[0].giao_dich_goc_id"


async def test_read_snapshot_is_repeatable_and_read_only(adjustment_context):
    _, sessions, _, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    async with sessions() as db:
        repository = SqlAlchemyPhieuDieuChinhRepository(db)
        await repository.begin_read_snapshot()
        assert await db.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert await db.scalar(text("SHOW transaction_read_only")) == "on"
        initial = await repository.get_phieu(created.json()["data"]["id"])
        assert (await confirm(adjustment_context, created)).status_code == 200
        assert await repository.get_phieu(initial.id) == initial


async def test_stock_overflow_and_ledger_mismatch_do_not_create_ticket(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    async with sessions.begin() as db:
        receipt_id = await db.scalar(
            text("""INSERT INTO "PhieuNhap" (ma_phieu_nhap, nhan_vien_id, ncc_id, ngay_nhap)
            VALUES ('PN-202611-000099', 2, 1, current_date) RETURNING id""")
        )
        amount = 2**31 - 1 - 265
        detail_id = await db.scalar(
            text("""INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id,mat_hang_id,so_luong)
            VALUES (:pn,17,:amount) RETURNING id"""),
            {"pn": receipt_id, "amount": amount},
        )
        await db.execute(
            text("""UPDATE "PhieuNhap" SET trang_thai='hoan_thanh' WHERE id=:id"""),
            {"id": receipt_id},
        )
        await db.execute(
            text("""INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chi_tiet_phieu_nhap_id,nhan_vien_id)
            VALUES (17,'nhap_vat_tu',:amount,:detail,2)"""),
            {"amount": amount, "detail": detail_id},
        )
        await db.execute(
            text('UPDATE "MatHang" SET so_luong_ton=:amount WHERE id=17'), {"amount": 2**31 - 1}
        )
    created = await create_phieu(adjustment_context, 986)
    baseline = await snapshot(sessions)
    overflow = await confirm(adjustment_context, created)
    assert (
        overflow.status_code == 409 and overflow.json()["error"].get("ticket_da_luu") is not True
    ), overflow.text
    assert await snapshot(sessions) == baseline
    async with sessions.begin() as db:
        await db.execute(text('UPDATE "MatHang" SET so_luong_ton=100 WHERE id=17'))
    mismatch = await confirm(adjustment_context, created)
    assert (
        mismatch.status_code == 409 and mismatch.json()["error"].get("ticket_da_luu") is not True
    ), mismatch.text
    read = await client.get(created.headers["location"], headers=headers())
    assert (
        read.json()["data"]["trang_thai"] == "nhap"
        and read.headers["etag"] == created.headers["etag"]
    )
    assert (await snapshot(sessions))["TicketLoiDieuChinh"] == baseline["TicketLoiDieuChinh"]


async def test_ledger_database_failure_rolls_back_everything_without_ticket(adjustment_context):
    client, sessions, headers, engine = adjustment_context
    created = await create_phieu(adjustment_context)
    baseline = await snapshot(sessions)

    def fail_ledger(conn, cursor, statement, parameters, context, executemany):
        if 'INSERT INTO "GiaoDichKho"' in statement:
            raise RuntimeError("Injected ledger failure")

    event.listen(engine.sync_engine, "before_cursor_execute", fail_ledger)
    try:
        response = await confirm(adjustment_context, created)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail_ledger)
    assert response.status_code == 500, response.text
    assert response.json()["error"].get("ticket_da_luu") is not True
    assert await snapshot(sessions) == baseline
    read = await client.get(created.headers["location"], headers=headers())
    assert (
        read.headers["etag"] == created.headers["etag"]
        and read.json()["data"]["trang_thai"] == "nhap"
    )
    assert [row[0] for row in await audits(sessions, created.json()["data"]["id"])] == ["tao"]


async def test_patch_identical_details_is_noop(adjustment_context):
    client, sessions, headers, _ = adjustment_context
    created = await create_phieu(adjustment_context)
    patched = await client.patch(
        created.headers["location"],
        headers={**headers(), "If-Match": created.headers["etag"]},
        json={"ly_do": created.json()["data"]["ly_do"], "chi_tiet": proposal()["chi_tiet"]},
    )
    assert patched.status_code == 200 and patched.headers["etag"] == created.headers["etag"], (
        patched.text
    )
    assert patched.json()["data"] == created.json()["data"]
    assert [row[0] for row in await audits(sessions, created.json()["data"]["id"])] == ["tao"]


async def test_adjustment_orm_matches_bootstrap_columns_constraints_and_indexes(adjustment_context):
    _, _, _, engine = adjustment_context
    async with engine.connect() as db:
        for model in (PhieuDieuChinhKho, ChiTietPhieuDieuChinhKho):

            def metadata(connection, model=model):
                inspector = inspect(connection)
                name = model.__tablename__
                return (
                    inspector.get_columns(name),
                    inspector.get_foreign_keys(name),
                    inspector.get_check_constraints(name),
                    inspector.get_indexes(name),
                )

            columns, keys, checks, indexes = await db.run_sync(metadata)
            expected = model.__table__
            assert {c["name"] for c in columns} == set(expected.columns.keys())
            for column in columns:
                mapped = expected.columns[column["name"]]
                assert column["nullable"] == mapped.nullable
                assert str(column["type"].compile(dialect=engine.dialect)) == str(
                    mapped.type.compile(dialect=engine.dialect)
                )
                if column["name"] == "id":
                    assert column["identity"]["always"] is False
                else:
                    assert (column["default"] is None) == (mapped.server_default is None)
                    if mapped.server_default is not None:
                        assert str(mapped.server_default.arg) in column["default"]
            actual_keys = {
                (key["constrained_columns"][0], key["referred_table"], key["referred_columns"][0])
                for key in keys
            }
            expected_keys = {
                (key.parent.name, *key.target_fullname.split(".")) for key in expected.foreign_keys
            }
            assert actual_keys == expected_keys
            assert all(key["options"].get("deferrable") is True for key in keys)
            assert all(key["options"].get("initially", "IMMEDIATE") == "IMMEDIATE" for key in keys)
            assert {check["name"] for check in checks} == {
                check.name
                for check in expected.constraints
                if check.__class__.__name__ == "CheckConstraint"
            }
            for index in expected.indexes:
                assert any(
                    value["column_names"] == [c.name for c in index.columns]
                    and bool(value["unique"]) == bool(index.unique)
                    for value in indexes
                )
