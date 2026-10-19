"""Run the real Alembic chain in temporary schemas rolled back after each test."""

import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
async def migration_connection():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL test database")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Migration tests require a database name ending in _test")
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        schema = "auth_migration_" + uuid4().hex
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


def migrate(connection, action="upgrade", revision="head"):
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.attributes["connection"] = connection
    getattr(command, action)(config, revision)


async def test_upgrade_old_empty_schema_and_downgrade(migration_connection):
    connection = migration_connection
    await connection.execute(text("CREATE TABLE nhan_vien (id INTEGER PRIMARY KEY)"))
    await connection.run_sync(migrate)
    columns = await connection.run_sync(lambda sync: inspect(sync).get_columns("nhan_vien"))
    status = next(column for column in columns if column["name"] == "trang_thai")
    assert not status["nullable"]
    assert "hoat_dong" in status["default"]
    await connection.execute(text("INSERT INTO nhan_vien (id) VALUES (1)"))
    assert await connection.scalar(text("SELECT trang_thai FROM nhan_vien")) == "hoat_dong"
    await connection.run_sync(lambda sync: migrate(sync, "downgrade", "20261018_status_default"))
    await connection.execute(text("UPDATE nhan_vien SET trang_thai=NULL"))
    assert await connection.scalar(text("SELECT count(*) FROM nhan_vien")) == 1


async def test_upgrade_preserves_existing_active_and_locked_accounts(migration_connection):
    connection = migration_connection
    await connection.execute(
        text("CREATE TABLE nhan_vien (id INTEGER PRIMARY KEY, trang_thai VARCHAR)")
    )
    await connection.execute(text("INSERT INTO nhan_vien VALUES (1, 'hoat_dong'), (2, 'bi_khoa')"))
    await connection.run_sync(lambda sync: migrate(sync, "stamp", "20261018_status_default"))
    await connection.run_sync(migrate)
    assert (
        await connection.execute(text("SELECT trang_thai FROM nhan_vien ORDER BY id"))
    ).scalars().all() == ["hoat_dong", "bi_khoa"]


@pytest.mark.parametrize("status", [None, "unknown"])
async def test_upgrade_refuses_to_guess_existing_account_status(migration_connection, status):
    connection = migration_connection
    await connection.execute(
        text("CREATE TABLE nhan_vien (id INTEGER PRIMARY KEY, trang_thai VARCHAR)")
    )
    await connection.execute(text("INSERT INTO nhan_vien VALUES (1, :status)"), {"status": status})
    with pytest.raises(RuntimeError, match="explicit hoat_dong/bi_khoa mapping"):
        await connection.run_sync(migrate)
    assert await connection.scalar(text("SELECT trang_thai FROM nhan_vien WHERE id=1")) == status
