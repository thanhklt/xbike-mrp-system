"""Execute the real Alembic revision on old and freshly bootstrapped PostgreSQL schemas."""

from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.inventory.repository import SqlAlchemyInventoryRepository
from app.modules.phieu_nhap.repository import SqlAlchemyPhieuNhapRepository
from app.modules.phieu_nhap.schemas import PhieuNhapCreate
from app.modules.phieu_nhap.service import PhieuNhapService
from tests.test_auth_migrations import migrate
from tests.test_auth_migrations import migration_connection as migration_connection

OLD_SCHEMA = """
CREATE TABLE nhan_vien (id integer PRIMARY KEY, trang_thai varchar);
INSERT INTO nhan_vien VALUES (2,'hoat_dong');
CREATE TABLE mat_hang (id integer PRIMARY KEY);
INSERT INTO mat_hang VALUES (1),(2);
CREATE TABLE ton_kho (id integer PRIMARY KEY,mat_hang_id integer UNIQUE,so_luong integer,updated_at timestamp);
INSERT INTO ton_kho VALUES (7,1,3,'2026-10-31 17:30:00');
CREATE TABLE phieu_nhap (id integer PRIMARY KEY, ma_phieu_nhap varchar,
    nhan_vien_id integer,ncc_id integer,tong_tien integer,created_at timestamp,ngay_nhap date);
INSERT INTO phieu_nhap VALUES (10,'PN-202610-000010',2,1,300,'2026-10-31 17:30:00','2026-10-30');
CREATE TABLE chi_tiet_phieu_nhap (id integer PRIMARY KEY,phieu_nhap_id integer,
    mat_hang_id integer,so_luong integer,don_gia_thuc integer,tong_gia integer);
INSERT INTO chi_tiet_phieu_nhap VALUES (20,10,1,3,100,300);
CREATE TABLE giao_dich_kho (id integer PRIMARY KEY,mat_hang_id integer,so_luong_bien_dong integer);
INSERT INTO giao_dich_kho VALUES (1,1,3);
CREATE TABLE lich_su_thao_tac (doi_tuong_id integer,loai_doi_tuong varchar,du_lieu_truoc jsonb,du_lieu_sau jsonb);
INSERT INTO lich_su_thao_tac VALUES (91,'phieu_nhap',
    '{"ma_phieu_nhap":"PN-202611-000010","chi_tiet":[{"id":101}]}',NULL);
"""


async def execute_script(connection, script):
    raw = await connection.get_raw_connection()
    await raw.driver_connection.execute(script)


async def upgrade(connection):
    await connection.run_sync(lambda sync: migrate(sync, revision="head"))


async def test_transfer_balances_dates_money_identity_and_preserve_archive(migration_connection):
    db = migration_connection
    await execute_script(db, OLD_SCHEMA)
    await upgrade(db)
    assert (
        await db.execute(text("SELECT so_luong_ton FROM mat_hang ORDER BY id"))
    ).scalars().all() == [3, 0]
    assert await db.scalar(text("SELECT so_luong FROM ton_kho WHERE id=7")) == 3
    assert (
        await db.scalar(text("SELECT ngay_nhap::text FROM phieu_nhap WHERE id=10")) == "2026-10-30"
    )
    assert (
        await db.scalar(text("SELECT created_at FROM phieu_nhap"))
    ).utcoffset().total_seconds() == 0
    assert await db.scalar(text("SELECT nextval(pg_get_serial_sequence('phieu_nhap','id'))")) == 92
    assert (
        await db.scalar(text("SELECT nextval(pg_get_serial_sequence('chi_tiet_phieu_nhap','id'))"))
        == 102
    )
    columns = await db.run_sync(lambda sync: inspect(sync).get_columns("phieu_nhap"))
    money = next(c for c in columns if c["name"] == "tong_tien")["type"]
    assert (money.precision, money.scale) == (18, 2)
    assert await db.scalar(text("SELECT count(*) FROM giao_dich_kho")) == 1


