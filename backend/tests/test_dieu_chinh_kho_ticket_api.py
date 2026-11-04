"""Ticket contract v3 on real bootstrap/seed in disposable PostgreSQL schemas."""

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.dependencies import get_audit_service
from app.main import app
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService

BASE = "/api/v1/ticket_loi_dieu_chinh"


@pytest.fixture
async def ticket_context():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL TEST_DATABASE_URL")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must end in _test")
    schema = "ticket_api_" + uuid4().hex
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


async def ticket_detail(ticket_context, ticket_id=1):
    client, _, headers, _ = ticket_context
    response = await client.get(f"{BASE}/{ticket_id}", headers=headers())
    assert response.status_code == 200, response.text
    return response


async def business_snapshot(sessions):
    result = {}
    async with sessions() as db:
        for table in (
            "MatHang",
            "GiaoDichKho",
            "PhieuNhap",
            "ChiTietPhieuNhap",
            "PhieuDieuChinhKho",
            "ChiTietPhieuDieuChinhKho",
        ):
            result[table] = await db.scalar(
                text(f'SELECT jsonb_agg(to_jsonb(r) ORDER BY id) FROM "{table}" r')
            )
    return result


def assert_immutable_context(before, after):
    for name in (
        "id",
        "ma_ticket",
        "phieu_nhap_id",
        "nguoi_tao_id",
        "mo_ta_loi",
        "created_at",
        "chi_tiet",
    ):
        assert after[name] == before[name]


async def ticket_audits(sessions, ticket_id=1):
    async with sessions() as db:
        return (
            await db.execute(
                text("""SELECT nhan_vien_id,thao_tac,du_lieu_truoc,du_lieu_sau
                    FROM "LichSuThaoTac"
                    WHERE loai_doi_tuong='ticket_loi_dieu_chinh'
                      AND doi_tuong_id=:id ORDER BY id"""),
                {"id": ticket_id},
            )
        ).all()


def test_openapi_contains_only_four_ticket_operations():
    paths = app.openapi()["paths"]
    assert set(paths[BASE]) == {"get"}
    assert set(paths[BASE + "/{id}"]) == {"get"}
    assert set(paths[BASE + "/{id}/nhan_xu_ly"]) == {"post"}
    assert set(paths[BASE + "/{id}/giai_quyet"]) == {"post"}
    for path, operations in paths.items():
        if not path.startswith(BASE):
            continue
        for operation in operations.values():
            assert operation["security"]
            assert {"200", "401", "403", "422", "500"} <= operation["responses"].keys()
            if path != BASE:
                assert "ETag" in operation["responses"]["200"]["headers"]
            if path.endswith(("/nhan_xu_ly", "/giai_quyet")):
                assert {"404", "409", "412", "428"} <= operation["responses"].keys()
                assert any(p["name"].lower() == "if-match" for p in operation["parameters"])


async def test_seed_ticket_read_envelope_snapshot_and_strong_etag(ticket_context):
    client, sessions, headers, _ = ticket_context
    baseline = await business_snapshot(sessions)
    audits = await ticket_audits(sessions)
    detail = await ticket_detail(ticket_context)
    record = detail.json()["data"]
    assert set(record) == {
        "id",
        "ma_ticket",
        "phieu_nhap_id",
        "nguoi_tao_id",
        "mo_ta_loi",
        "trang_thai",
        "nguoi_xu_ly_id",
        "ket_qua_xu_ly",
        "created_at",
        "closed_at",
        "chi_tiet",
    }
    assert record["id"] == 1 and record["phieu_nhap_id"] == 1
    assert record["trang_thai"] == "cho_xu_ly" and record["nguoi_xu_ly_id"] is None
    assert record["created_at"].endswith("Z") and record["closed_at"] is None
    assert set(record["chi_tiet"][0]) == {
        "id",
        "chi_tiet_phieu_nhap_id",
        "mat_hang_id",
        "so_luong_hieu_luc_truoc",
        "so_luong_de_nghi",
        "so_luong_bien_dong",
        "ton_kho_tai_thoi_diem",
    }
    assert record["chi_tiet"][0]["so_luong_bien_dong"] == -785
    etag = detail.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"') and not etag.startswith("W/")
    same = await client.get(BASE + "/1", headers=headers(4))
    assert same.headers["etag"] == etag and same.json()["data"] == record
    assert detail.json()["meta"]["request_id"]
    listing = await client.get(BASE, headers=headers())
    assert listing.status_code == 200, listing.text
    assert "etag" not in listing.headers
    assert listing.json()["meta"]["total"] == 2
    assert listing.json()["meta"]["total_pages"] == 1
    assert record in listing.json()["data"]
    assert await business_snapshot(sessions) == baseline
    assert await ticket_audits(sessions) == audits


