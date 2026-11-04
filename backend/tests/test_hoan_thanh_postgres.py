"""Run explicitly against a PostgreSQL server; creates a fresh *_test database only.

python -m pytest tests/test_hoan_thanh_postgres.py -q
No application tables are changed, and test databases are retained for inspection.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import configure_mappers

from app import models  # noqa: F401
from app.config.settings import settings
from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.main import app
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.san_xuat.repository import SqlAlchemyHoanThanhRepository
from app.modules.san_xuat.service import ChungTuHoanThanhService

BASE = "/api/v1/chung_tu_hoan_thanh_sx"
ROOT = Path(__file__).resolve().parents[2]
FINISH = "2026-11-03T12:00:00+07:00"
Q = {"sub": "2", "roles": ["quan_ly"]}


@pytest.fixture(scope="module")
def database_url():
    async def bootstrap():
        source = make_url(os.environ.get("HOAN_THANH_TEST_SERVER_URL", settings.database_url))
        name = f"xbike_hoan_thanh_{uuid4().hex[:10]}_test"
        assert name.endswith("_test") and name != source.database
        admin = await asyncpg.connect(
            source.set(drivername="postgresql", database="postgres").render_as_string(
                hide_password=False
            ),
            timeout=5,
        )
        try:
            assert not await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", name)
            await admin.execute(f'CREATE DATABASE "{name}"')
        finally:
            await admin.close()
        target = source.set(database=name)
        connection = await asyncpg.connect(
            target.set(drivername="postgresql").render_as_string(hide_password=False)
        )
        try:
            assert (
                await connection.fetchval(
                    "SELECT count(*) FROM pg_tables WHERE schemaname='public'"
                )
                == 0
            )
            await connection.execute((ROOT / "infra/postgres/init.sql").read_text(encoding="utf-8"))
            await connection.execute((ROOT / "infra/postgres/seed.sql").read_text(encoding="utf-8"))
        finally:
            await connection.close()
        print("ISOLATED_TEST_DATABASE:", name)
        return target

    return asyncio.run(bootstrap())


@pytest.fixture
async def engine(database_url):
    engine = create_async_engine(database_url, hide_parameters=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    async with engine.connect() as connection:
        transaction = await connection.begin()
        sessions = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with sessions() as session:
            yield session
        await transaction.rollback()


async def scalar(session, sql, **params):
    return await session.scalar(text(sql), params)


async def headers(session, actor=3):
    hashed = await scalar(session, 'SELECT mat_khau FROM "NhanVien" WHERE id=:id', id=actor)
    token = create_access_token(
        actor, roles=["untrusted_role"], credential_version=password_version(hashed)
    )
    return {"Authorization": f"Bearer {token}"}


@asynccontextmanager
async def client_for(session):
    saved = app.dependency_overrides.copy()

    async def db():
        yield session

    app.dependency_overrides[get_db] = db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


async def request(client, method, path, expected, **kwargs):
    response = await client.request(method, path, **kwargs)
    assert response.status_code == expected, (method, path, response.status_code, response.text)
    return response


async def make_order(session, *, item_id=1, quantity=10, supplied=True, request_id=None):
    if request_id is None:
        request_id = await scalar(
            session,
            """
            INSERT INTO "YeuCauSanXuat" (ma_yeu_cau_san_xuat, mat_hang_id, so_luong,
                nhan_vien_id, nhan_vien_duoc_giao_id, trang_thai)
            VALUES ('YCSX-202611-' || lpad(nextval(pg_get_serial_sequence('"YeuCauSanXuat"','id'))::text,6,'0'),
                1, 10, 2, 3, 'dang_thuc_hien') RETURNING id
        """,
        )
    order_id = await scalar(
        session,
        """
        INSERT INTO "LenhSanXuat" (ma_lenh_san_xuat, yeu_cau_san_xuat_id, mat_hang_id,
            bom_id, so_luong, nhan_vien_id, trang_thai, started_at)
        VALUES ('LSX-202611-' || lpad(nextval(pg_get_serial_sequence('"LenhSanXuat"','id'))::text,6,'0'),
            :request_id, :item_id, :bom_id, :quantity, 3, 'dang_thuc_hien', '2026-11-01T00:00:00Z') RETURNING id
    """,
        request_id=request_id,
        item_id=item_id,
        bom_id=item_id,
        quantity=quantity,
    )
    await session.execute(
        text(
            'INSERT INTO "ChiTietLenhSanXuat" (lenh_san_xuat_id, mat_hang_id, so_luong_can) VALUES (:id,6,1)'
        ),
        {"id": order_id},
    )
    if supplied:
        issue_id = await scalar(
            session,
            """
            INSERT INTO "PhieuXuat" (ma_phieu_xuat, nhan_vien_id, loai_phieu, lenh_san_xuat_id)
            VALUES ('PX-202611-' || lpad(nextval(pg_get_serial_sequence('"PhieuXuat"','id'))::text,6,'0'),
                2, 'xuat_vat_tu', :order_id) RETURNING id
        """,
            order_id=order_id,
        )
        line_id = await scalar(
            session,
            """
            INSERT INTO "ChiTietPhieuXuat" (phieu_xuat_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
            VALUES (:id,6,1,1800000,1800000) RETURNING id
        """,
            id=issue_id,
        )
        await session.execute(
            text("UPDATE \"PhieuXuat\" SET trang_thai='da_duyet',tong_tien=1800000 WHERE id=:id"),
            {"id": issue_id},
        )
        await session.execute(
            text("""INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,chi_tiet_phieu_xuat_id,nhan_vien_id)
            VALUES (6,'xuat_vat_tu',-1,:id,2)"""),
            {"id": line_id},
        )
        await session.execute(
            text(
                'UPDATE "MatHang" SET so_luong_ton=so_luong_ton-1,ton_kho_updated_at=now() WHERE id=6'
            )
        )
    return request_id, order_id


async def draft(client, session, order_id, quantity):
    response = await request(
        client,
        "POST",
        BASE,
        201,
        json={"lenh_san_xuat_id": order_id, "so_luong_hoan_thanh": quantity, "finish_time": FINISH},
        headers=await headers(session),
    )
    assert response.headers["location"] == f"{BASE}/{response.json()['data']['id']}"
    return response.json()["data"]["id"], response.headers["etag"]


async def submit(client, session, document_id, tag):
    response = await request(
        client,
        "POST",
        f"{BASE}/{document_id}/gui",
        200,
        json={},
        headers={**await headers(session), "If-Match": tag},
    )
    return response.headers["etag"]


async def test_openapi_and_mappers():
    configure_mappers()
    paths = app.openapi()["paths"]
    assert sum(len(methods) for path, methods in paths.items() if path.startswith(BASE)) == 9
    assert (
        sum(
            len(methods)
            for path, methods in paths.items()
            if path.startswith("/api/v1/yeu_cau_san_xuat")
        )
        == 9
    )


@pytest.mark.parametrize("item_id", [1, 5])
async def test_multiple_batches_post_once_and_complete_only_order(session, item_id):
    request_id, order_id = await make_order(session, item_id=item_id)
    initial_stock = await scalar(
        session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=:id', id=item_id
    )
    material_stock = await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=6')
    async with client_for(session) as client:
        a, tag_a = await draft(client, session, order_id, 3)
        b, tag_b = await draft(client, session, order_id, 7)
        assert (
            await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=:id', id=item_id)
            == initial_stock
        )
        tag_a = await submit(client, session, a, tag_a)
        tag_b = await submit(client, session, b, tag_b)
        ids = []
        for document_id, tag, expected_state in [
            (a, tag_a, "dang_thuc_hien"),
            (b, tag_b, "hoan_thanh"),
        ]:
            result = await request(
                client,
                "POST",
                f"{BASE}/{document_id}/duyet",
                200,
                json={},
                headers={**await headers(session, 2), "If-Match": tag},
            )
            action = result.json()["data"]
            assert not action["da_ghi_so_truoc_do"] and action["nhan_vien_id"] == 3
            ids += action["giao_dich_kho_ids"]
            assert (
                await scalar(
                    session, 'SELECT trang_thai FROM "LenhSanXuat" WHERE id=:id', id=order_id
                )
                == expected_state
            )
            audits = await scalar(session, 'SELECT count(*) FROM "LichSuThaoTac"')
            retry = await request(
                client,
                "POST",
                f"{BASE}/{document_id}/duyet",
                200,
                json={},
                headers={**await headers(session, 2), "If-Match": tag},
            )
            assert retry.json()["data"]["da_ghi_so_truoc_do"]
            assert retry.json()["data"]["giao_dich_kho_ids"] == action["giao_dich_kho_ids"]
            assert retry.headers["etag"] == result.headers["etag"]
            assert await scalar(session, 'SELECT count(*) FROM "LichSuThaoTac"') == audits
        assert len(set(ids)) == 2
        assert (
            await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=:id', id=item_id)
            == initial_stock + 10
        )
        assert (
            await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=6') == material_stock
        )
        assert (
            await scalar(
                session, 'SELECT trang_thai FROM "YeuCauSanXuat" WHERE id=:id', id=request_id
            )
            == "dang_thuc_hien"
        )
        assert (
            await scalar(
                session, 'SELECT completed_at FROM "LenhSanXuat" WHERE id=:id', id=order_id
            )
            is not None
        )
        assert await scalar(
            session,
            'SELECT bool_and(nhan_vien_id=2) FROM "GiaoDichKho" WHERE chung_tu_hoan_thanh_sx_id IN (:a,:b)',
            a=a,
            b=b,
        )


async def test_draft_transitions_and_delete_do_not_post(session):
    _, order_id = await make_order(session)
    async with client_for(session) as client:
        before = await scalar(session, 'SELECT count(*) FROM "GiaoDichKho"')
        document_id, tag = await draft(client, session, order_id, 3)
        path = f"{BASE}/{document_id}"
        noop = await request(
            client,
            "PATCH",
            path,
            200,
            json={"so_luong_hoan_thanh": 3},
            headers={**await headers(session), "If-Match": tag},
        )
        assert noop.headers["etag"] == tag
        assert (
            await scalar(
                session,
                "SELECT count(*) FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='chung_tu_hoan_thanh_san_xuat' AND doi_tuong_id=:id",
                id=document_id,
            )
            == 1
        )
        patched = await request(
            client,
            "PATCH",
            path,
            200,
            json={"so_luong_hoan_thanh": 4},
            headers={**await headers(session), "If-Match": tag},
        )
        tag = await submit(client, session, document_id, patched.headers["etag"])
        rejected = await request(
            client,
            "POST",
            path + "/tu_choi",
            200,
            json={"ly_do": "  cần sửa  "},
            headers={**await headers(session, 2), "If-Match": tag},
        )
        returned = await request(
            client,
            "POST",
            path + "/ve_nhap",
            200,
            json={"ly_do": "sửa lại"},
            headers={**await headers(session), "If-Match": rejected.headers["etag"]},
        )
        await request(
            client,
            "DELETE",
            path,
            204,
            headers={**await headers(session), "If-Match": returned.headers["etag"]},
        )
        await request(client, "GET", path, 404, headers=await headers(session))
        assert await scalar(session, 'SELECT count(*) FROM "GiaoDichKho"') == before
        assert await scalar(
            session,
            "SELECT du_lieu_sau IS NULL FROM \"LichSuThaoTac\" WHERE thao_tac='xoa_nhap' AND loai_doi_tuong='chung_tu_hoan_thanh_san_xuat' AND doi_tuong_id=:id",
            id=document_id,
        )


@pytest.mark.parametrize("failure", ["state", "stock", "ledger", "audit", "flush", "commit"])
async def test_approval_failure_rolls_back_every_effect(session, failure, monkeypatch):
    _, order_id = await make_order(session, quantity=3)
    async with client_for(session) as client:
        document_id, tag = await draft(client, session, order_id, 3)
        tag = await submit(client, session, document_id, tag)
        stock = await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=1')
        audits = await scalar(session, 'SELECT count(*) FROM "LichSuThaoTac"')
        repo = SqlAlchemyHoanThanhRepository(session)
        audit = AuditService(SqlAlchemyAuditRepository(session))
        if failure == "state":
            original = repo.update

            async def broken_update(*args):
                await original(*args)
                raise RuntimeError("after state")

            monkeypatch.setattr(repo, "update", broken_update)
        elif failure in {"stock", "ledger"}:
            original = repo.post_output

            async def broken_post(document, actor, posted):
                if failure == "stock":
                    await session.execute(
                        text('UPDATE "MatHang" SET so_luong_ton=so_luong_ton+:qty WHERE id=:id'),
                        {"qty": document.so_luong_hoan_thanh, "id": document.mat_hang_id},
                    )
                else:
                    await original(document, actor, posted)
                raise RuntimeError("after posting")

            monkeypatch.setattr(repo, "post_output", broken_post)
        elif failure == "audit":

            async def broken_audit(entry):
                raise RuntimeError("audit unavailable")

            monkeypatch.setattr(audit, "append", broken_audit)
        else:
            original = getattr(session, failure)

            async def broken(*args, **kwargs):
                if failure == "flush":
                    await original(*args, **kwargs)
                raise RuntimeError("injected " + failure)

            monkeypatch.setattr(session, failure, broken)
        service = ChungTuHoanThanhService(repo, audit, SqlAlchemyTransaction(session))
        with pytest.raises(RuntimeError):
            await service.duyet(document_id, Q, tag, "rollback")
        monkeypatch.undo()
        assert (
            await scalar(
                session, 'SELECT trang_thai FROM "ChungTuHoanThanhSx" WHERE id=:id', id=document_id
            )
            == "cho_duyet"
        )
        assert await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=1') == stock
        assert (
            await scalar(
                session,
                'SELECT count(*) FROM "GiaoDichKho" WHERE chung_tu_hoan_thanh_sx_id=:id',
                id=document_id,
            )
            == 0
        )
        assert (
            await scalar(session, 'SELECT trang_thai FROM "LenhSanXuat" WHERE id=:id', id=order_id)
            == "dang_thuc_hien"
        )
        assert await scalar(session, 'SELECT count(*) FROM "LichSuThaoTac"') == audits


def endpoints(document_id=1):
    path = f"{BASE}/{document_id}"
    return [
        ("GET", BASE, None),
        ("GET", path, None),
        ("POST", BASE, {"lenh_san_xuat_id": 2, "so_luong_hoan_thanh": 1, "finish_time": FINISH}),
        ("PATCH", path, {"so_luong_hoan_thanh": 1}),
        ("DELETE", path, None),
        ("POST", path + "/gui", {}),
        ("POST", path + "/duyet", {}),
        ("POST", path + "/tu_choi", {"ly_do": "test"}),
        ("POST", path + "/ve_nhap", {"ly_do": "test"}),
    ]


async def test_all_endpoints_enforce_current_account_and_role(session):
    async with client_for(session) as client:
        employee = await headers(session)
        admin = await headers(session, 1)
        for auth, expected in [({}, 401), ({"Authorization": "Bearer invalid"}, 401), (admin, 403)]:
            for method, path, body in endpoints():
                await request(
                    client,
                    method,
                    path,
                    expected,
                    headers=auth,
                    **({"json": body} if body is not None else {}),
                )
        await session.execute(text("UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=3"))
        for method, path, body in endpoints():
            await request(
                client,
                method,
                path,
                403,
                headers=employee,
                **({"json": body} if body is not None else {}),
            )
        await session.execute(
            text(
                "UPDATE \"NhanVien\" SET trang_thai='hoat_dong',mat_khau=mat_khau || 'changed' WHERE id=3"
            )
        )
        for method, path, body in endpoints():
            await request(
                client,
                method,
                path,
                401,
                headers=employee,
                **({"json": body} if body is not None else {}),
            )


async def test_roles_scope_and_reassignment_are_enforced(session):
    _, order_id = await make_order(session)
    async with client_for(session) as client:
        document_id, tag = await draft(client, session, order_id, 3)
        path = f"{BASE}/{document_id}"
        for method, url, body in endpoints(document_id):
            if (method, url) in [
                ("POST", BASE),
                ("PATCH", path),
                ("DELETE", path),
                ("POST", path + "/gui"),
                ("POST", path + "/ve_nhap"),
            ]:
                await request(
                    client,
                    method,
                    url,
                    403,
                    headers=await headers(session, 2),
                    **({"json": body} if body is not None else {}),
                )
            elif url in [path + "/duyet", path + "/tu_choi"]:
                await request(client, method, url, 403, json=body, headers=await headers(session))
        await session.execute(
            text("""INSERT INTO "NhanVien" (vai_tro_id,ten_dang_nhap,mat_khau,ma_nhan_vien,ho_ten,ngay_vao_lam,trang_thai)
            VALUES (3,'other_employee','test-hash','NV-000004','Other employee','2026-11-01','hoat_dong')""")
        )
        other_id = await scalar(
            session, "SELECT id FROM \"NhanVien\" WHERE ten_dang_nhap='other_employee'"
        )
        await session.execute(
            text('UPDATE "LenhSanXuat" SET nhan_vien_id=:other WHERE id=:id'),
            {"id": order_id, "other": other_id},
        )
        await request(client, "GET", path, 403, headers=await headers(session))
        await request(
            client, "DELETE", path, 403, headers={**await headers(session), "If-Match": tag}
        )
        # Even the new assignee cannot read a document created by someone else.
        await request(client, "GET", path, 403, headers=await headers(session, other_id))
        page = await request(
            client,
            "GET",
            BASE,
            200,
            params={"lenh_san_xuat_id": order_id},
            headers=await headers(session),
        )
        assert page.json()["data"] == [] and page.json()["meta"]["total"] == 0
        page = await request(
            client,
            "GET",
            BASE,
            200,
            params={"lenh_san_xuat_id": order_id},
            headers=await headers(session, 2),
        )
        assert page.json()["meta"]["total"] == 1


async def test_http_validation_and_precondition_matrix(session):
    _, order_id = await make_order(session)
    async with client_for(session) as client:
        document_id, tag = await draft(client, session, order_id, 3)
        path = f"{BASE}/{document_id}"
        employee, manager = await headers(session), await headers(session, 2)
        for method, url, body in endpoints(document_id):
            auth = manager if url in [path + "/duyet", path + "/tu_choi"] else employee
            kwargs = {"json": body} if body is not None else {}
            await request(
                client, method, url, 422, headers=auth, params={"unsupported": "1"}, **kwargs
            )
            if method in {"PATCH", "DELETE"} or url.startswith(path + "/"):
                await request(client, method, url, 428, headers=auth, **kwargs)
                for stale in [" ", "*", "W/" + tag, '"stale"']:
                    await request(
                        client,
                        method,
                        url,
                        428 if stale == " " else 412,
                        headers={**auth, "If-Match": stale},
                        **kwargs,
                    )
                await request(
                    client,
                    method,
                    url,
                    422,
                    headers=[*auth.items(), ("If-Match", tag), ("If-Match", tag)],
                    **kwargs,
                )
        for params in [
            [("page", "1"), ("page", "2")],
            {"sort": "-created_at"},
            {"unknown": "1"},
            {"tu_ngay": "2026-11-04", "den_ngay": "2026-11-03"},
        ]:
            await request(client, "GET", BASE, 422, headers=employee, params=params)
        for payload in [
            {},
            {"finish_time": None},
            {"so_luong_hoan_thanh": True},
            {"ma_phieu": "HACK"},
            {"lenh_san_xuat_id": order_id},
            {"nhan_vien_id": 2},
        ]:
            await request(
                client, "PATCH", path, 422, json=payload, headers={**employee, "If-Match": tag}
            )
        for action in ["gui", "duyet"]:
            await request(
                client,
                "POST",
                path + "/" + action,
                422,
                json={"extra": 1},
                headers={**(manager if action == "duyet" else employee), "If-Match": tag},
            )
        for action in ["tu_choi", "ve_nhap"]:
            for payload in [{}, {"ly_do": "  "}, {"ly_do": None}]:
                await request(
                    client,
                    "POST",
                    path + "/" + action,
                    422,
                    json=payload,
                    headers={**(manager if action == "tu_choi" else employee), "If-Match": tag},
                )
        for missing in [2147483647, 2147483648]:
            for method, url, body in endpoints(missing):
                if url == BASE:
                    continue
                auth = manager if url.endswith(("/duyet", "/tu_choi")) else employee
                await request(
                    client,
                    method,
                    url,
                    404,
                    headers={**auth, "If-Match": tag},
                    **({"json": body} if body is not None else {}),
                )


async def test_local_date_filter_null_history_and_literal_search(session):
    _, order_id = await make_order(session)
    async with client_for(session) as client:
        ids = []
        for finish in [
            "2026-11-02T16:59:59Z",
            "2026-11-02T17:00:00Z",
            "2026-11-03T16:59:59Z",
            "2026-11-03T17:00:00Z",
        ]:
            response = await request(
                client,
                "POST",
                BASE,
                201,
                json={
                    "lenh_san_xuat_id": order_id,
                    "so_luong_hoan_thanh": 1,
                    "finish_time": finish,
                },
                headers=await headers(session),
            )
            ids.append(response.json()["data"]["id"])
        document_id, _ = await draft(client, session, order_id, 1)
        await session.execute(
            text('UPDATE "ChungTuHoanThanhSx" SET finish_time=NULL WHERE id=:id'),
            {"id": document_id},
        )
        detail = await request(
            client, "GET", f"{BASE}/{document_id}", 200, headers=await headers(session)
        )
        assert detail.json()["data"]["finish_time"] is None
        await request(
            client,
            "POST",
            f"{BASE}/{document_id}/gui",
            409,
            json={},
            headers={**await headers(session), "If-Match": detail.headers["etag"]},
        )
        common = {"lenh_san_xuat_id": order_id, "sort": "finish_time", "page_size": 2}
        all_rows = await request(
            client,
            "GET",
            BASE,
            200,
            params={**common, "page_size": 100},
            headers=await headers(session),
        )
        assert all_rows.json()["data"][-1]["id"] == document_id
        filtered = await request(
            client,
            "GET",
            BASE,
            200,
            params={**common, "tu_ngay": "2026-11-03", "den_ngay": "2026-11-03"},
            headers=await headers(session),
        )
        assert [row["id"] for row in filtered.json()["data"]] == ids[1:3]
        assert filtered.json()["meta"]["total"] == 2
        wildcard = await request(
            client, "GET", BASE, 200, params={**common, "q": "%"}, headers=await headers(session)
        )
        assert wildcard.json()["meta"]["total"] == 0


@pytest.mark.parametrize(
    "condition,code",
    [
        ("materials", "chua_du_vat_tu_da_cap"),
        ("exceeded", "vuot_so_luong_hoan_thanh"),
        ("inactive", "mat_hang_ngung_hoat_dong"),
        ("balance", "trang_thai_khong_hop_le"),
    ],
)
async def test_approval_business_failures_leave_pending_without_posting(session, condition, code):
    _, order_id = await make_order(session, supplied=condition != "materials")
    async with client_for(session) as client:
        document_id, tag = await draft(client, session, order_id, 7)
        tag = await submit(client, session, document_id, tag)
        if condition == "exceeded":
            other, other_tag = await draft(client, session, order_id, 4)
            other_tag = await submit(client, session, other, other_tag)
            await request(
                client,
                "POST",
                f"{BASE}/{other}/duyet",
                200,
                json={},
                headers={**await headers(session, 2), "If-Match": other_tag},
            )
        elif condition == "inactive":
            await session.execute(text('UPDATE "MatHang" SET is_active=false WHERE id=1'))
        elif condition == "balance":
            await session.execute(text('UPDATE "MatHang" SET so_luong_ton=123 WHERE id=1'))
        stock = await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=1')
        response = await request(
            client,
            "POST",
            f"{BASE}/{document_id}/duyet",
            409,
            json={},
            headers={**await headers(session, 2), "If-Match": tag},
        )
        assert response.json()["error"]["code"] == code
        assert (
            await scalar(
                session, 'SELECT trang_thai FROM "ChungTuHoanThanhSx" WHERE id=:id', id=document_id
            )
            == "cho_duyet"
        )
        assert await scalar(session, 'SELECT so_luong_ton FROM "MatHang" WHERE id=1') == stock
        assert (
            await scalar(
                session,
                'SELECT count(*) FROM "GiaoDichKho" WHERE chung_tu_hoan_thanh_sx_id=:id',
                id=document_id,
            )
            == 0
        )


async def test_future_and_pre_start_time_are_checked_on_send(session):
    _, order_id = await make_order(session)
    async with client_for(session) as client:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = await request(
            client,
            "POST",
            BASE,
            201,
            json={"lenh_san_xuat_id": order_id, "so_luong_hoan_thanh": 1, "finish_time": future},
            headers=await headers(session),
        )
        path = f"{BASE}/{response.json()['data']['id']}"
        await request(
            client,
            "POST",
            path + "/gui",
            422,
            json={},
            headers={**await headers(session), "If-Match": response.headers["etag"]},
        )
        await request(
            client,
            "PATCH",
            path,
            422,
            json={"finish_time": "2026-10-31T23:59:59Z"},
            headers={**await headers(session), "If-Match": response.headers["etag"]},
        )


async def pending_document(session, order_id, quantity):
    from app.modules.san_xuat.schemas import HoanThanhCreate

    service = ChungTuHoanThanhService(
        SqlAlchemyHoanThanhRepository(session),
        AuditService(SqlAlchemyAuditRepository(session)),
        SqlAlchemyTransaction(session),
    )
    actor = {"sub": "3", "roles": ["nhan_vien"]}
    created, tag = await service.create_entry(
        HoanThanhCreate(
            lenh_san_xuat_id=order_id, so_luong_hoan_thanh=quantity, finish_time=FINISH
        ),
        actor,
        "create",
    )
    submitted, tag = await service.gui(created.data.id, actor, tag, "submit")
    return submitted.data.id, tag


async def test_two_connections_cannot_approve_over_order_quantity(engine):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as setup:
        _, order_id = await make_order(setup)
        await setup.commit()
        a = await pending_document(setup, order_id, 7)
        b = await pending_document(setup, order_id, 7)
    ready = asyncio.Event()

    async def approve(document):
        async with sessions() as session:
            service = ChungTuHoanThanhService(
                SqlAlchemyHoanThanhRepository(session),
                AuditService(SqlAlchemyAuditRepository(session)),
                SqlAlchemyTransaction(session),
            )
            await ready.wait()
            try:
                return await service.duyet(document[0], Q, document[1], "concurrent")
            except Exception as error:
                return error

    tasks = [asyncio.create_task(approve(document)) for document in [a, b]]
    ready.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)
    from app.modules.san_xuat.service import HoanThanhExceeded

    assert sum(isinstance(result, HoanThanhExceeded) for result in results) == 1
    assert sum(isinstance(result, tuple) for result in results) == 1
    async with sessions() as check:
        assert (
            await scalar(
                check,
                "SELECT sum(so_luong_hoan_thanh) FROM \"ChungTuHoanThanhSx\" WHERE lenh_san_xuat_id=:id AND trang_thai='da_duyet'",
                id=order_id,
            )
            == 7
        )


async def test_two_orders_sharing_output_do_not_lose_balance_updates(engine):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as setup:
        # Distinct requests ensure only the output lock serializes these approvals.
        orders = [(await make_order(setup, item_id=5, quantity=3))[1] for _ in range(2)]
        await setup.commit()
        documents = [await pending_document(setup, order_id, 3) for order_id in orders]
        initial = await scalar(setup, 'SELECT so_luong_ton FROM "MatHang" WHERE id=5')
    ready = asyncio.Event()

    async def approve(document):
        async with sessions() as session:
            service = ChungTuHoanThanhService(
                SqlAlchemyHoanThanhRepository(session),
                AuditService(SqlAlchemyAuditRepository(session)),
                SqlAlchemyTransaction(session),
            )
            await ready.wait()
            return await service.duyet(document[0], Q, document[1], "shared-output")

    tasks = [asyncio.create_task(approve(document)) for document in documents]
    ready.set()
    results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15)
    assert all(not result[0].data.da_ghi_so_truoc_do for result in results)
    async with sessions() as check:
        assert await scalar(check, 'SELECT so_luong_ton FROM "MatHang" WHERE id=5') == initial + 6
        assert await scalar(
            check,
            'SELECT so_luong_ton=(SELECT sum(so_luong_bien_dong) FROM "GiaoDichKho" WHERE mat_hang_id=5) FROM "MatHang" WHERE id=5',
        )
