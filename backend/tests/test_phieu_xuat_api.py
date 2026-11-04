"""Contract v3 against real bootstrap/seed in disposable PostgreSQL schemas."""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.errors import PostedProductionDependency
from app.core.security import create_access_token, password_version
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.dependencies import get_mat_hang_cache
from app.main import app
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository
from app.modules.phieu_xuat.repository import SqlAlchemyPhieuXuatRepository
from app.modules.phieu_xuat.service import PhieuXuatService

BASE = "/api/v1/phieu_xuat"
BODY = {
    "loai_phieu": "xuat_vat_tu",
    "lenh_san_xuat_id": 100,
    "chi_tiet": [{"mat_hang_id": 8, "so_luong": 3}],
}


@pytest.fixture
async def context():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL TEST_DATABASE_URL")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL must end in _test")
    schema = "issue_v3_" + uuid4().hex
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
                text("""INSERT INTO "NhanVien" (id,vai_tro_id,ten_dang_nhap,ma_nhan_vien,mat_khau)
                SELECT 4,2,'manager2','NV-000004',mat_khau FROM "NhanVien" WHERE id=2""")
            )
            await connection.execute(
                text("""INSERT INTO "NhanVien" (id,vai_tro_id,ten_dang_nhap,ma_nhan_vien,mat_khau)
                SELECT 5,3,'worker2','NV-000005',mat_khau FROM "NhanVien" WHERE id=2""")
            )
            await connection.execute(
                text("""INSERT INTO "YeuCauSanXuat" (id,ma_yeu_cau_san_xuat,mat_hang_id,so_luong,nhan_vien_id,nhan_vien_duoc_giao_id,trang_thai)
                VALUES (100,'YCSX-202611-000100',1,10,2,3,'da_gui')""")
            )
            await connection.execute(
                text("""INSERT INTO "LenhSanXuat" (id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,mat_hang_id,bom_id,so_luong,nhan_vien_id,trang_thai)
                VALUES (100,'LSX-202611-000100',100,1,1,10,3,'da_gui')""")
            )
            await connection.execute(
                text(
                    """INSERT INTO "ChiTietLenhSanXuat" (lenh_san_xuat_id,mat_hang_id,so_luong_can) VALUES (100,8,20),(100,10,20)"""
                )
            )
            await connection.execute(
                text(
                    """INSERT INTO "PhieuNhap" (id,ma_phieu_nhap,nhan_vien_id,ncc_id,ngay_nhap) VALUES (100,'PN-202611-000100',2,1,current_date)"""
                )
            )
            line = await connection.scalar(
                text(
                    """INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia) VALUES (100,8,100,1,100) RETURNING id"""
                )
            )
            await connection.execute(
                text("""UPDATE "PhieuNhap" SET trang_thai='hoan_thanh' WHERE id=100""")
            )
            await connection.execute(
                text(
                    """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chi_tiet_phieu_nhap_id,nhan_vien_id) VALUES (8,'nhap_vat_tu',100,:line,2)"""
                ),
                {"line": line},
            )
            await connection.execute(
                text("""UPDATE "MatHang" SET so_luong_ton=so_luong_ton+100 WHERE id=8""")
            )
            await connection.execute(
                text(
                    """INSERT INTO "ChungTuHoanThanhSx" (id,ma_phieu,lenh_san_xuat_id,so_luong_hoan_thanh,nhan_vien_id,trang_thai,finish_time) VALUES (100,'HTSX-202611-000100',100,10,3,'da_duyet',now())"""
                )
            )
            await connection.execute(
                text(
                    """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chung_tu_hoan_thanh_sx_id,nhan_vien_id) VALUES (1,'nhap_san_pham_san_xuat',10,100,2)"""
                )
            )
            await connection.execute(
                text("""UPDATE "MatHang" SET so_luong_ton=so_luong_ton+10 WHERE id=1""")
            )
            password_hash = await connection.scalar(
                text('SELECT mat_khau FROM "NhanVien" WHERE id=2')
            )

        async def db():
            async with sessions() as session:
                yield session

        app.dependency_overrides[get_db] = db

        def headers(employee=2, roles=None):
            role = {1: "quan_tri_vien", 2: "quan_ly", 3: "nhan_vien", 4: "quan_ly", 5: "nhan_vien"}[
                employee
            ]
            return {
                "Authorization": "Bearer "
                + create_access_token(
                    employee,
                    roles=roles or [role],
                    credential_version=password_version(password_hash),
                )
            }

        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client, sessions, headers, engine
    finally:
        app.dependency_overrides.clear()
        async with engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()