async def test_claim_then_resolve_preserves_context_and_audits_actual_actor(ticket_context):
    client, sessions, headers, _ = ticket_context
    original = await ticket_detail(ticket_context)
    before = await business_snapshot(sessions)
    audit_before = await ticket_audits(sessions)
    claimed = await client.post(
        BASE + "/1/nhan_xu_ly",
        headers={**headers(4), "If-Match": original.headers["etag"]},
        json={},
    )
    assert claimed.status_code == 200, claimed.text
    record = claimed.json()["data"]
    assert record["trang_thai"] == "dang_xu_ly" and record["nguoi_xu_ly_id"] == 4
    assert record["closed_at"] is None and record["ket_qua_xu_ly"] is None
    assert claimed.headers["etag"] != original.headers["etag"]
    assert_immutable_context(original.json()["data"], record)
    denied = await client.post(
        BASE + "/1/giai_quyet",
        headers={**headers(2), "If-Match": claimed.headers["etag"]},
        json={"ket_qua_xu_ly": "Cannot close another manager's ticket"},
    )
    assert denied.status_code == 403, denied.text
    closed = await client.post(
        BASE + "/1/giai_quyet",
        headers={**headers(4), "If-Match": claimed.headers["etag"]},
        json={"ket_qua_xu_ly": "  Reviewed failed proposal; no adjustment needed.  "},
    )
    assert closed.status_code == 200, closed.text
    resolved = closed.json()["data"]
    assert resolved["trang_thai"] == "da_xu_ly" and resolved["nguoi_xu_ly_id"] == 4
    assert resolved["ket_qua_xu_ly"] == "Reviewed failed proposal; no adjustment needed."
    assert resolved["closed_at"].endswith("Z")
    assert_immutable_context(original.json()["data"], resolved)
    assert await business_snapshot(sessions) == before
    new_audits = (await ticket_audits(sessions))[len(audit_before) :]
    assert [(row.nhan_vien_id, row.thao_tac) for row in new_audits] == [
        (4, "nhan_xu_ly"),
        (4, "giai_quyet"),
    ]
    assert new_audits[0].du_lieu_truoc == original.json()["data"]
    assert new_audits[0].du_lieu_sau == record
    assert new_audits[1].du_lieu_truoc == record and new_audits[1].du_lieu_sau == resolved


