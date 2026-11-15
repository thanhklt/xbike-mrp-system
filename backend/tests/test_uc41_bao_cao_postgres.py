"""UC-41 SQL thật trên database UUID riêng dựng từ init.sql, không dùng DB ứng dụng.

Chỉ chạy khi dev cấp REPORTING_TEST_DATABASE_URL trỏ server test local, cổng khác
5432, tài khoản uc41_test và database *_test. Mỗi case tự tạo/xóa DB riêng.
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.modules.reporting.repository import SqlAlchemyBaoCaoRepository
from app.modules.reporting.schemas import NhapXuatTonQuery
from app.modules.reporting.service import LOCAL_TZ, BaoCaoService, bien_ky

BOOTSTRAP = Path(__file__).resolve().parents[2] / "infra/postgres/init.sql"
JANUARY = {"ky": "thang", "nam": 2026, "thang": 1}


@pytest.fixture
async def database():
    configured = os.environ.get("REPORTING_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("UC-41 PostgreSQL chưa kiểm chứng: thiếu REPORTING_TEST_DATABASE_URL")
    url = make_url(configured)
    if not (
        url.drivername == "postgresql+asyncpg"
        and url.host in ("127.0.0.1", "localhost")
        and url.port is not None and url.port != 5432
        and url.username == "uc41_test"
        and url.database and url.database.endswith("_test")
        and not url.query
    ):
        pytest.fail("Từ chối DB: cần server test local, cổng riêng khác 5432, uc41_test, *_test")
    name = f"uc41_{uuid4().hex}_test"
    test_url = url.set(database=name)
    admin = await asyncpg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False))
    raw = engine = None
    created = False
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        raw = await asyncpg.connect(test_url.set(drivername="postgresql").render_as_string(hide_password=False))
        assert await raw.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'") == 0
        await raw.execute(BOOTSTRAP.read_text(encoding="utf-8"))
        await raw.execute('''
            INSERT INTO "VaiTro" (id, ma_vai_tro, ten_vai_tro) VALUES (1, 'quan_ly', 'Manager');
            INSERT INTO "NhanVien" (id, vai_tro_id, ten_dang_nhap, mat_khau, ma_nhan_vien)
                VALUES (1, 1, 'uc41', 'test-hash', 'NV-000001');
            INSERT INTO "NhaCungCap" (id, ma_ncc, ten_ncc, so_dien_thoai, dia_chi, phuong, tinh)
                VALUES (1, 'NCC-000001', 'Supplier', '0901234567', 'Street', 'Ward', 'City');
            INSERT INTO "MatHang" (id, ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, is_active)
                VALUES (1, 'Frame', 'FRAME', 'linh_kien', 'cái', 100, true),
                       (2, 'Bike', 'BIKE', 'thanh_pham', 'chiếc', 200, true),
                       (3, 'Old bike', 'OLD-BIKE', 'thanh_pham', 'chiếc', 200, false);
        ''')
        engine = create_async_engine(test_url, echo=False)
        statements = []
        event.listen(engine.sync_engine, "before_cursor_execute",
                     lambda _c, _cur, statement, _p, _ctx, _many: statements.append(statement))
        async with AsyncSession(engine, expire_on_commit=False, autoflush=False) as session:
            yield SimpleNamespace(
                raw=raw, service=BaoCaoService(SqlAlchemyBaoCaoRepository(session)),
                statements=statements,
            )
    finally:
        if raw is not None:
            await raw.close()
        if engine is not None:
            await engine.dispose()
        try:
            if created:
                assert re.fullmatch(r"uc41_[0-9a-f]{32}_test", name)
                await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        finally:
            await admin.close()


async def production_request(raw, at, quantity):
    id_ = await raw.fetchval('SELECT COALESCE(MAX(id), 0) + 1 FROM "YeuCauSanXuat"')
    await raw.execute('''
        INSERT INTO "YeuCauSanXuat"
        (id, ma_yeu_cau_san_xuat, mat_hang_id, so_luong, han_hoan_thanh,
         nhan_vien_id, nhan_vien_duoc_giao_id, created_at)
        VALUES ($1, $2, 2, $3, $4, 1, 1, $5)
    ''', id_, f"YCSX-{at:%Y%m}-{id_:06d}", quantity, at.date(), at)
    return id_


async def receipt(raw, at, quantity, state="hoan_thanh"):
    id_ = await raw.fetchval('SELECT COALESCE(MAX(id), 0) + 1 FROM "PhieuNhap"')
    await raw.execute('''
        INSERT INTO "PhieuNhap" (id, ma_phieu_nhap, nhan_vien_id, ncc_id, ngay_nhap, created_at)
        VALUES ($1, $2, 1, 1, $3, $4)
    ''', id_, f"PN-{at:%Y%m}-{id_:06d}", at.date(), at)
    line = await raw.fetchval('''
        INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
        VALUES ($1, 1, $2::int, 1, $2::int::bigint) RETURNING id
    ''', id_, quantity)
    if state == "hoan_thanh":
        await raw.execute('''UPDATE "PhieuNhap" SET trang_thai='hoan_thanh',
            hoan_thanh_at=$2, nguoi_hoan_thanh_id=1 WHERE id=$1''', id_, at)
    return (1, "nhap_linh_kien", quantity, line, None, None)


async def issue(raw, at, quantity, item_id=1, state="da_duyet"):
    request_id = await production_request(raw, at, quantity)
    id_ = await raw.fetchval('SELECT COALESCE(MAX(id), 0) + 1 FROM "PhieuXuat"')
    kind = "xuat_linh_kien" if item_id == 1 else "xuat_thanh_pham"
    await raw.execute('''
        INSERT INTO "PhieuXuat" (id, ma_phieu_xuat, nhan_vien_id, loai_phieu, yeu_cau_san_xuat_id, created_at)
        VALUES ($1, $2, 1, $3, $4, $5)
    ''', id_, f"PX-{at:%Y%m}-{id_:06d}", kind, request_id, at)
    line = await raw.fetchval('''
        INSERT INTO "ChiTietPhieuXuat" (phieu_xuat_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
        VALUES ($1, $2, $3::int, 1, $3::int::bigint) RETURNING id
    ''', id_, item_id, quantity)
    await raw.execute('''UPDATE "PhieuXuat" SET trang_thai=$2, gui_at=$3,
        nguoi_xu_ly_id=CASE WHEN $2 IN ('da_duyet', 'tu_choi') THEN 1 END,
        xu_ly_at=CASE WHEN $2 IN ('da_duyet', 'tu_choi') THEN $3::timestamptz END,
        ly_do_tu_choi=CASE WHEN $2='tu_choi' THEN 'Test rejected' END,
        tong_tien=$4 WHERE id=$1''', id_, state, at, quantity)
    return (item_id, kind, -quantity, None, line, None)


async def completion(raw, at, quantity, state="da_duyet"):
    request_id = await production_request(raw, at, quantity)
    id_ = await raw.fetchval('SELECT COALESCE(MAX(id), 0) + 1 FROM "ChungTuHoanThanhSx"')
    await raw.execute('''
        INSERT INTO "ChungTuHoanThanhSx"
        (id, ma_phieu, yeu_cau_san_xuat_id, so_luong_hoan_thanh, nhan_vien_id,
         trang_thai, finish_time, created_at, nguoi_xu_ly_id, xu_ly_at, ly_do_tu_choi)
        VALUES ($1, $2, $3, $4, 1, $5, $6, $6, 1, $6,
                CASE WHEN $5='tu_choi' THEN 'Test rejected' END)
    ''', id_, f"HTSX-{at:%Y%m}-{id_:06d}", request_id, quantity, state, at)
    return (2, "nhap_san_pham_san_xuat", quantity, None, None, id_)


async def post(raw, source, at):
    item_id, kind, delta, receipt_id, issue_id, completion_id = source
    async with raw.transaction():
        balance = await raw.fetchval('SELECT so_luong_ton FROM "MatHang" WHERE id=$1', item_id) + delta
        await raw.execute('''
            INSERT INTO "GiaoDichKho" (mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                so_luong_ton_sau, chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id,
                chung_tu_hoan_thanh_sx_id, nhan_vien_id, posted_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,1,$8)
        ''', item_id, kind, delta, balance, receipt_id, issue_id, completion_id, at)
        await raw.execute('UPDATE "MatHang" SET so_luong_ton=$2 WHERE id=$1', item_id, balance)


async def read(database, query=None):
    result = await database.service.nhap_xuat_ton(NhapXuatTonQuery(**(query or JANUARY)))
    return result.data.mat_hang


# UC-41 AC-1: Tồn cuối kỳ khớp tồn thực tế
async def test_postgres_current_period_matches_actual_stock(database):
    now = datetime.now(LOCAL_TZ)
    tu, _ = bien_ky("thang", now.year, now.month)
    raw = database.raw
    for creator, item_id in ((receipt, 1), (completion, 2)):
        await post(raw, await creator(raw, tu - timedelta(seconds=1), 20), tu - timedelta(seconds=1))
        await post(raw, await creator(raw, tu, 8), tu)
        await post(raw, await issue(raw, tu, 3, item_id), tu)
        await post(raw, await creator(raw, tu, 2), tu)
        await post(raw, await issue(raw, tu, 1, item_id), tu)
    rows = await read(database, {"ky": "thang", "nam": now.year, "thang": now.month})
    actual = {r["id"]: r["so_luong_ton"] for r in await raw.fetch('SELECT id, so_luong_ton FROM "MatHang"')}
    assert [r.mat_hang_id for r in rows] == [1, 2, 3]
    for r in rows:
        assert r.ton_cuoi_ky == actual[r.mat_hang_id]
        assert r.ton_cuoi_ky == r.ton_dau_ky + r.nhap_trong_ky - r.xuat_trong_ky
    assert [(r.ton_dau_ky, r.nhap_trong_ky, r.xuat_trong_ky, r.ton_cuoi_ky)
            for r in rows] == [(20, 10, 4, 26), (20, 10, 4, 26), (0, 0, 0, 0)]
    assert len(database.statements) == 1
    assert database.statements[0].lstrip().startswith("SELECT")


# UC-41 AC-2: Không tính chứng từ chưa ghi nhận
async def test_postgres_unposted_documents_excluded_and_trigger_rejects(database):
    raw = database.raw
    at = datetime(2026, 1, 10, tzinfo=LOCAL_TZ)
    await post(raw, await receipt(raw, at, 50), at)
    await post(raw, await completion(raw, at, 20), at)
    before = await read(database)
    sources = [
        (await receipt(raw, at, 100, "nhap"), "Phiếu nhập chưa hoàn tất"),
        (await issue(raw, at, 3, state="cho_duyet"), "Phiếu xuất chưa duyệt"),
        (await issue(raw, at, 4, state="tu_choi"), "Phiếu xuất chưa duyệt"),
        (await completion(raw, at, 80, "tu_choi"), "Chứng từ hoàn thành chưa duyệt"),
    ]
    assert await read(database) == before
    for source, error in sources:
        with pytest.raises(asyncpg.RaiseError, match=error):
            await post(raw, source, at)
    assert await raw.fetchval('SELECT COUNT(*) FROM "GiaoDichKho"') == 2
    assert await read(database) == before
    assert [(r.nhap_trong_ky, r.xuat_trong_ky) for r in before] == [(50, 0), (20, 0), (0, 0)]


# UC-41 AC-3: Kỳ tính theo giờ Việt Nam
async def test_postgres_january_2330_and_half_open_boundary(database):
    raw = database.raw
    late = datetime(2026, 1, 31, 23, 30, tzinfo=LOCAL_TZ)
    boundary = datetime(2026, 2, 1, tzinfo=LOCAL_TZ)
    await post(raw, await receipt(raw, late, 9), late)
    await post(raw, await receipt(raw, boundary, 4), boundary)
    jan = await read(database)
    feb = await read(database, {"ky": "thang", "nam": 2026, "thang": 2})
    assert (jan[0].nhap_trong_ky, jan[0].ton_cuoi_ky) == (9, 9)
    assert (feb[0].ton_dau_ky, feb[0].nhap_trong_ky, feb[0].ton_cuoi_ky) == (9, 4, 13)


# UC-41 AC-4: Tồn đầu kỳ nối tiếp
@pytest.mark.parametrize("first,second", [
    (JANUARY, {"ky": "thang", "nam": 2026, "thang": 2}),
    ({"ky": "quy", "nam": 2026, "quy": 1}, {"ky": "quy", "nam": 2026, "quy": 2}),
])
async def test_postgres_adjacent_periods(database, first, second):
    at = datetime(2026, 1, 10, tzinfo=LOCAL_TZ)
    await post(database.raw, await receipt(database.raw, at, 15), at)
    await post(database.raw, await completion(database.raw, at, 7), at)
    previous, following = await read(database, first), await read(database, second)
    assert [r.ton_cuoi_ky for r in previous] == [15, 7, 0]
    assert [r.ton_dau_ky for r in following] == [15, 7, 0]
    assert [(r.nhap_trong_ky, r.xuat_trong_ky) for r in following] == [(0, 0)] * 3


# UC-41 A2: Mặt hàng không biến động và chưa giao dịch vẫn có dòng, lọc AND
async def test_postgres_unchanged_items_filters_and_tied_timestamps(database):
    raw = database.raw
    at = datetime(2025, 12, 1, tzinfo=LOCAL_TZ)
    await post(raw, await receipt(raw, at, 10), at)
    await post(raw, await receipt(raw, at, 5), at)
    rows = await read(database)
    assert [r.mat_hang_id for r in rows] == [1, 2, 3]
    assert [(r.ton_dau_ky, r.nhap_trong_ky, r.xuat_trong_ky, r.ton_cuoi_ky)
            for r in rows] == [(15, 0, 0, 15), (0, 0, 0, 0), (0, 0, 0, 0)]
    assert await read(database, {**JANUARY, "mat_hang_id": 999}) == []
    assert await read(database, {**JANUARY, "mat_hang_id": 1, "loai_mat_hang": "thanh_pham"}) == []
    assert [r.mat_hang_id for r in await read(database, {**JANUARY, "loai_mat_hang": "thanh_pham"})] == [2, 3]
    assert [r.mat_hang_id for r in await read(database, {**JANUARY, "mat_hang_id": 1})] == [1]
