"""Real UC-04 PostgreSQL tests, isolated from the application database.

Set NHAN_VIEN_CODE_TEST_DATABASE_URL to a dedicated local *_test database on
a test-only server owned by uc04_test. Each case creates/drops only its UUID DB.
"""

import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy.engine import make_url

BOOTSTRAP = Path(__file__).resolve().parents[2] / "infra/postgres/init.sql"


@pytest.fixture
async def database():
    configured = os.environ.get("NHAN_VIEN_CODE_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("UC-04 PostgreSQL not verified: NHAN_VIEN_CODE_TEST_DATABASE_URL is required")
    url = make_url(configured)
    if not (
        url.drivername == "postgresql+asyncpg"
        and url.host in ("127.0.0.1", "localhost")
        and url.username == "uc04_test"
        and url.database
        and url.database.endswith("_test")
    ):
        pytest.fail("Refusing database not identified as a local uc04_test test server")
    name = f"uc04_{uuid4().hex}_test"
    admin = await asyncpg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    connection = None
    created = False
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        connection = await asyncpg.connect(
            url.set(drivername="postgresql", database=name).render_as_string(hide_password=False)
        )
        assert await connection.fetchval(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        ) == 0
        await connection.execute(BOOTSTRAP.read_text(encoding="utf-8"))
        await connection.execute(
            """INSERT INTO "VaiTro" (id, ma_vai_tro, ten_vai_tro)
               VALUES (1, 'quan_tri_vien', 'Admin')"""
        )
        yield connection
    finally:
        try:
            if connection is not None:
                await connection.close()
        finally:
            try:
                # Only the UUID database successfully created by this fixture may be dropped.
                assert name.startswith("uc04_") and name.endswith("_test") and len(name) == 42
                if created:
                    await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
            finally:
                await admin.close()


# UC-04 R6: hai INSERT không truyền mã nhận hai mã khác nhau đúng NV- + id sáu chữ số
async def test_insert_without_code_uses_identity(database):
    rows = await database.fetch(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'first', 'test-hash'), (1, 'second', 'test-hash')
           RETURNING id, ma_nhan_vien"""
    )
    assert len(rows) == 2
    assert len({row["ma_nhan_vien"] for row in rows}) == 2
    assert {row["id"] for row in rows} == {1, 2}
    for row in rows:
        assert row["ma_nhan_vien"] == f"NV-{row['id']:06d}"
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 2


# UC-04 R6: không sửa được mã hoặc id sau tạo; cập nhật hồ sơ vẫn được phép
@pytest.mark.parametrize("assignment", ["ma_nhan_vien='NV-000002'", "id=2"])
async def test_update_cannot_change_code_or_identity(database, assignment):
    await database.execute(
        """INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (1, 'employee', 'test-hash')"""
    )
    with pytest.raises(asyncpg.RaiseError, match="Không được sửa mã nhân viên") as caught:
        async with database.transaction():
            await database.execute(f'UPDATE "NhanVien" SET {assignment} WHERE id=1')
    assert caught.value.sqlstate == "P0001"
    row = await database.fetchrow('SELECT id, ma_nhan_vien FROM "NhanVien"')
    assert dict(row) == {"id": 1, "ma_nhan_vien": "NV-000001"}
    assert await database.fetchval(
        """UPDATE "NhanVien" SET ho_ten='Updated profile' WHERE id=1 RETURNING ho_ten"""
    ) == "Updated profile"


# UC-04 R6: id 999999 còn hợp lệ; id 1000000 báo hết dải và không lưu mã bị lpad cắt
async def test_insert_rejects_exhausted_code_range(database):
    assert await database.fetchval(
        """INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau)
           VALUES (999999, 1, 'last', 'test-hash') RETURNING ma_nhan_vien"""
    ) == "NV-999999"
    with pytest.raises(asyncpg.RaiseError, match="Hết dải mã nhân viên NV-NNNNNN") as caught:
        async with database.transaction():
            await database.execute(
                """INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau)
                   VALUES (1000000, 1, 'exhausted', 'test-hash')"""
            )
    assert caught.value.sqlstate == "P0001"
    assert await database.fetchval('SELECT count(*) FROM "NhanVien"') == 1
    assert await database.fetchval('SELECT ma_nhan_vien FROM "NhanVien"') == "NV-999999"
