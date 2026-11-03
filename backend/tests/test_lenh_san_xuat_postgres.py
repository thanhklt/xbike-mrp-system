"""Real PostgreSQL workflow in session-local v2 TEMP tables, rolled back."""

import os
import re

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.errors import ConflictException
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.lenh_san_xuat.repository import SqlAlchemyLenhSanXuatRepository
from app.modules.lenh_san_xuat.service import LenhSanXuatService
from tests.test_lenh_san_xuat_repository import FIXTURES, TABLES


@pytest.fixture
async def postgres_session():
    url = os.environ.get("LSX_V2_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Requires a dedicated PostgreSQL _test database for v2 checks")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Refusing to use a non-test database")
    engine = create_async_engine(url, hide_parameters=True)
    try:
        async with engine.connect() as connection, connection.begin():
            for name, columns in TABLES.items():
                columns = re.sub(
                    r"(created_at|started_at|completed_at) text", r"\1 timestamptz", columns
                )
                await connection.execute(text(f'CREATE TEMP TABLE "{name}" ({columns})'))
            for sql in FIXTURES:
                for name in TABLES:
                    sql = re.sub(rf"\b{name}\b", f'"{name}"', sql)
                await connection.execute(text(sql))
            for statement in [
                'CREATE TEMP TABLE "YeuCauSanXuat" (id int, trang_thai text)',
                'CREATE TEMP TABLE "NhanVien" (id int, trang_thai text)',
                'CREATE TEMP TABLE "Bom" (id int, mat_hang_id int, is_active bool)',
                'CREATE TEMP TABLE "ChiTietBom" (bom_id int, mat_hang_id int, so_luong int)',
                """CREATE TEMP TABLE "LichSuThaoTac" (id serial primary key, nhan_vien_id int,
                loai_doi_tuong text, doi_tuong_id int, thao_tac text, du_lieu_truoc jsonb,
                du_lieu_sau jsonb, ly_do text, created_at timestamptz default now())""",
                """INSERT INTO "YeuCauSanXuat" VALUES (1, 'da_gui')""",
                """INSERT INTO "NhanVien" VALUES (7, 'hoat_dong')""",
                """INSERT INTO "Bom" VALUES (3, 2, true)""",
                """INSERT INTO "ChiTietBom" VALUES (3, 4, 2)""",
                """UPDATE "LenhSanXuat" SET trang_thai='nhap' WHERE id=1""",
            ]:
                await connection.execute(text(statement))
            async with AsyncSession(
                bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
            ) as session:
                yield session
            # The outer transaction and all TEMP tables disappear on disconnect.
    finally:
        await engine.dispose()


async def test_postgres_workflow_and_atomic_audit(postgres_session):
    session = postgres_session
    service = LenhSanXuatService(
        SqlAlchemyLenhSanXuatRepository(session),
        SqlAlchemyAuditRepository(session),
        SqlAlchemyTransaction(session),
    )
    manager = {"sub": "9", "roles": ["quan_ly"]}
    worker = {"sub": "7", "roles": ["nhan_vien"]}
    assigned = await service.assign(1, 7, manager, "r")
    assert assigned.data.nhan_vien_id == 7
    sent = await service.send(1, manager, "r")
    assert sent.data.trang_thai == "da_gui"
    with pytest.raises(ConflictException):
        await service.start(1, worker, "r")
    assert (await service.get_order(1, "r")).data.trang_thai == "da_gui"
    assert await session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == 2
    await session.execute(
        text("""UPDATE "PhieuDieuChinhKho" SET trang_thai='tu_choi' WHERE id=1""")
    )
    started = await service.start(1, worker, "r")
    assert started.data.trang_thai == "dang_thuc_hien"
    assert started.data.started_at is not None
    assert await session.scalar(text('SELECT count(*) FROM "GiaoDichKho"')) == 7
    with pytest.raises(ConflictException):
        await service.cancel(1, "Thay đổi", manager, "r")
    assert await session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == 3


async def test_postgres_audit_failure_rolls_back_order(postgres_session):
    session = postgres_session
    # A failed audit insert aborts the same savepoint as the order update.
    await session.execute(text('ALTER TABLE "LichSuThaoTac" ADD CHECK (nhan_vien_id > 0)'))
    service = LenhSanXuatService(
        SqlAlchemyLenhSanXuatRepository(session),
        SqlAlchemyAuditRepository(session),
        SqlAlchemyTransaction(session),
    )
    with pytest.raises(ConflictException):
        await service.send(1, {"sub": "-1", "roles": ["quan_ly"]}, "r")
    assert (await service.get_order(1, "r")).data.trang_thai == "nhap"
    assert await session.scalar(text('SELECT count(*) FROM "LichSuThaoTac"')) == 0
