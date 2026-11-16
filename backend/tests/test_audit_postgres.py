"""UC-43 on the existing local PostgreSQL schema via TEST_DATABASE_URL.

Missing URL skips; require postgresql+asyncpg and localhost/127.0.0.1.
Default raw/ORM fixture rolls back. The caller-commit and real-session HTTP tests
commit unique setup and leave immutable audit rows plus employees/items in DB.
Never bootstrap, clear data or create/drop a database.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import get_args
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError
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
    "danh_sach_thieu": [{"ten_mat_hang": "Frame", "so_luong_thieu": 10}],
    "nested": [{"passwordHash": "never-return-this", "quantity": 10}],
}


async def seed_audit(database):
    db = database
    db.admin = await db.add_employee("quan_tri_vien", prefix="audit_admin")
    db.manager = await db.add_employee("quan_ly", prefix="audit_manager")
    db.employee = await db.add_employee("nhan_vien", prefix="audit_employee")
    # One unused object ID scopes all eight polymorphic audit examples. Reserve
    # identities until it is absent in existing audit data; never edit seed rows.
    while True:
        item_id = await db.raw.fetchval("SELECT nextval(pg_get_serial_sequence('\"MatHang\"', 'id'))")
        if not await db.raw.fetchval('SELECT EXISTS (SELECT 1 FROM "LichSuThaoTac" WHERE doi_tuong_id=$1)', item_id):
            break
    db.item_id = await db.raw.fetchval('''
        INSERT INTO "MatHang" (id, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, so_luong_ton)
        VALUES ($1, 'Frame', $2, 'linh_kien', 'piece', 100, 5) RETURNING id
    ''', item_id, f"AUDIT_{uuid4().hex}")
    db.evidence = {**EVIDENCE, "danh_sach_thieu": [
        {**EVIDENCE["danh_sach_thieu"][0], "mat_hang_id": db.item_id}
    ]}
    rows = [
        (db.admin["id"], "cong_thuc", "tao_phien_ban", "2026-11-13T16:59:59+00:00", "before day"),
        (db.manager["id"], "cong_thuc", "tao_phien_ban", "2026-11-13T17:00:00+00:00", "literal 50%_x\\path"),
        (db.manager["id"], "cong_thuc", "sua", "2026-11-14T01:00:00+00:00", "changed"),
        (db.admin["id"], "mat_hang", "sua", "2026-11-14T01:00:00+00:00", None),
        (db.manager["id"], "cong_thuc", "tao_phien_ban", "2026-11-14T16:59:59.999999+00:00", "end of day"),
        (db.manager["id"], "cong_thuc", "tao_phien_ban", "2026-11-14T17:00:00+00:00", "next day"),
        (db.manager["id"], "yeu_cau_san_xuat", "kiem_tra", "2026-11-14T01:00:00+00:00", None),
        (db.manager["id"], "nhan_vien", "doi_mat_khau", "2026-11-14T01:00:00+00:00", None),
    ]
    db.audit_ids = []
    for position, (actor, kind, action, at, reason) in enumerate(rows):
        db.audit_ids.append(await db.raw.fetchval('''
            INSERT INTO "LichSuThaoTac"
            (nhan_vien_id, loai_doi_tuong, doi_tuong_id, thao_tac, created_at, ly_do,
             du_lieu_truoc, du_lieu_sau, trang_thai_truoc, trang_thai_sau)
            VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9,$10) RETURNING id
        ''', actor, kind, db.item_id, action, datetime.fromisoformat(at), reason,
            json.dumps({"name": "before", "token": "hidden-token"}) if position == 2 else None,
            json.dumps(db.evidence) if position == 6 else None,
            "da_gui" if position == 6 else None,
            "cho_bo_sung_linh_kien" if position == 6 else None))
    db.service = AuditService(SqlAlchemyAuditRepository(db.session))
    db.statements.clear()
    return db


@pytest.fixture
async def database(postgres_database):
    yield await seed_audit(postgres_database)


@pytest.fixture
async def committed_database(committed_postgres_database):
    # Only the caller-commit and HTTP tests request this fixture. Each leaves
    # three employees, one item and eight audit rows (nine for caller-commit).
    db = await seed_audit(committed_postgres_database)
    await db.connection.commit()
    yield db


async def read(database, **query):
    query.setdefault("doi_tuong_id", database.item_id)
    return await database.service.list_entries(AuditListQuery(**query), {"roles": ["quan_ly"]})


async def test_uc43_ac05_ac06_ac10_all_filters_are_anded_before_count(database):
    result = await read(
        database,
        nhan_vien_id=database.manager["id"],
        loai_doi_tuong="cong_thuc",
        doi_tuong_id=database.item_id,
        thao_tac="tao_phien_ban",
        tu_ngay="2026-11-14",
        den_ngay="2026-11-14",
        page_size=1,
        sort_by="id",
        sort_order="asc",
    )
    assert [entry.id for entry in result.data] == [database.audit_ids[1]]
    assert result.pagination.total_items == 2 and result.pagination.total_pages == 2
    second = await read(
        database,
        nhan_vien_id=database.manager["id"],
        loai_doi_tuong="cong_thuc",
        doi_tuong_id=database.item_id,
        thao_tac="tao_phien_ban",
        tu_ngay="2026-11-14",
        den_ngay="2026-11-14",
        page_size=1,
        sort_by="id",
        sort_order="asc",
        page=2,
    )
    assert [entry.id for entry in second.data] == [database.audit_ids[4]]


async def test_uc43_ac11_inclusive_vietnamese_day_boundaries_and_open_ends(database):
    single = await read(database, tu_ngay="2026-11-14", den_ngay="2026-11-14")
    assert {entry.id for entry in single.data} == {database.audit_ids[i - 1] for i in (2, 3, 4, 5, 7, 8)}
    since = await read(database, tu_ngay="2026-11-14")
    assert {entry.id for entry in since.data} == {database.audit_ids[i - 1] for i in (2, 3, 4, 5, 6, 7, 8)}
    until = await read(database, den_ngay="2026-11-14")
    assert {entry.id for entry in until.data} == {database.audit_ids[i - 1] for i in (1, 2, 3, 4, 5, 7, 8)}


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
    assert [entry.id for entry in result.data] == [database.audit_ids[i - 1] for i in ids]


@pytest.mark.parametrize("order", ["asc", "desc"])
async def test_uc43_ac12_stable_pagination_tied_timestamps(database, order):
    result_ids = []
    for page in range(1, 5):
        result = await read(database, page=page, page_size=2, sort_order=order)
        assert result.pagination.total_items == 8
        result_ids.extend(entry.id for entry in result.data)
    expected = [database.audit_ids[i - 1] for i in (1, 2, 3, 4, 7, 8, 5, 6)]
    assert result_ids == (expected if order == "asc" else list(reversed(expected)))
    beyond = await read(database, page=10**30, page_size=100)
    assert beyond.data == [] and beyond.pagination.total_items == 8


async def test_uc43_ac10_legacy_exclusion_and_conflicting_filters(database):
    legacy = await read(database, bo_thao_tac="thu_hoi_quyen")
    assert legacy.pagination.total_items == 8
    conflict = await read(database, thao_tac="tao", bo_thao_tac="tao")
    assert conflict.data == [] and conflict.pagination.total_items == 0
    excluded = await read(database, bo_thao_tac="tao_phien_ban")
    assert {entry.id for entry in excluded.data} == {database.audit_ids[i - 1] for i in (3, 4, 7, 8)}


async def test_uc43_ac01_ac04_ac14_ac15_snapshot_does_not_follow_current_stock(database):
    detail = await database.service.get_entry(database.audit_ids[6], {"roles": ["quan_tri_vien"]})
    await database.session.execute(text('UPDATE "MatHang" SET so_luong_ton=100 WHERE id=:id'), {"id": database.item_id})
    await database.session.commit()
    reread = await database.service.get_entry(database.audit_ids[6], {"roles": ["quan_ly"]})
    assert reread == detail
    assert reread.data.du_lieu_sau["danh_sach_thieu"][0]["so_luong_thieu"] == 10
    assert reread.data.du_lieu_sau["nested"] == [{"quantity": 10}]
    raw = await database.session.scalar(text('SELECT du_lieu_sau FROM "LichSuThaoTac" WHERE id=:id'), {"id": database.audit_ids[6]})
    assert raw["nested"][0]["passwordHash"] == "never-return-this"


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE \"LichSuThaoTac\" SET ly_do='tamper' WHERE id=:id",
        'DELETE FROM "LichSuThaoTac" WHERE id=:id',
    ],
)
async def test_uc43_ac02_ac16_database_trigger_blocks_mutation(database, sql):
    async with database.session.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match="LichSuThaoTac"):
            await database.session.execute(text(sql), {"id": database.audit_ids[0]})
        await savepoint.rollback()
    assert await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac" WHERE doi_tuong_id=:id'), {"id": database.item_id}) == 8
    assert (
        await database.session.scalar(text('SELECT ly_do FROM "LichSuThaoTac" WHERE id=:id'), {"id": database.audit_ids[0]})
        == "before day"
    )


async def test_uc43_ac17_append_rolls_back_with_callers_operation(database):
    before = await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac" WHERE doi_tuong_id=:id'), {"id": database.item_id})
    with pytest.raises(RuntimeError, match="simulate failure"):
        async with SqlAlchemyTransaction(database.session):
            await database.session.execute(text('UPDATE "MatHang" SET so_luong_ton=123 WHERE id=:id'), {"id": database.item_id})
            await database.service.append(
                CreationAudit(
                    nhan_vien_id=database.admin["id"],
                    loai_doi_tuong="mat_hang",
                    doi_tuong_id=database.item_id,
                    du_lieu_sau={"so_luong_ton": 123},
                )
            )
            await database.session.flush()
            raise RuntimeError("simulate failure")
    assert await database.session.scalar(text('SELECT count(*) FROM "LichSuThaoTac" WHERE doi_tuong_id=:id'), {"id": database.item_id}) == before
    assert await database.session.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=:id'), {"id": database.item_id}) == 5


# UC-43 AC-17: Real commits are required to observe caller commit from another connection.
async def test_uc43_ac17_append_commits_only_when_caller_commits(committed_database):
    database = committed_database
    count = text('SELECT count(*) FROM "LichSuThaoTac" WHERE doi_tuong_id=:id')
    params = {"id": database.item_id}
    async with SqlAlchemyTransaction(database.session):
        await database.service.append(
            CreationAudit(
                nhan_vien_id=database.admin["id"],
                loai_doi_tuong="mat_hang",
                doi_tuong_id=database.item_id,
                du_lieu_sau=None,
                trang_thai_truoc=None,
                trang_thai_sau=None,
            )
        )
        await database.session.flush()
        assert await database.session.scalar(count, params) == 9
        async with database.factory() as independent:
            assert await independent.scalar(count, params) == 8
    async with database.factory() as independent:
        assert await independent.scalar(count, params) == 9


# UC-43 AC-7/9/17: HTTP uses independent real sessions, so setup/lock are committed.
async def test_uc43_ac07_ac09_ac17_http_reads_with_real_auth_repository_are_read_only(committed_database):
    database = committed_database

    async def test_session():
        async with database.factory() as session:
            yield session

    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = test_session
    snapshot = text('SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM "LichSuThaoTac" t WHERE doi_tuong_id=:id')
    params = {"id": database.item_id}
    before = await database.session.scalar(snapshot, params)
    database.statements.clear()
    listing = f"/api/v1/audit?doi_tuong_id={database.item_id}"
    detail = f"/api/v1/audit/{database.audit_ids[6]}"
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        for employee_id in (database.admin["id"], database.manager["id"]):
            for path in (listing, detail):
                response = await client.get(path, headers=auth_headers(employee_id))
                assert response.status_code == 200, response.text
                assert "never-return-this" not in response.text
                if path == listing:
                    assert response.json()["pagination"]["total_items"] == 8
                    assert {row["id"] for row in response.json()["data"]} == set(database.audit_ids)
                else:
                    assert response.json()["data"]["id"] == database.audit_ids[6]
        assert (await client.get(listing, headers=auth_headers(database.employee["id"]))).status_code == 403
        await database.session.execute(
            text("UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=:id"),
            {"id": database.manager["id"]},
        )
        await database.session.commit()
        assert (await client.get(listing, headers=auth_headers(database.manager["id"]))).status_code == 403
    after = await database.session.scalar(snapshot, params)
    assert before == after
    assert await database.session.scalar(text('SELECT so_luong_ton FROM "MatHang" WHERE id=:id'), params) == 5
    writes = [sql for sql in database.statements if not sql.lstrip().upper().startswith("SELECT")]
    assert len(writes) == 1 and writes[0].startswith('UPDATE "NhanVien"')


async def test_uc43_schema_matches_bootstrap_audit_table(database):
    # Read the worktree bootstrap as a specification only; never execute DDL.
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    definition = re.search(r'CREATE TABLE "LichSuThaoTac" \((.*?)\n\);', bootstrap, re.S)
    assert definition is not None, "init.sql is missing LichSuThaoTac"
    bootstrap_columns = {
        name: declaration.rstrip(",")
        for name, declaration in re.findall(r'^\s*"(\w+)" (.+)$', definition[1], re.M)
    }
    bootstrap_checks = dict(re.findall(
        r'CONSTRAINT "(\w+)" CHECK \((.+)\)', definition[1],
    ))
    bootstrap_indexes = {
        (name, tuple(column.strip() for column in columns.split(",")))
        for name, columns in re.findall(
            r'CREATE INDEX (\w+) ON "LichSuThaoTac" \(([^)]+)\)', bootstrap,
        )
    }
    def compare(sync):
        inspector = inspect(sync)
        columns = {column["name"]: column for column in inspector.get_columns("LichSuThaoTac")}
        table = LichSuThaoTac.__table__
        assert set(columns) == set(table.columns.keys())
        assert set(columns) == set(bootstrap_columns), "DB columns differ from worktree init.sql"
        sql_types = {"INT": "INTEGER", "TIMESTAMPTZ": "TIMESTAMP WITH TIME ZONE"}
        for column in table.columns:
            reflected = columns[column.name]
            declaration = bootstrap_columns[column.name].upper()
            sql_type = declaration.split()[0]
            assert reflected["type"].compile(dialect=sync.dialect) == sql_types.get(sql_type, sql_type), column.name
            assert reflected["nullable"] == ("NOT NULL" not in declaration and "PRIMARY KEY" not in declaration), column.name
            assert bool(reflected.get("identity")) == ("AS IDENTITY" in declaration), column.name
            if reflected.get("identity"):
                assert reflected["identity"]["always"] == ("GENERATED ALWAYS" in declaration)
            else:
                expected_default = re.search(r"\bDEFAULT (.+)", declaration)
                actual_default = reflected.get("default")
                assert bool(actual_default) == bool(expected_default), column.name
                if expected_default:
                    assert actual_default.lower().replace("(", "").replace(")", "") == expected_default[1].lower().replace("(", "").replace(")", ""), column.name
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
        assert set(checks) == set(bootstrap_checks), "DB checks differ from worktree init.sql"
        for name, expression in bootstrap_checks.items():
            assert set(re.findall(r"'([^']*)'", checks[name])) == set(re.findall(r"'([^']*)'", expression)), name
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
        assert {
            (index["name"], tuple(index["column_names"]))
            for index in inspector.get_indexes("LichSuThaoTac")
        } == bootstrap_indexes, "DB indexes differ from worktree init.sql"
        foreign = inspector.get_foreign_keys("LichSuThaoTac")
        assert re.search(
            r'ALTER TABLE "LichSuThaoTac" ADD FOREIGN KEY \("nhan_vien_id"\) REFERENCES "NhanVien" \("id"\) DEFERRABLE INITIALLY IMMEDIATE;',
            bootstrap,
        ), "init.sql audit FK differs from the contract asserted below"
        assert len(foreign) == 1
        assert foreign[0]["constrained_columns"] == ["nhan_vien_id"]
        assert foreign[0]["referred_table"] == "NhanVien" and foreign[0][
            "referred_columns"
        ] == ["id"]
        assert foreign[0]["options"]["deferrable"] is True
        assert foreign[0]["options"].get("initially", "IMMEDIATE") == "IMMEDIATE"

    await database.connection.run_sync(compare)


@pytest.mark.parametrize(
    "action", ["tao_phien_ban", "kiem_tra", "doi_mat_khau", "gui_lai", "dung_lai_phien_ban"]
)
async def test_uc43_ac05_v4_actions_are_readable(database, action):
    async with SqlAlchemyTransaction(database.session):
        await database.service.append(
            CreationAudit(
                nhan_vien_id=database.admin["id"],
                loai_doi_tuong="cong_thuc",
                doi_tuong_id=database.item_id,
                thao_tac=action,
                du_lieu_sau=None,
            )
        )
    response = await read(database, thao_tac=action)
    assert response.pagination.total_items >= 1
    assert all(row.thao_tac == action for row in response.data)