async def test_resolve_unclaimed_ticket_without_new_adjustment_succeeding(ticket_context):
    client, sessions, headers, _ = ticket_context
    original = await ticket_detail(ticket_context)
    snapshot = await business_snapshot(sessions)
    response = await client.post(
        BASE + "/1/giai_quyet",
        headers={**headers(4), "If-Match": original.headers["etag"]},
        json={"ket_qua_xu_ly": "Close without changing the failed adjustment"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["nguoi_xu_ly_id"] == 4
    assert response.json()["data"]["trang_thai"] == "da_xu_ly"
    assert await business_snapshot(sessions) == snapshot


@pytest.mark.parametrize("operation", ["nhan_xu_ly", "giai_quyet"])
async def test_closed_ticket_cannot_be_changed_or_reopened(ticket_context, operation):
    client, sessions, headers, _ = ticket_context
    original = await ticket_detail(ticket_context, 2)
    audits = await ticket_audits(sessions, 2)
    body = {"ket_qua_xu_ly": "Overwrite"} if operation == "giai_quyet" else {}
    response = await client.post(
        BASE + f"/2/{operation}",
        headers={**headers(), "If-Match": original.headers["etag"]},
        json=body,
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "trang_thai_khong_hop_le"
    current = await ticket_detail(ticket_context, 2)
    assert current.json()["data"] == original.json()["data"]
    assert current.headers["etag"] == original.headers["etag"]
    assert await ticket_audits(sessions, 2) == audits


@pytest.mark.parametrize("employee", [1, 3])
@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "", None),
        ("GET", "/1", None),
        ("POST", "/1/nhan_xu_ly", {}),
        ("POST", "/1/giai_quyet", {"ket_qua_xu_ly": "Reviewed"}),
    ],
)
async def test_only_current_db_manager_role_can_access(
    ticket_context, employee, method, suffix, body
):
    client, _, headers, _ = ticket_context
    response = await client.request(
        method,
        BASE + suffix,
        headers={**headers(employee, roles=["quan_ly"]), "If-Match": '"any"'},
        **({"json": body} if body is not None else {}),
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "khong_co_quyen"


@pytest.mark.parametrize(
    "change,status,code",
    [
        ("missing", 401, "chua_xac_thuc"),
        ("expired", 401, "chua_xac_thuc"),
        ("password", 401, "chua_xac_thuc"),
        ("role", 403, "khong_co_quyen"),
        ("locked", 403, "tai_khoan_bi_vo_hieu_hoa"),
    ],
)
async def test_authentication_uses_current_account_and_password(
    ticket_context, change, status, code
):
    client, sessions, headers, _ = ticket_context
    auth = headers(expires_delta=timedelta(seconds=-5)) if change == "expired" else headers()
    if change == "missing":
        auth = {}
    statements = {
        "password": "UPDATE \"NhanVien\" SET mat_khau='changed-hash' WHERE id=2",
        "role": 'UPDATE "NhanVien" SET vai_tro_id=3 WHERE id=2',
        "locked": "UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=2",
    }
    if change in statements:
        async with sessions() as db:
            await db.execute(text(statements[change]))
            await db.commit()
    response = await client.get(BASE, headers=auth)
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert response.json()["meta"]["request_id"]
    if status == 401:
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("operation", ["nhan_xu_ly", "giai_quyet"])
@pytest.mark.parametrize(
    "etag,status",
    [(None, 428), ("", 428), ('"stale"', 412), ("*", 412), ('W/"weak"', 412), ("unquoted", 412)],
)
async def test_mutation_preconditions_are_strict(ticket_context, operation, etag, status):
    client, _, headers, _ = ticket_context
    auth = headers()
    if etag is not None:
        auth["If-Match"] = etag
    response = await client.post(
        BASE + f"/1/{operation}",
        headers=auth,
        json={"ket_qua_xu_ly": "Reviewed"} if operation == "giai_quyet" else {},
    )
    assert response.status_code == status, response.text


@pytest.mark.parametrize("body", [None, [], {"nguoi_xu_ly_id": 4}, {"other": 1}])
async def test_claim_requires_exact_empty_json_object(ticket_context, body):
    client, _, headers, _ = ticket_context
    original = await ticket_detail(ticket_context)
    response = await client.post(
        BASE + "/1/nhan_xu_ly",
        headers={**headers(), "If-Match": original.headers["etag"]},
        json=body,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "body",
    [
        None,
        [],
        {},
        {"ket_qua_xu_ly": None},
        {"ket_qua_xu_ly": "  "},
        {"ket_qua_xu_ly": 12},
        {"ket_qua_xu_ly": True},
        {"ket_qua_xu_ly": "Done", "nguoi_xu_ly_id": 4},
        {"ket_qua_xu_ly": "Done", "closed_at": "2026-11-03"},
    ],
)
async def test_resolution_requires_nonempty_result_and_rejects_server_fields(ticket_context, body):
    client, _, headers, _ = ticket_context
    original = await ticket_detail(ticket_context)
    response = await client.post(
        BASE + "/1/giai_quyet",
        headers={**headers(), "If-Match": original.headers["etag"]},
        json=body,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "method,suffix,body",
    [
        ("GET", "/999999", None),
        ("POST", "/999999/nhan_xu_ly", {}),
        ("POST", "/999999/giai_quyet", {"ket_qua_xu_ly": "Done"}),
    ],
)
async def test_missing_ticket_returns_404(ticket_context, method, suffix, body):
    client, _, headers, _ = ticket_context
    response = await client.request(
        method,
        BASE + suffix,
        headers={**headers(), "If-Match": '"any"'},
        **({"json": body} if body is not None else {}),
    )
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "khong_tim_thay"


@pytest.mark.parametrize("identifier", ["0", "-1", "abc"])
async def test_path_ids_are_validated(ticket_context, identifier):
    client, _, headers, _ = ticket_context
    response = await client.get(BASE + "/" + identifier, headers=headers())
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "query",
    [
        {"q": "ticket"},
        {"sort": "mo_ta_loi"},
        {"sort": "wrong"},
        {"trang_thai": "wrong"},
        {"page": 0},
        {"page_size": 101},
        {"nguoi_tao_id": 0},
        {"nguoi_xu_ly_id": -1},
        {"tu_ngay": "2026-11-04", "den_ngay": "2026-11-03"},
        {"tu_ngay": "2026-11-03T00:00:00Z"},
        [("page", "1"), ("page", "2")],
    ],
)
async def test_query_validation(ticket_context, query):
    client, _, headers, _ = ticket_context
    response = await client.get(BASE, headers=headers(), params=query)
    assert response.status_code == 422, response.text