async def create(context, body=None, employee=2):
    client, _, headers, _ = context
    response = await client.post(
        BASE, headers=headers(employee), json=BODY if body is None else body
    )
    assert response.status_code == 201, response.text
    return response


async def submit(context, created):
    client, _, headers, _ = context
    response = await client.post(
        created.headers["location"] + "/gui",
        headers={**headers(), "If-Match": created.headers["etag"]},
        json={},
    )
    assert response.status_code == 200, response.text
    return response


async def approve(context, created):
    client, _, headers, _ = context
    submitted = await submit(context, created)
    response = await client.post(
        created.headers["location"] + "/duyet",
        headers={**headers(), "If-Match": submitted.headers["etag"]},
        json={},
    )
    assert response.status_code == 200, response.text
    return response


@pytest.mark.parametrize("if_match", [None, "", "*", 'W/"x"', '"stale"'])
async def test_approve_replay_ignores_if_match(context, if_match):
    client, sessions, headers, _ = context
    created = await create(context)
    approved = await approve(context, created)
    path = created.headers["location"]
    audit_query = text(
        "SELECT count(*) FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_xuat' AND doi_tuong_id=:id"
    )
    stock_query = text('SELECT so_luong_ton FROM "MatHang" WHERE id=8')
    async with sessions() as db:
        audit_count = await db.scalar(audit_query, {"id": created.json()["data"]["id"]})
        stock = await db.scalar(stock_query)
    auth = headers(4)
    if if_match is not None:
        auth["If-Match"] = if_match

    replay = await client.post(path + "/duyet", headers=auth, json={})

    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["da_ghi_so_truoc_do"] is True
    assert (
        replay.json()["data"]["giao_dich_kho_ids"] == approved.json()["data"]["giao_dich_kho_ids"]
    )
    detail = await client.get(path, headers=headers())
    assert detail.status_code == 200, detail.text
    assert replay.headers["etag"] == detail.headers["etag"] == approved.headers["etag"]
    async with sessions() as db:
        assert await db.scalar(stock_query) == stock
        assert await db.scalar(audit_query, {"id": created.json()["data"]["id"]}) == audit_count


@pytest.mark.parametrize("if_match,status", [(None, 428), ("*", 412)])
async def test_first_approval_still_requires_if_match(context, if_match, status):
    client, _, headers, _ = context
    created = await create(context)
    await submit(context, created)
    auth = headers()
    if if_match is not None:
        auth["If-Match"] = if_match

    response = await client.post(created.headers["location"] + "/duyet", headers=auth, json={})

    assert response.status_code == status, response.text
    detail = await client.get(created.headers["location"], headers=headers())
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["trang_thai"] == "cho_duyet"


@pytest.mark.parametrize("employee", [3, 1])
async def test_approve_replay_still_checks_role(context, employee):
    client, _, headers, _ = context
    created = await create(context)
    await approve(context, created)

    replay = await client.post(
        created.headers["location"] + "/duyet", headers=headers(employee), json={}
    )

    assert replay.status_code == 403, replay.text


async def test_reads_do_not_wait_for_write_locks(context):
    client, sessions, headers, _ = context
    created = await create(context)
    issue_id = created.json()["data"]["id"]
    async with sessions() as locked:
        try:
            await locked.execute(
                text('SELECT id FROM "PhieuXuat" WHERE id=:id FOR UPDATE'), {"id": issue_id}
            )
            await locked.execute(
                text('SELECT id FROM "ChiTietPhieuXuat" WHERE phieu_xuat_id=:id FOR UPDATE'),
                {"id": issue_id},
            )

            detail = await asyncio.wait_for(
                client.get(created.headers["location"], headers=headers(3)), 3
            )
            listing = await asyncio.wait_for(client.get(BASE, headers=headers(3)), 3)

            assert detail.status_code == 200, detail.text
            assert detail.json()["data"]["id"] == issue_id
            assert listing.status_code == 200, listing.text
            assert issue_id in {record["id"] for record in listing.json()["data"]}
        finally:
            await locked.rollback()


