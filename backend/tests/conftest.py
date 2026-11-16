"""Local PostgreSQL fixtures using the existing schema and TEST_DATABASE_URL.

Most tests share one connection with an outer rollback transaction. Only tests
requesting committed_postgres_database persist their setup and caller commits.
Neither fixture bootstraps, clears or deletes application data.
"""

import os
from functools import partial
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


async def _add_employee(raw, role="quan_ly", prefix="postgres"):
    role_id = await raw.fetchval('SELECT id FROM "VaiTro" WHERE ma_vai_tro=$1', role)
    assert role_id is not None, f"Existing database is missing seed role {role}"
    return await raw.fetchrow('''
        INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
        VALUES ($1, $2, 'test-credential-hash') RETURNING id, ma_nhan_vien
    ''', role_id, f"{prefix}_{uuid4().hex}")


@pytest.fixture
async def postgres_engine():
    configured = os.environ.get("TEST_DATABASE_URL")
    if not configured:
        pytest.skip("Local PostgreSQL not verified: TEST_DATABASE_URL is required")
    url = make_url(configured)
    if url.drivername != "postgresql+asyncpg" or url.host not in ("localhost", "127.0.0.1"):
        pytest.fail("TEST_DATABASE_URL must use postgresql+asyncpg on localhost/127.0.0.1")
    engine = create_async_engine(url, echo=False)
    statements = []

    def record_statement(_conn, _cursor, statement, _params, _context, _many):
        # Preserve SQL read/write assertions without counting fixture savepoints.
        if not statement.lstrip().upper().startswith(("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT")):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        yield SimpleNamespace(engine=engine, statements=statements)
    finally:
        await engine.dispose()


@pytest.fixture
async def postgres_database(postgres_engine):
    async with postgres_engine.engine.connect() as connection:
        transaction = await connection.begin()
        try:
            # begin() is lazy: start asyncpg's transaction before raw.transaction()
            # so raw nested transactions and ORM commits only release savepoints.
            await connection.exec_driver_sql("SELECT 1")
            raw = (await connection.get_raw_connection()).driver_connection
            factory = async_sessionmaker(
                bind=connection, join_transaction_mode="create_savepoint",
                expire_on_commit=False, autoflush=False,
            )
            async with factory() as session:
                yield SimpleNamespace(
                    engine=postgres_engine.engine, connection=connection, raw=raw,
                    session=session, factory=factory, statements=postgres_engine.statements,
                    add_employee=partial(_add_employee, raw),
                )
        finally:
            await transaction.rollback()


@pytest.fixture
async def committed_postgres_database(postgres_engine):
    """Real commits for independent-session visibility and HTTP auth/read tests.

    Callers commit their raw setup explicitly. Rows intentionally remain in the
    existing DB, including immutable audit entries; there is no delete cleanup.
    """
    async with postgres_engine.engine.connect() as connection:
        await connection.exec_driver_sql("SELECT 1")
        raw = (await connection.get_raw_connection()).driver_connection
        factory = async_sessionmaker(
            postgres_engine.engine, expire_on_commit=False, autoflush=False,
        )
        async with factory() as session:
            yield SimpleNamespace(
                engine=postgres_engine.engine, connection=connection, raw=raw,
                session=session, factory=factory, statements=postgres_engine.statements,
                add_employee=partial(_add_employee, raw),
            )
