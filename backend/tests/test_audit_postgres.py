"""UC-43 real PostgreSQL tests; never use the configured application database.

Set AUDIT_TEST_DATABASE_URL to an empty dedicated *_test database on a local
test-only server owned by uc43_test. Every case creates/drops its own UUID DB.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import get_args
from uuid import uuid4

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from test_audit_api import auth_headers

from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.models import LichSuThaoTac
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.router import router
from app.modules.audit.schemas import AuditListQuery, AuditObject, CreationAudit, ThaoTac
from app.modules.audit.service import AuditService

BOOTSTRAP = Path(__file__).resolve().parents[2] / "infra/postgres/init.sql"
EVIDENCE = {
    "danh_sach_thieu": [{"mat_hang_id": 1, "ten_mat_hang": "Frame", "so_luong_thieu": 10}],
    "nested": [{"passwordHash": "never-return-this", "quantity": 10}],
}


@pytest.fixture
async def database():
    configured = os.environ.get("AUDIT_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("UC-43 PostgreSQL not verified: AUDIT_TEST_DATABASE_URL is required")
    url = make_url(configured)
    if not (
        url.drivername == "postgresql+asyncpg"
        and url.host in ("127.0.0.1", "localhost")
        and url.username == "uc43_test"
        and url.database
        and url.database.endswith("_test")
    ):
        pytest.fail("Refusing database not identified as a local uc43_test test server")
    name = f"uc43_{uuid4().hex}_test"
    test_url = url.set(database=name)
    admin = await asyncpg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    engine = None
    raw = None
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        raw = await asyncpg.connect(
            test_url.set(drivername="postgresql").render_as_string(hide_password=False)
        )
        assert (
            await raw.fetchval(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
            )
            == 0
        )
        await raw.execute(BOOTSTRAP.read_text(encoding="utf-8"))
        await raw.execute("""
            INSERT INTO "VaiTro" (id, ma_vai_tro, ten_vai_tro) VALUES
                (1, 'quan_tri_vien', 'Admin'), (2, 'quan_ly', 'Manager'), (3, 'nhan_vien', 'Employee');
            INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien)
                VALUES (1, 1, 'admin', 'test-credential-hash', 'NV-000001'),
                       (2, 2, 'manager', 'test-credential-hash', 'NV-000002'),
                       (3, 3, 'employee', 'test-credential-hash', 'NV-000003');
            INSERT INTO "MatHang" (id, ma_mat_hang, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, so_luong_ton)
                VALUES (1, 'MH-000001', 'Frame', 'FRAME-01', 'linh_kien', 'piece', 100, 5);
        """)
        rows = [
            (1, 1, "cong_thuc", 10, "tao_phien_ban", "2026-11-13T16:59:59+00:00", "before day"),
            (
                2,
                2,
                "cong_thuc",
                10,
                "tao_phien_ban",
                "2026-11-13T17:00:00+00:00",
                "literal 50%_x\\path",
            ),
            (3, 2, "cong_thuc", 10, "sua", "2026-11-14T01:00:00+00:00", "changed"),
            (4, 1, "mat_hang", 1, "sua", "2026-11-14T01:00:00+00:00", None),
            (
                5,
                2,
                "cong_thuc",
                10,
                "tao_phien_ban",
                "2026-11-14T16:59:59.999999+00:00",
                "end of day",
            ),
            (6, 2, "cong_thuc", 10, "tao_phien_ban", "2026-11-14T17:00:00+00:00", "next day"),
            (7, 2, "yeu_cau_san_xuat", 20, "kiem_tra", "2026-11-14T01:00:00+00:00", None),
            (8, 2, "nhan_vien", 2, "doi_mat_khau", "2026-11-14T01:00:00+00:00", None),
        ]
        await raw.executemany(
            """INSERT INTO "LichSuThaoTac"
            (id, nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, created_at, ly_do, du_lieu_truoc, du_lieu_sau, trang_thai_truoc, trang_thai_sau)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9::jsonb,$10,$11)""",
            [
                (
                    *row[:5],
                    datetime.fromisoformat(row[5]),
                    row[6],
                    json.dumps({"name": "before", "token": "hidden-token"})
                    if row[0] == 3
                    else None,
                    json.dumps(EVIDENCE) if row[0] == 7 else None,
                    "da_gui" if row[0] == 7 else None,
                    "cho_bo_sung_linh_kien" if row[0] == 7 else None,
                )
                for row in rows
            ],
        )
        await raw.execute("SELECT setval(pg_get_serial_sequence('\"LichSuThaoTac\"', 'id'), 8)")
        await raw.close()
        raw = None
        engine = create_async_engine(test_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        statements = []
        event.listen(
            engine.sync_engine,
            "before_cursor_execute",
            lambda _c, _cur, statement, _p, _ctx, _many: statements.append(statement),
        )
        async with factory() as session:
            yield SimpleNamespace(
                engine=engine,
                factory=factory,
                session=session,
                service=AuditService(SqlAlchemyAuditRepository(session)),
                statements=statements,
            )
    finally:
        if raw is not None:
            await raw.close()
        if engine is not None:
            await engine.dispose()
        # Only the UUID database created by this fixture can be dropped.
        assert name.startswith("uc43_") and name.endswith("_test") and len(name) == 42
        try:
            await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        finally:
            await admin.close()


async def read(database, **query):
    return await database.service.list_entries(AuditListQuery(**query), {"roles": ["quan_ly"]})


async def test_uc43_ac05_ac06_ac10_all_filters_are_anded_before_count(database):
    result = await read(
        database,
        nhan_vien_id=2,
        loai_doi_tuong="cong_thuc",
        doi_tuong_id=10,
        thao_tac="tao_phien_ban",
        tu_ngay="2026-11-14",
        den_ngay="2026-11-14",
        page_size=1,
        sort_by="id",
        sort_order="asc",
    )
    assert [entry.id for entry in result.data] == [2]
    assert result.pagination.total_items == 2 and result.pagination.total_pages == 2
    second = await read(
        database,
        nhan_vien_id=2,
        loai_doi_tuong="cong_thuc",
        doi_tuong_id=10,
        thao_tac="tao_phien_ban",
        tu_ngay="2026-11-14",
        den_ngay="2026-11-14",
        page_size=1,
        sort_by="id",
        sort_order="asc",
        page=2,
    )
    assert [entry.id for entry in second.data] == [5]


async def test_uc43_ac11_inclusive_vietnamese_day_boundaries_and_open_ends(database):
    single = await read(database, tu_ngay="2026-11-14", den_ngay="2026-11-14")
    assert {entry.id for entry in single.data} == {2, 3, 4, 5, 7, 8}
    since = await read(database, tu_ngay="2026-11-14")
    assert {entry.id for entry in since.data} == {2, 3, 4, 5, 6, 7, 8}
    until = await read(database, den_ngay="2026-11-14")
    assert {entry.id for entry in until.data} == {1, 2, 3, 4, 5, 7, 8}


@pytest.mark.parametrize(
    "search,ids",
    [
        ("%_x\\path", [2]),
        ("50%", [2]),
        ("BEFORE DAY", [1]),
        ("' OR 1=1 --", []),
        ("hidden-token", []),
    ],
)
async def test_uc43_ac10_search_is_literal_case_insensitive_not_json(database, search, ids):
    result = await read(database, search=search)
    assert [entry.id for entry in result.data] == ids


@pytest.mark.parametrize("order", ["asc", "desc"])
async def test_uc43_ac12_stable_pagination_tied_timestamps(database, order):
    result_ids = []
    for page in range(1, 5):
        result = await read(database, page=page, page_size=2, sort_order=order)
        assert result.pagination.total_items == 8
        result_ids.extend(entry.id for entry in result.data)
    expected = [1, 2, 3, 4, 7, 8, 5, 6]
    assert result_ids == (expected if order == "asc" else list(reversed(expected)))
    beyond = await read(database, page=10**30, page_size=100)
    assert beyond.data == [] and beyond.pagination.total_items == 8


async def test_uc43_ac10_legacy_exclusion_and_conflicting_filters(database):
    legacy = await read(database, bo_thao_tac="thu_hoi_quyen")
    assert legacy.pagination.total_items == 8
    conflict = await read(database, thao_tac="tao", bo_thao_tac="tao")
    assert conflict.data == [] and conflict.pagination.total_items == 0
    excluded = await read(database, bo_thao_tac="tao_phien_ban")
    assert {entry.id for entry in excluded.data} == {3, 4, 7, 8}


async def test_uc43_ac01_ac04_ac14_ac15_snapshot_does_not_follow_current_stock(database):
    detail = await database.service.get_entry(7, {"roles": ["quan_tri_vien"]})
    await database.session.execute(text('UPDATE "MatHang" SET so_luong_ton=100 WHERE id=1'))
    await database.session.commit()
    reread = await database.service.get_entry(7, {"roles": ["quan_ly"]})
    assert reread == detail
    assert reread.data.du_lieu_sau["danh_sach_thieu"][0]["so_luong_thieu"] == 10
    assert reread.data.du_lieu_sau["nested"] == [{"quantity": 10}]
    raw = await database.session.scalar(text('SELECT du_lieu_sau FROM "LichSuThaoTac" WHERE id=7'))
    assert raw["nested"][0]["passwordHash"] == "never-return-this"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE \"LichSuThaoTac\" SET ly_do='tamper' WHERE id=1",
        'DELETE FROM "LichSuThaoTac" WHERE id=1',
    ],
)
async def test_uc43_ac02_ac16_database_trigger_blocks_mutation(database, sql):
    async with database.session.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="LichSuThaoTac"):
            await database.session.execute(text(sql))
        await savepoint.rollback()
    assert await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == 8
    assert (
        await database.session.scalar(text('SELECT ly_do FROM "LichSuThaoTac" WHERE id=1'))
        == "before day"
    )


async def test_uc43_ac17_append_rolls_back_with_callers_operation(database):
    before = await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"'))
    with pytest.raises(RuntimeError, match="simulate failure"):
        async with SqlAlchemyTransaction(database.session):
            await database.session.execute(text('UPDATE "MatHang" SET so_luong_ton=123 WHERE id=1'))
            await database.service.append(
                CreationAudit(
                    nhan_vien_id=1,
                    loai_doi_tuong="mat_hang",
                    doi_tuong_id=1,
                    du_lieu_sau={"so_luong_ton": 123},
                )
            )
            await database.session.flush()
            raise RuntimeError("simulate failure")
    assert await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == before
    assert await database.session.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=1')) == 5


async def test_uc43_ac17_append_commits_only_when_caller_commits(database):
    async with SqlAlchemyTransaction(database.session):
        await database.service.append(
            CreationAudit(
                nhan_vien_id=1,
                loai_doi_tuong="mat_hang",
                doi_tuong_id=1,
                du_lieu_sau=None,
                trang_thai_truoc=None,
                trang_thai_sau=None,
            )
        )
    async with database.factory() as independent:
        assert await independent.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == 9


async def test_uc43_ac07_ac09_ac17_http_reads_with_real_auth_repository_are_read_only(database):
    async def test_session():
        async with database.factory() as session:
            yield session

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = test_session
    before = await database.session.scalar(
        text('SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM "LichSuThaoTac" t')
    )
    database.statements.clear()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        for employee_id in (1, 2):
            for path in ("/api/v1/audit", "/api/v1/audit/7"):
                response = await client.get(path, headers=auth_headers(employee_id))
                assert response.status_code == 200, response.text
                assert "never-return-this" not in response.text
        assert (await client.get("/api/v1/audit", headers=auth_headers(3))).status_code == 403
        await database.session.execute(
            text("UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=2")
        )
        await database.session.commit()
        assert (await client.get("/api/v1/audit", headers=auth_headers(2))).status_code == 403
    after = await database.session.scalar(
        text('SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM "LichSuThaoTac" t')
    )
    assert before == after
    assert await database.session.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=1')) == 5
    writes = [sql for sql in database.statements if not sql.lstrip().upper().startswith("SELECT")]
    assert len(writes) == 1 and writes[0].startswith('UPDATE "NhanVien"')


async def test_uc43_schema_matches_bootstrap_audit_table(database):
    async with database.engine.connect() as connection:

        def compare(sync):
            inspector = inspect(sync)
            columns = {column["name"]: column for column in inspector.get_columns("LichSuThaoTac")}
            table = LichSuThaoTac.__table__
            assert set(columns) == set(table.columns.keys())
            for column in table.columns:
                reflected = columns[column.name]
                assert column.nullable == reflected["nullable"]
                assert column.type.compile(dialect=sync.dialect) == reflected["type"].compile(
                    dialect=sync.dialect
                )
                assert bool(column.identity) == bool(reflected.get("identity"))
                if column.identity:
                    assert reflected["identity"]["always"] == column.identity.always
                if column.server_default and not column.identity:
                    assert str(column.server_default.arg).lower() in reflected["default"].lower()
            assert inspector.get_pk_constraint("LichSuThaoTac")["constrained_columns"] == ["id"]
            assert {
                check["name"] for check in inspector.get_check_constraints("LichSuThaoTac")
            } == {
                constraint.name
                for constraint in table.constraints
                if constraint.__class__.__name__ == "CheckConstraint"
            }
            checks = {
                check["name"]: check["sqltext"]
                for check in inspector.get_check_constraints("LichSuThaoTac")
            }
            for name, values in (
                ("ck_lstt_loai_doi_tuong", get_args(AuditObject)),
                ("ck_lstt_thao_tac", get_args(ThaoTac)),
            ):
                assert set(re.findall(r"'([^']+)'", checks[name])) == set(values)
            assert {
                (index["name"], tuple(index["column_names"]))
                for index in inspector.get_indexes("LichSuThaoTac")
            } == {
                (index.name, tuple(column.name for column in index.columns))
                for index in table.indexes
            }
            foreign = inspector.get_foreign_keys("LichSuThaoTac")
            assert len(foreign) == 1
            assert foreign[0]["constrained_columns"] == ["nhan_vien_id"]
            assert foreign[0]["referred_table"] == "NhanVien" and foreign[0][
                "referred_columns"
            ] == ["id"]
            assert foreign[0]["options"]["deferrable"] is True
            assert foreign[0]["options"].get("initially", "IMMEDIATE") == "IMMEDIATE"

        await connection.run_sync(compare)


@pytest.mark.parametrize(
    "action", ["tao_phien_ban", "kiem_tra", "doi_mat_khau", "gui_lai", "dung_lai_phien_ban"]
)
async def test_uc43_ac05_v4_actions_are_readable(database, action):
    async with SqlAlchemyTransaction(database.session):
        await database.service.append(
            CreationAudit(
                nhan_vien_id=1,
                loai_doi_tuong="cong_thuc",
                doi_tuong_id=10,
                thao_tac=action,
                du_lieu_sau=None,
            )
        )
    response = await read(database, thao_tac=action)
    assert response.pagination.total_items >= 1
    assert all(row.thao_tac == action for row in response.data)