async def test_list_loads_lines_in_one_query(context):
    client, _, headers, engine = context
    created = [await create(context) for _ in range(3)]
    statements = []

    def capture(_connection, _cursor, statement, _parameters, _context, _executemany):
        if '"ChiTietPhieuXuat"' in statement:
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", capture)
    try:
        listing = await client.get(BASE, headers=headers(), params={"page_size": 100})
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", capture)

    assert listing.status_code == 200, listing.text
    records = {record["id"]: record for record in listing.json()["data"]}
    for response in created:
        record = response.json()["data"]
        assert records[record["id"]] == record
    assert len(statements) == 1, statements


@pytest.mark.parametrize("employee", [2, 3])
async def test_detail_etag_matches_write_etag(context, employee):
    client, _, headers, _ = context
    created = await create(context)

    detail = await client.get(created.headers["location"], headers=headers(employee))

    assert detail.status_code == 200, detail.text
    assert detail.json()["data"] == created.json()["data"]
    assert detail.headers["etag"] == created.headers["etag"]


async def test_detail_keeps_snapshot_during_concurrent_patch(context, monkeypatch):
    client, _, headers, _ = context
    created = await create(context)
    path = created.headers["location"]
    original_lines = SqlAlchemyPhieuXuatRepository._lines

    async def patch_before_lines(repository, issue_ids, *, lock):
        if not lock:
            assert (
                await repository.session.scalar(text("SHOW transaction_isolation"))
                == "repeatable read"
            )
            assert await repository.session.scalar(text("SHOW transaction_read_only")) == "on"
            changed = await client.patch(
                path,
                headers={**headers(), "If-Match": created.headers["etag"]},
                json={"chi_tiet": [{"mat_hang_id": 8, "so_luong": 4}]},
            )
            assert changed.status_code == 200, changed.text
        return await original_lines(repository, issue_ids, lock=lock)

    with monkeypatch.context() as patch:
        patch.setattr(SqlAlchemyPhieuXuatRepository, "_lines", patch_before_lines)
        detail = await client.get(path, headers=headers(3))

    assert detail.status_code == 200, detail.text
    assert detail.json()["data"] == created.json()["data"]
    assert detail.headers["etag"] == created.headers["etag"]
    current = await client.get(path, headers=headers(3))
    assert current.status_code == 200, current.text
    assert current.json()["data"]["chi_tiet"][0]["so_luong"] == 4
    assert current.headers["etag"] != detail.headers["etag"]


def test_openapi_nine_endpoints_and_no_legacy_routes():
    paths = app.openapi()["paths"]
    assert sum(len(value) for path, value in paths.items() if path.startswith(BASE)) == 9
    assert "/api/v1/material-issuing" not in paths
    assert "/api/v1/finished-goods-issuing" not in paths
    for path, value in paths.items():
        if path.startswith(BASE):
            for method, operation in value.items():
                assert operation["security"]
                assert {"401", "403", "422", "500"} <= operation["responses"].keys()
                if method != "delete" and path != BASE:
                    assert "ETag" in operation["responses"]["200"]["headers"]