async def test_filters_sort_and_inclusive_local_dates(ticket_context):
    client, sessions, headers, _ = ticket_context
    async with sessions() as db:
        for record_id, created_at, creator in (
            (3, "2026-10-21 17:00:00+00", 4),
            (4, "2026-10-22 17:00:00+00", 4),
            (5, "2026-10-21 16:59:59+00", 2),
        ):
            await db.execute(
                text("""INSERT INTO "TicketLoiDieuChinh"
                    (id,ma_ticket,phieu_nhap_id,nguoi_tao_id,mo_ta_loi,created_at)
                    VALUES (:id,:code,1,:creator,'Failed adjustment snapshot',cast(:created_at as timestamptz))"""),
                {
                    "id": record_id,
                    "code": f"TKDC-202610-{record_id:06d}",
                    "creator": creator,
                    "created_at": datetime.fromisoformat(created_at),
                },
            )
        await db.commit()
    response = await client.get(
        BASE,
        headers=headers(),
        params={"tu_ngay": "2026-10-22", "den_ngay": "2026-10-22", "sort": "id"},
    )
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()["data"]] == [1, 2, 3]
    response = await client.get(
        BASE,
        headers=headers(),
        params={
            "nguoi_tao_id": 4,
            "trang_thai": "cho_xu_ly",
            "sort": "-ma_ticket",
            "page": 2,
            "page_size": 1,
        },
    )
    assert response.json()["meta"]["total"] == 2 and response.json()["meta"]["total_pages"] == 2
    assert [row["id"] for row in response.json()["data"]] == [3]
    response = await client.get(
        BASE,
        headers=headers(),
        params={"nguoi_xu_ly_id": 2, "trang_thai": "da_xu_ly", "phieu_nhap_id": 1},
    )
    assert [row["id"] for row in response.json()["data"]] == [2]
    empty = await client.get(BASE, headers=headers(), params={"phieu_nhap_id": 999})
    assert empty.json()["data"] == [] and empty.json()["meta"]["total_pages"] == 0


async def test_unsupported_methods_cannot_create_modify_delete_or_reopen_tickets(ticket_context):
    client, _, headers, _ = ticket_context
    for method, suffix in [("POST", ""), ("PATCH", "/1"), ("DELETE", "/1"), ("PUT", "/1")]:
        response = await client.request(method, BASE + suffix, headers=headers(), json={})
        assert response.status_code == 405, response.text


async def test_duplicate_if_match_and_extra_action_query_are_rejected(ticket_context):
    client, _, headers, _ = ticket_context
    detail = await ticket_detail(ticket_context)
    duplicate = await client.post(
        BASE + "/1/nhan_xu_ly",
        headers=[
            *headers().items(),
            ("If-Match", detail.headers["etag"]),
            ("If-Match", detail.headers["etag"]),
        ],
        json={},
    )
    assert duplicate.status_code == 422, duplicate.text
    extra = await client.post(
        BASE + "/1/giai_quyet?unexpected=1",
        headers={**headers(), "If-Match": detail.headers["etag"]},
        json={"ket_qua_xu_ly": "Done"},
    )
    assert extra.status_code == 422, extra.text