@pytest.mark.parametrize(
    "change,reason",
    [
        ("UPDATE phieu_nhap SET nhan_vien_id=NULL", "missing creator"),
        ("UPDATE phieu_nhap SET ncc_id=NULL", "missing creator"),
        ("UPDATE phieu_nhap SET created_at=NULL", "missing creator"),
        ("UPDATE phieu_nhap SET ngay_nhap=NULL", "map missing ngay_nhap"),
        ("ALTER TABLE phieu_nhap DROP COLUMN ngay_nhap", "add and map ngay_nhap"),
        ("UPDATE ton_kho SET so_luong=2", "balances do not match"),
        ("UPDATE ton_kho SET so_luong=-1", "balances do not match"),
        ("UPDATE phieu_nhap SET tong_tien=-1", "invalid numeric"),
        ("UPDATE chi_tiet_phieu_nhap SET don_gia_thuc=-1", "invalid numeric"),
        ("UPDATE lich_su_thao_tac SET doi_tuong_id=2147483647", "ID range exhausted"),
    ],
)
async def test_bad_legacy_data_stops_and_rolls_back_schema(migration_connection, change, reason):
    db = migration_connection
    await execute_script(db, OLD_SCHEMA)
    await db.execute(text(change))
    with pytest.raises(RuntimeError, match=reason):
        async with db.begin_nested():
            await upgrade(db)
    names = await db.run_sync(
        lambda sync: [c["name"] for c in inspect(sync).get_columns("mat_hang")]
    )
    assert "so_luong_ton" not in names
    assert await db.scalar(text("SELECT count(*) FROM ton_kho")) == 1


async def test_bootstrap_is_compatible_and_downgrade_refuses_data_loss(migration_connection):
    db = migration_connection
    schema = await db.scalar(text("SELECT current_schema()"))
    root = Path(__file__).resolve().parents[2]
    script = (root / "infra/postgres/init.sql").read_text(encoding="utf-8")
    # Execute the actual bootstrap in the isolated test schema, within the fixture transaction.
    script = script.replace("BEGIN;", "").replace("COMMIT;", "")
    script = script.replace(
        "SET LOCAL search_path TO public;", f'SET LOCAL search_path TO "{schema}";'
    )
    await execute_script(db, script)
    seed = (root / "infra/postgres/seed.sql").read_text(encoding="utf-8")
    seed = "\n".join(line for line in seed.splitlines() if not line.startswith("\\"))
    seed = seed.replace("BEGIN;", "").replace("COMMIT;", "").replace("public", schema)
    await execute_script(db, seed)
    assert await db.scalar(text("SELECT count(*) FROM ton_kho")) == 0
    assert await db.scalar(text("SELECT sum(so_luong_ton) FROM mat_hang")) == await db.scalar(
        text("SELECT sum(so_luong_bien_dong) FROM giao_dich_kho")
    )
    assert await db.scalar(text("SELECT nextval(pg_get_serial_sequence('phieu_nhap','id'))")) == 2
    await upgrade(db)
    before = await db.scalar(text("SELECT so_luong_ton FROM mat_hang WHERE id=8"))
    async with AsyncSession(
        bind=db, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        service = PhieuNhapService(
            SqlAlchemyPhieuNhapRepository(session),
            AuditService(SqlAlchemyAuditRepository(session)),
            SqlAlchemyTransaction(session),
            SqlAlchemyInventoryRepository(session),
        )
        created, etag = await service.create_receipt(
            PhieuNhapCreate(
                ncc_id=1,
                ngay_nhap="2026-11-03",
                chi_tiet=[{"mat_hang_id": 8, "so_luong": 3, "don_gia_thuc": "0.10"}],
            ),
            {"sub": "2"},
            "bootstrap-test",
        )
        assert await db.scalar(text("SELECT so_luong_ton FROM mat_hang WHERE id=8")) == before
        result, _ = await service.complete_receipt(
            created.data.id, etag, {"sub": "2"}, "bootstrap-test"
        )
        assert result.data.model_dump(mode="json")["tong_tien"] == "0.30"
    assert await db.scalar(text("SELECT so_luong_ton FROM mat_hang WHERE id=8")) == before + 3
    assert await db.scalar(text("SELECT count(*) FROM ton_kho")) == 0
    with pytest.raises(RuntimeError, match="reviewed restore/reconciliation"):
        await db.run_sync(lambda sync: migrate(sync, "downgrade", "20261018_auth_status"))
    assert await db.scalar(text("SELECT to_regclass('ton_kho') IS NOT NULL"))


async def test_existing_item_balance_must_not_be_overwritten(migration_connection):
    db = migration_connection
    await execute_script(
        db,
        OLD_SCHEMA
        + "ALTER TABLE mat_hang ADD so_luong_ton integer DEFAULT 0; UPDATE mat_hang SET so_luong_ton=3 WHERE id=1;",
    )
    await db.execute(text("UPDATE ton_kho SET so_luong=1"))  # archive can be stale after cutover
    await upgrade(db)
    assert await db.scalar(text("SELECT so_luong_ton FROM mat_hang WHERE id=1")) == 3
    assert await db.scalar(text("SELECT so_luong FROM ton_kho WHERE id=7")) == 1