async def test_full_lifecycle_prices_frozen_stock_and_replay(context):
    client, sessions, headers, _ = context
    created = await create(context)
    record = created.json()["data"]
    assert record["nhan_vien_id"] == 2 and "ma_nhan_vien" not in record
    assert record["tong_tien"] is None and record["chi_tiet"][0]["don_gia_thuc"] is None
    assert record["created_at"].endswith("Z")
    path = created.headers["location"]
    changed = await client.patch(
        path,
        headers={**headers(4), "If-Match": created.headers["etag"]},
        json={"chi_tiet": [{"mat_hang_id": 8, "so_luong": 4}]},
    )
    assert changed.status_code == 200, changed.text
    assert changed.headers["etag"] != created.headers["etag"]
    submitted = await client.post(
        path + "/gui", headers={**headers(), "If-Match": changed.headers["etag"]}, json={}
    )
    assert submitted.json()["data"]["trang_thai"] == "cho_duyet"
    async with sessions() as db:
        before = await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8'))
        await db.execute(text('UPDATE "MatHang" SET don_gia=3000000000 WHERE id=8'))
        await db.commit()
    approved = await client.post(
        path + "/duyet", headers={**headers(), "If-Match": submitted.headers["etag"]}, json={}
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["tong_tien"] == 12000000000
    assert approved.json()["data"]["da_ghi_so_truoc_do"] is False
    async with sessions() as db:
        assert await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8')) == before - 4
        await db.execute(text('UPDATE "MatHang" SET don_gia=5 WHERE id=8'))
        await db.commit()
        audit_count = await db.scalar(
            text(
                "SELECT count(*) FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_xuat' AND doi_tuong_id=:id"
            ),
            {"id": record["id"]},
        )
    replay = await client.post(
        path + "/duyet", headers={**headers(4), "If-Match": created.headers["etag"]}, json={}
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["da_ghi_so_truoc_do"] is True
    assert (
        replay.json()["data"]["giao_dich_kho_ids"] == approved.json()["data"]["giao_dich_kho_ids"]
    )
    assert replay.json()["data"]["tong_tien"] == 12000000000
    detail = await client.get(path, headers=headers(3))
    assert detail.headers["etag"] == approved.headers["etag"]
    for method, suffix, body in [
        ("patch", "", {}),
        ("delete", "", None),
        ("post", "/ve_nhap", {"ly_do": "test"}),
    ]:
        response = await client.request(
            method,
            path + suffix,
            headers={**headers(), "If-Match": detail.headers["etag"]},
            **({"json": body} if body is not None else {}),
        )
        assert response.status_code == 409, response.text
    async with sessions() as db:
        assert (
            await db.scalar(
                text(
                    "SELECT count(*) FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_xuat' AND doi_tuong_id=:id"
                ),
                {"id": record["id"]},
            )
            == audit_count
        )


async def test_reject_return_draft_and_delete_store_reason(context):
    client, sessions, headers, _ = context
    created = await create(context)
    path = created.headers["location"]
    submitted = await submit(context, created)
    rejected = await client.post(
        path + "/tu_choi",
        headers={**headers(4), "If-Match": submitted.headers["etag"]},
        json={"ly_do": "  Wrong quantity  "},
    )
    assert rejected.status_code == 200, rejected.text
    reverted = await client.post(
        path + "/ve_nhap",
        headers={**headers(), "If-Match": rejected.headers["etag"]},
        json={"ly_do": "Corrected"},
    )
    assert reverted.json()["data"]["trang_thai"] == "nhap"
    deleted = await client.delete(path, headers={**headers(), "If-Match": reverted.headers["etag"]})
    assert deleted.status_code == 204 and deleted.content == b""
    assert (await client.get(path, headers=headers())).status_code == 404
    async with sessions() as db:
        reasons = (
            await db.scalars(
                text(
                    "SELECT ly_do FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_xuat' AND doi_tuong_id=:id AND ly_do IS NOT NULL ORDER BY id"
                ),
                {"id": created.json()["data"]["id"]},
            )
        ).all()
        assert reasons == ["Wrong quantity", "Corrected"]


@pytest.mark.parametrize("employee,status", [(1, 403), (3, 403), (5, 403)])
async def test_non_managers_cannot_write(context, employee, status):
    client, _, headers, _ = context
    created = await create(context)
    for method, suffix, body in [
        ("post", "", BODY),
        ("patch", "/1", {}),
        ("delete", "/1", None),
        *[
            ("post", f"/1/{action}", {"ly_do": "test"} if action in {"tu_choi", "ve_nhap"} else {})
            for action in ("gui", "duyet", "tu_choi", "ve_nhap")
        ],
    ]:
        path = BASE if suffix == "" else created.headers["location"] + suffix[2:]
        response = await client.request(
            method,
            path,
            headers={**headers(employee, roles=["quan_ly"]), "If-Match": created.headers["etag"]},
            **({"json": body} if body is not None else {}),
        )
        assert response.status_code == status, response.text


async def test_read_scope_uses_current_assignment_not_creator(context):
    client, sessions, headers, _ = context
    created = await create(context)
    assert (await client.get(BASE, headers=headers(3))).json()["meta"]["total"] >= 1
    assert (await client.get(created.headers["location"], headers=headers(5))).status_code == 403
    async with sessions() as db:
        await db.execute(text('UPDATE "LenhSanXuat" SET nhan_vien_id=5 WHERE id=100'))
        await db.commit()
    assert (await client.get(created.headers["location"], headers=headers(3))).status_code == 403
    assert (await client.get(created.headers["location"], headers=headers(5))).status_code == 200
    assert (await client.get(BASE, headers=headers(3), params={"lenh_san_xuat_id": 100})).json()[
        "data"
    ] == []


@pytest.mark.parametrize(
    "change,code,status",
    [
        ("locked", "tai_khoan_bi_vo_hieu_hoa", 403),
        ("password", "chua_xac_thuc", 401),
        ("missing", "chua_xac_thuc", 401),
    ],
)
async def test_current_account_and_password_version(context, change, code, status):
    client, sessions, headers, _ = context
    auth = headers()
    if change == "missing":
        auth = {}
    else:
        async with sessions() as db:
            await db.execute(
                text(
                    "UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=2"
                    if change == "locked"
                    else "UPDATE \"NhanVien\" SET mat_khau='new-hash' WHERE id=2"
                )
            )
            await db.commit()
    response = await client.get(BASE, headers=auth)
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize(
    "etag,status", [(None, 428), ("*", 412), ('W/"abc"', 412), ('"stale"', 412), ("", 428)]
)
async def test_preconditions(context, etag, status):
    client, _, headers, _ = context
    created = await create(context)
    auth = headers()
    if etag is not None:
        auth["If-Match"] = etag
    response = await client.post(created.headers["location"] + "/gui", headers=auth, json={})
    assert response.status_code == status, response.text


@pytest.mark.parametrize(
    "body",
    [
        {},
        {**BODY, "don_gia_thuc": 1},
        {**BODY, "nhan_vien_id": 3},
        {**BODY, "ma_nhan_vien": "NV-000003"},
        {**BODY, "yeu_cau_san_xuat_id": 100},
        {**BODY, "chi_tiet": []},
        {**BODY, "chi_tiet": BODY["chi_tiet"] * 2},
        *[
            {**BODY, "chi_tiet": [{"mat_hang_id": 8, "so_luong": value}]}
            for value in (0, -1, True, 1.0, "1")
        ],
        {**BODY, "chi_tiet": [{"mat_hang_id": 8, "so_luong": 1, "don_gia_thuc": 2}]},
    ],
)
async def test_create_validation(context, body):
    client, _, headers, _ = context
    response = await client.post(BASE, headers=headers(), json=body)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "query",
    [
        {"sort": "wrong"},
        {"page": 0},
        {"page_size": 101},
        {"ma_nhan_vien": "NV-000003"},
        {"tu_ngay": "2026-11-04", "den_ngay": "2026-11-03"},
        [("page", "1"), ("page", "2")],
    ],
)
async def test_query_validation(context, query):
    client, _, headers, _ = context
    response = await client.get(BASE, headers=headers(), params=query)
    assert response.status_code == 422, response.text


async def test_finished_goods_progress_and_waiting_materials_block(context):
    client, sessions, headers, _ = context
    body = {
        "loai_phieu": "xuat_thanh_pham",
        "yeu_cau_san_xuat_id": 100,
        "chi_tiet": [{"mat_hang_id": 1, "so_luong": 4}],
    }
    for quantity, expected in ((4, "dang_thuc_hien"), (6, "hoan_thanh")):
        created = await create(
            context, {**body, "chi_tiet": [{"mat_hang_id": 1, "so_luong": quantity}]}
        )
        sent = await submit(context, created)
        approved = await client.post(
            created.headers["location"] + "/duyet",
            headers={**headers(), "If-Match": sent.headers["etag"]},
            json={},
        )
        assert approved.status_code == 200, approved.text
        async with sessions() as db:
            assert (
                await db.scalar(text('SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=100'))
                == expected
            )
            assert bool(
                await db.scalar(text('SELECT completed_at FROM "YeuCauSanXuat" WHERE id=100'))
            ) == (expected == "hoan_thanh")
    async with sessions() as db:
        await db.execute(
            text("UPDATE \"YeuCauSanXuat\" SET trang_thai='cho_bo_sung_vat_tu' WHERE id=100")
        )
        await db.commit()
    response = await client.post(BASE, headers=headers(), json=body)
    assert response.status_code == 409, response.text


async def test_concurrent_approval_same_issue_is_idempotent(context):
    client, _, headers, _ = context
    created = await create(context)
    sent = await submit(context, created)

    async def approve():
        return await client.post(
            created.headers["location"] + "/duyet",
            headers={**headers(), "If-Match": sent.headers["etag"]},
            json={},
        )

    results = await asyncio.gather(approve(), approve())
    assert [result.status_code for result in results] == [200, 200], [r.text for r in results]
    assert sorted(result.json()["data"]["da_ghi_so_truoc_do"] for result in results) == [
        False,
        True,
    ]
    assert (
        results[0].json()["data"]["giao_dich_kho_ids"]
        == results[1].json()["data"]["giao_dich_kho_ids"]
    )


async def test_concurrent_issues_cannot_exceed_demand(context):
    client, _, headers, _ = context
    body = {**BODY, "chi_tiet": [{"mat_hang_id": 8, "so_luong": 15}]}
    created = [await create(context, body) for _ in range(2)]
    sent = [await submit(context, item) for item in created]
    results = await asyncio.gather(
        *[
            client.post(
                item.headers["location"] + "/duyet",
                headers={**headers(), "If-Match": state.headers["etag"]},
                json={},
            )
            for item, state in zip(created, sent, strict=True)
        ]
    )
    assert sorted(r.status_code for r in results) == [200, 409], [r.text for r in results]
    assert (
        next(r for r in results if r.status_code == 409).json()["error"]["code"] == "vuot_nhu_cau"
    )


@pytest.mark.parametrize("point", ["ledger", "balance", "audit"])
async def test_failure_rolls_back_price_state_ledger_balance_and_audit(context, point):
    client, sessions, headers, engine = context
    created = await create(context)
    sent = await submit(context, created)
    async with sessions() as db:
        baseline = await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8'))

    def inject(conn, cursor, statement, parameters, execution_context, many):
        normalized = statement.lower()
        if (
            (point == "ledger" and 'insert into "giaodichkho"' in normalized)
            or (point == "balance" and 'update "mathang"' in normalized)
            or (point == "audit" and 'insert into "lichsuthaotac"' in normalized)
        ):
            raise RuntimeError("private injected failure")

    event.listen(engine.sync_engine, "before_cursor_execute", inject)
    try:
        response = await client.post(
            created.headers["location"] + "/duyet",
            headers={**headers(), "If-Match": sent.headers["etag"]},
            json={},
        )
        assert response.status_code == 500, response.text
        assert "private" not in response.text
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", inject)
    detail = await client.get(created.headers["location"], headers=headers())
    assert detail.headers["etag"] == sent.headers["etag"]
    assert detail.json()["data"]["tong_tien"] is None
    async with sessions() as db:
        assert await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8')) == baseline
        assert (
            await db.scalar(
                text('SELECT count(*) FROM "GiaoDichKho" WHERE chi_tiet_phieu_xuat_id=:id'),
                {"id": created.json()["data"]["chi_tiet"][0]["id"]},
            )
            == 0
        )
        assert (
            await db.scalar(
                text(
                    "SELECT count(*) FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_xuat' AND doi_tuong_id=:id AND thao_tac='duyet'"
                ),
                {"id": created.json()["data"]["id"]},
            )
            == 0
        )


async def test_shared_stock_cannot_be_overdrawn_by_different_sources(context):
    client, sessions, headers, _ = context
    async with sessions() as db:
        await db.execute(
            text(
                """INSERT INTO "YeuCauSanXuat" (id,ma_yeu_cau_san_xuat,mat_hang_id,so_luong,nhan_vien_id,nhan_vien_duoc_giao_id,trang_thai) VALUES (101,'YCSX-202611-000101',1,10,2,3,'da_gui')"""
            )
        )
        await db.execute(
            text(
                """INSERT INTO "LenhSanXuat" (id,ma_lenh_san_xuat,yeu_cau_san_xuat_id,mat_hang_id,bom_id,so_luong,nhan_vien_id,trang_thai) VALUES (101,'LSX-202611-000101',101,1,1,10,3,'da_gui')"""
            )
        )
        await db.execute(
            text(
                """UPDATE "ChiTietLenhSanXuat" SET so_luong_can=200 WHERE lenh_san_xuat_id=100 AND mat_hang_id=8"""
            )
        )
        await db.execute(
            text(
                """INSERT INTO "ChiTietLenhSanXuat" (lenh_san_xuat_id,mat_hang_id,so_luong_can) VALUES (101,8,200)"""
            )
        )
        stock = await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8'))
        await db.commit()
    quantity = stock // 2 + 1
    records = [
        await create(
            context,
            {
                **BODY,
                "lenh_san_xuat_id": source,
                "chi_tiet": [{"mat_hang_id": 8, "so_luong": quantity}],
            },
        )
        for source in (100, 101)
    ]
    submitted = [await submit(context, record) for record in records]
    results = await asyncio.gather(
        *[
            client.post(
                record.headers["location"] + "/duyet",
                headers={**headers(), "If-Match": sent.headers["etag"]},
                json={},
            )
            for record, sent in zip(records, submitted, strict=True)
        ]
    )
    assert sorted(response.status_code for response in results) == [200, 409], [
        r.text for r in results
    ]
    failure = next(response for response in results if response.status_code == 409)
    assert failure.json()["error"]["code"] == "khong_du_ton_kho"
    assert failure.json()["error"]["details"][0]["mat_hang_id"] == 8
    async with sessions() as db:
        assert (
            await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=8'))
            == stock - quantity
        )
        assert (
            await db.scalar(
                text('SELECT sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id=8')
            )
            == stock - quantity
        )


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("inactive", "mat_hang_ngung_hoat_dong"),
        ("source", "trang_thai_khong_hop_le"),
        ("balance", "trang_thai_khong_hop_le"),
        ("overflow", "phu_thuoc_khong_hop_le"),
    ],
)
async def test_approve_rechecks_data_after_submission(context, mutation, code):
    client, sessions, headers, _ = context
    created = await create(context)
    sent = await submit(context, created)
    statements = {
        "inactive": 'UPDATE "MatHang" SET is_active=false WHERE id=8',
        "source": "UPDATE \"LenhSanXuat\" SET trang_thai='da_huy' WHERE id=100",
        "balance": 'UPDATE "MatHang" SET so_luong_ton=so_luong_ton+1 WHERE id=8',
        "overflow": 'UPDATE "MatHang" SET don_gia=9223372036854775807 WHERE id=8',
    }
    async with sessions() as db:
        await db.execute(text(statements[mutation]))
        await db.commit()
    response = await client.post(
        created.headers["location"] + "/duyet",
        headers={**headers(), "If-Match": sent.headers["etag"]},
        json={},
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == code
    detail = await client.get(created.headers["location"], headers=headers())
    assert detail.json()["data"]["trang_thai"] == "cho_duyet"
    assert detail.json()["data"]["tong_tien"] is None


@pytest.mark.parametrize("body", [None, [], {"other": 1}, {"ly_do": " "}])
async def test_action_bodies_are_strict(context, body):
    client, _, headers, _ = context
    created = await create(context)
    for action in ("gui", "duyet", "tu_choi", "ve_nhap"):
        response = await client.post(
            created.headers["location"] + "/" + action,
            headers={**headers(), "If-Match": created.headers["etag"]},
            json=body,
        )
        assert response.status_code == 422, response.text


async def test_list_filters_pagination_and_headers(context):
    client, _, headers, _ = context
    records = [await create(context) for _ in range(3)]
    ids = [record.json()["data"]["id"] for record in records]
    response = await client.get(
        BASE,
        headers=headers(),
        params={
            "lenh_san_xuat_id": 100,
            "nhan_vien_id": 2,
            "sort": "-id",
            "page": 2,
            "page_size": 1,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["meta"]["total"] == 3
    assert response.json()["data"][0]["id"] == ids[1]
    assert "etag" not in response.headers
    empty = await client.get(BASE, headers=headers(), params={"q": "%_"})
    assert empty.json()["data"] == []
    assert (await client.get(BASE, headers=headers(1))).status_code == 403
    duplicate = await client.post(
        records[0].headers["location"] + "/gui",
        headers=[
            *headers().items(),
            ("If-Match", records[0].headers["etag"]),
            ("If-Match", records[0].headers["etag"]),
        ],
        json={},
    )
    assert duplicate.status_code == 422


async def test_mat_hang_price_is_required_integer_vnd_in_api_and_bootstrap(context):
    client, sessions, headers, _ = context
    cache = MatHangCache()
    async with sessions() as db:
        cache.replace(await SqlAlchemyMatHangRepository(db).load_all())
        columns = (
            await db.execute(
                text(
                    "SELECT table_name,column_name,data_type,is_nullable FROM information_schema.columns WHERE table_schema=current_schema() AND ((table_name='MatHang' AND column_name='don_gia') OR (table_name='PhieuXuat' AND column_name='tong_tien') OR (table_name='ChiTietPhieuXuat' AND column_name IN ('don_gia_thuc','tong_gia')))"
                )
            )
        ).all()
        assert len(columns) == 4 and all(row.data_type == "bigint" for row in columns)
        assert next(row for row in columns if row.table_name == "MatHang").is_nullable == "NO"
    app.dependency_overrides[get_mat_hang_cache] = lambda: cache
    detail = await client.get("/api/v1/mat_hang/8", headers=headers())
    assert detail.status_code == 200, detail.text
    assert isinstance(detail.json()["data"]["don_gia"], int)
    for price in (None, 1.5, "100", True):
        response = await client.patch(
            "/api/v1/mat_hang/8",
            headers={**headers(), "If-Match": detail.headers["etag"]},
            json={"don_gia": price},
        )
        assert response.status_code == 422, response.text
    response = await client.patch(
        "/api/v1/mat_hang/8",
        headers={**headers(), "If-Match": detail.headers["etag"]},
        json={"don_gia": 3000000000},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["don_gia"] == 3000000000


async def test_concurrent_patch_rejects_stale_update_and_deleted_codes_are_not_reused(context):
    client, _, headers, _ = context
    created = await create(context)
    path = created.headers["location"]
    results = await asyncio.gather(
        *[
            client.patch(
                path,
                headers={**headers(), "If-Match": created.headers["etag"]},
                json={"chi_tiet": [{"mat_hang_id": 8, "so_luong": qty}]},
            )
            for qty in (4, 5)
        ]
    )
    assert sorted(response.status_code for response in results) == [200, 412], [
        r.text for r in results
    ]
    changed = next(response for response in results if response.status_code == 200)
    assert (
        await client.delete(path, headers={**headers(), "If-Match": changed.headers["etag"]})
    ).status_code == 204
    replacement = await create(context)
    assert replacement.json()["data"]["ma_phieu_xuat"] != created.json()["data"]["ma_phieu_xuat"]


async def test_finished_goods_audit_failure_rolls_back_request_progress(context):
    client, sessions, headers, engine = context
    created = await create(
        context,
        {
            "loai_phieu": "xuat_thanh_pham",
            "yeu_cau_san_xuat_id": 100,
            "chi_tiet": [{"mat_hang_id": 1, "so_luong": 10}],
        },
    )
    sent = await submit(context, created)

    def fail(conn, cursor, statement, parameters, execution_context, many):
        if 'insert into "lichsuthaotac"' in statement.lower():
            raise RuntimeError("private audit failure")

    event.listen(engine.sync_engine, "before_cursor_execute", fail)
    try:
        result = await client.post(
            created.headers["location"] + "/duyet",
            headers={**headers(), "If-Match": sent.headers["etag"]},
            json={},
        )
        assert result.status_code == 500, result.text
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", fail)
    async with sessions() as db:
        assert (
            await db.scalar(text('SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=100')) == "da_gui"
        )
        assert (
            await db.scalar(text('SELECT completed_at FROM "YeuCauSanXuat" WHERE id=100')) is None
        )
        assert await db.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=1')) == 10
    detail = await client.get(created.headers["location"], headers=headers())
    assert detail.headers["etag"] == sent.headers["etag"]


@pytest.mark.parametrize("posted", [False, True])
async def test_production_issue_helpers_remain_atomic(context, posted):
    client, sessions, headers, _ = context
    draft = await create(context)
    waiting = await create(context)
    submitted = await submit(context, waiting)
    if posted:
        result = await client.post(
            waiting.headers["location"] + "/duyet",
            headers={**headers(), "If-Match": submitted.headers["etag"]},
            json={},
        )
        assert result.status_code == 200, result.text
    async with sessions() as db:
        transaction = SqlAlchemyTransaction(db)
        service = PhieuXuatService(
            SqlAlchemyPhieuXuatRepository(db),
            AuditService(SqlAlchemyAuditRepository(db)),
            transaction,
            SqlAlchemyInventoryRepository(db),
        )
        if posted:
            with pytest.raises(PostedProductionDependency):
                async with transaction:
                    await service.huy_phieu_chua_ghi_so(100, [100], "Cancel production", 2)
        else:
            async with transaction:
                await service.huy_phieu_chua_ghi_so(100, [100], "Cancel production", 2)
    assert (await client.get(draft.headers["location"], headers=headers())).status_code == (
        200 if posted else 404
    )
    detail = await client.get(waiting.headers["location"], headers=headers())
    assert detail.json()["data"]["trang_thai"] == ("da_duyet" if posted else "tu_choi")