async def test_concurrent_claims_have_one_winner_and_one_stale_request(ticket_context):
    client, sessions, headers, _ = ticket_context
    detail = await ticket_detail(ticket_context)
    baseline = await ticket_audits(sessions)
    results = await asyncio.gather(
        *[
            client.post(
                BASE + "/1/nhan_xu_ly",
                headers={**headers(employee), "If-Match": detail.headers["etag"]},
                json={},
            )
            for employee in (2, 4)
        ]
    )
    assert sorted(response.status_code for response in results) == [200, 412], [
        r.text for r in results
    ]
    winner = next(response for response in results if response.status_code == 200)
    current = await ticket_detail(ticket_context)
    assert current.json()["data"] == winner.json()["data"]
    assert len(await ticket_audits(sessions)) == len(baseline) + 1


async def test_concurrent_resolutions_only_close_once(ticket_context):
    client, sessions, headers, _ = ticket_context
    detail = await ticket_detail(ticket_context)
    baseline = await ticket_audits(sessions)
    results = await asyncio.gather(
        *[
            client.post(
                BASE + "/1/giai_quyet",
                headers={**headers(employee), "If-Match": detail.headers["etag"]},
                json={"ket_qua_xu_ly": f"Reviewed by manager {employee}"},
            )
            for employee in (2, 4)
        ]
    )
    assert sorted(response.status_code for response in results) == [200, 412], [
        r.text for r in results
    ]
    winner = next(response for response in results if response.status_code == 200)
    current = await ticket_detail(ticket_context)
    assert current.json()["data"] == winner.json()["data"]
    assert len(await ticket_audits(sessions)) == len(baseline) + 1


@pytest.mark.parametrize("operation", ["nhan_xu_ly", "giai_quyet"])
@pytest.mark.parametrize("failure_point", ["service", "audit_flush", "commit"])
async def test_audit_service_or_database_failure_rolls_back_ticket_and_audit(
    ticket_context, operation, failure_point
):
    client, sessions, headers, engine = ticket_context
    before = await ticket_detail(ticket_context)
    audit_before = await ticket_audits(sessions)
    business_before = await business_snapshot(sessions)
    seen = []

    class ObservedAuditService(AuditService):
        async def append(self, entry):
            seen.append(entry.thao_tac)
            if failure_point == "service":
                raise RuntimeError("private audit service failure")
            await super().append(entry)

    def audit_factory(db: Annotated[AsyncSession, Depends(get_db)]):
        return ObservedAuditService(SqlAlchemyAuditRepository(db))

    def fail_flush(conn, cursor, statement, parameters, execution_context, many):
        if 'insert into "lichsuthaotac"' in statement.lower():
            raise RuntimeError("private audit flush failure")

    def fail_commit(conn):
        raise RuntimeError("private transaction commit failure")

    app.dependency_overrides[get_audit_service] = audit_factory
    if failure_point == "audit_flush":
        event.listen(engine.sync_engine, "before_cursor_execute", fail_flush)
    if failure_point == "commit":
        event.listen(engine.sync_engine, "commit", fail_commit)
    try:
        result = await client.post(
            BASE + f"/1/{operation}",
            headers={**headers(), "If-Match": before.headers["etag"]},
            json={"ket_qua_xu_ly": "Reviewed"} if operation == "giai_quyet" else {},
        )
        assert result.status_code == 500, result.text
        assert result.json()["error"]["code"] == "loi_noi_bo"
        assert "private" not in result.text
        assert seen == [operation]
    finally:
        app.dependency_overrides.pop(get_audit_service, None)
        if failure_point == "audit_flush":
            event.remove(engine.sync_engine, "before_cursor_execute", fail_flush)
        if failure_point == "commit":
            event.remove(engine.sync_engine, "commit", fail_commit)
    after = await ticket_detail(ticket_context)
    assert after.json()["data"] == before.json()["data"]
    assert after.headers["etag"] == before.headers["etag"]
    assert await ticket_audits(sessions) == audit_before
    assert await business_snapshot(sessions) == business_before
