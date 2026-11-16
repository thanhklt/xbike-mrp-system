"""UC-41 on the existing local PostgreSQL schema via TEST_DATABASE_URL.

Missing URL skips; require postgresql+asyncpg and localhost/127.0.0.1.
Each case creates unique data, shares raw/ORM connection and rolls back all rows.
No bootstrap, seed reload or database creation/deletion is performed.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import asyncpg
import pytest

from app.modules.reporting.repository import SqlAlchemyBaoCaoRepository
from app.modules.reporting.schemas import NhapXuatTonQuery
from app.modules.reporting.service import LOCAL_TZ, BaoCaoService, bien_ky

JANUARY = {"ky": "thang", "nam": 2026, "thang": 1}


@pytest.fixture
async def database(postgres_database):
    db = postgres_database
    db.employee = await db.add_employee(prefix="reporting")
    db.supplier_id = await db.raw.fetchval('''
        INSERT INTO "NhaCungCap" (ten_ncc, so_dien_thoai, dia_chi, phuong, tinh)
        VALUES ($1, '0901234567', 'Street', 'Ward', 'City') RETURNING id
    ''', f"Supplier_{uuid4().hex}")
    items = []
    for name, kind, active in (("Frame", "linh_kien", True), ("Bike", "thanh_pham", True),
                               ("Old bike", "thanh_pham", False)):
        items.append(await db.raw.fetchrow('''
            INSERT INTO "MatHang" (ten_mat_hang, sku, loai_mat_hang, don_vi_tinh, don_gia, is_active)
            VALUES ($1, $2, $3, 'piece', 100, $4) RETURNING id, ma_mat_hang, ten_mat_hang
        ''', name, f"REPORT_{uuid4().hex}", kind, active))
    db.frame, db.bike, db.old_bike = items
    db.item_ids = [item["id"] for item in items]
    # A positive ID proven absent in this transaction, without assuming a fixed ID.
    db.missing_item_id = await db.raw.fetchval('SELECT max(id) + 1 FROM "MatHang"')
    db.service = BaoCaoService(SqlAlchemyBaoCaoRepository(db.session))
    db.statements.clear()
    yield db


async def document_id(raw, table):
    # Document codes require a six-digit suffix: reserve an identity value rather
    # than MAX(id)+1, then retrieve the inserted ID with RETURNING below.
    return await raw.fetchval("SELECT nextval(pg_get_serial_sequence($1, 'id'))", f'"{table}"')


async def production_request(database, at, quantity):
    raw = database.raw
    id_ = await document_id(raw, "YeuCauSanXuat")
    return await raw.fetchval('''
        INSERT INTO "YeuCauSanXuat"
        (id, ma_yeu_cau_san_xuat, mat_hang_id, so_luong, han_hoan_thanh,
         nhan_vien_id, nhan_vien_duoc_giao_id, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $6, $7) RETURNING id
    ''', id_, f"YCSX-{at:%Y%m}-{id_:06d}", database.bike["id"], quantity,
        at.date(), database.employee["id"], at)


async def receipt(database, at, quantity, state="hoan_thanh"):
    raw = database.raw
    id_ = await document_id(raw, "PhieuNhap")
    id_ = await raw.fetchval('''
        INSERT INTO "PhieuNhap" (id, ma_phieu_nhap, nhan_vien_id, ncc_id, ngay_nhap, created_at)
        VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
    ''', id_, f"PN-{at:%Y%m}-{id_:06d}", database.employee["id"], database.supplier_id, at.date(), at)
    line = await raw.fetchval('''
        INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
        VALUES ($1, $2, $3::int, 1, $3::int::bigint) RETURNING id
    ''', id_, database.frame["id"], quantity)
    if state == "hoan_thanh":
        await raw.execute('''UPDATE "PhieuNhap" SET trang_thai='hoan_thanh',
            hoan_thanh_at=$2, nguoi_hoan_thanh_id=$3 WHERE id=$1''', id_, at, database.employee["id"])
    return (database.frame["id"], "nhap_linh_kien", quantity, line, None, None)


async def issue(database, at, quantity, item_id=None, state="da_duyet"):
    raw = database.raw
    item_id = database.frame["id"] if item_id is None else item_id
    request_id = await production_request(database, at, quantity)
    id_ = await document_id(raw, "PhieuXuat")
    kind = "xuat_linh_kien" if item_id == database.frame["id"] else "xuat_thanh_pham"
    id_ = await raw.fetchval('''
        INSERT INTO "PhieuXuat" (id, ma_phieu_xuat, nhan_vien_id, loai_phieu, yeu_cau_san_xuat_id, created_at)
        VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
    ''', id_, f"PX-{at:%Y%m}-{id_:06d}", database.employee["id"], kind, request_id, at)
    line = await raw.fetchval('''
        INSERT INTO "ChiTietPhieuXuat" (phieu_xuat_id, mat_hang_id, so_luong, don_gia_thuc, tong_gia)
        VALUES ($1, $2, $3::int, 1, $3::int::bigint) RETURNING id
    ''', id_, item_id, quantity)
    await raw.execute('''UPDATE "PhieuXuat" SET trang_thai=$2::varchar, gui_at=$3,
        nguoi_xu_ly_id=CASE WHEN $2::varchar IN ('da_duyet', 'tu_choi') THEN $5::int END,
        xu_ly_at=CASE WHEN $2::varchar IN ('da_duyet', 'tu_choi') THEN $3::timestamptz END,
        ly_do_tu_choi=CASE WHEN $2::varchar='tu_choi' THEN 'Test rejected' END,
        tong_tien=$4 WHERE id=$1''', id_, state, at, quantity, database.employee["id"])
    return (item_id, kind, -quantity, None, line, None)


async def completion(database, at, quantity, state="da_duyet"):
    raw = database.raw
    request_id = await production_request(database, at, quantity)
    id_ = await document_id(raw, "ChungTuHoanThanhSx")
    id_ = await raw.fetchval('''
        INSERT INTO "ChungTuHoanThanhSx"
        (id, ma_phieu, yeu_cau_san_xuat_id, so_luong_hoan_thanh, nhan_vien_id,
         trang_thai, finish_time, created_at, nguoi_xu_ly_id, xu_ly_at, ly_do_tu_choi)
        VALUES ($1, $2, $3, $4, $7, $5::varchar, $6, $6, $7, $6,
                CASE WHEN $5::varchar='tu_choi' THEN 'Test rejected' END) RETURNING id
    ''', id_, f"HTSX-{at:%Y%m}-{id_:06d}", request_id, quantity, state, at, database.employee["id"])
    return (database.bike["id"], "nhap_san_pham_san_xuat", quantity, None, None, id_)


async def post(database, source, at):
    raw = database.raw
    item_id, kind, delta, receipt_id, issue_id, completion_id = source
    async with raw.transaction():
        balance = await raw.fetchval('SELECT so_luong_ton FROM "MatHang" WHERE id=$1', item_id) + delta
        await raw.execute('''
            INSERT INTO "GiaoDichKho" (mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                so_luong_ton_sau, chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id,
                chung_tu_hoan_thanh_sx_id, nhan_vien_id, posted_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        ''', item_id, kind, delta, balance, receipt_id, issue_id, completion_id, database.employee["id"], at)
        await raw.execute('UPDATE "MatHang" SET so_luong_ton=$2 WHERE id=$1', item_id, balance)


async def read(database, query=None):
    query = query or JANUARY
    result = await database.service.nhap_xuat_ton(NhapXuatTonQuery(**query))
    if "mat_hang_id" in query:
        return result.data.mat_hang
    if "loai_mat_hang" in query:
        assert all(row.loai_mat_hang == query["loai_mat_hang"] for row in result.data.mat_hang)
    # The unfiltered report includes seed items: assert exact values/presence of
    # our items without making assumptions about the rest of the database.
    return [row for row in result.data.mat_hang if row.mat_hang_id in database.item_ids]


# UC-41 AC-1: Tồn cuối kỳ khớp tồn thực tế
async def test_postgres_current_period_matches_actual_stock(database):
    now = datetime.now(LOCAL_TZ)
    tu, _ = bien_ky("thang", now.year, now.month)
    raw = database.raw
    for creator, item_id in ((receipt, database.frame["id"]), (completion, database.bike["id"])):
        await post(database, await creator(database, tu - timedelta(seconds=1), 20), tu - timedelta(seconds=1))
        await post(database, await creator(database, tu, 8), tu)
        await post(database, await issue(database, tu, 3, item_id), tu)
        await post(database, await creator(database, tu, 2), tu)
        await post(database, await issue(database, tu, 1, item_id), tu)
    rows = await read(database, {"ky": "thang", "nam": now.year, "thang": now.month})
    actual = {r["id"]: r["so_luong_ton"] for r in await raw.fetch('SELECT id, so_luong_ton FROM "MatHang" WHERE id=ANY($1::int[])', database.item_ids)}
    assert [r.mat_hang_id for r in rows] == database.item_ids
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
    await post(database, await receipt(database, at, 50), at)
    await post(database, await completion(database, at, 20), at)
    before = await read(database)
    sources = [
        (await receipt(database, at, 100, "nhap"), "Phiếu nhập chưa hoàn tất"),
        (await issue(database, at, 3, state="cho_duyet"), "Phiếu xuất chưa duyệt"),
        (await issue(database, at, 4, state="tu_choi"), "Phiếu xuất chưa duyệt"),
        (await completion(database, at, 80, "tu_choi"), "Chứng từ hoàn thành chưa duyệt"),
    ]
    assert await read(database) == before
    for source, error in sources:
        with pytest.raises(asyncpg.RaiseError, match=error):
            await post(database, source, at)
    assert await raw.fetchval('SELECT COUNT(*) FROM "GiaoDichKho" WHERE nhan_vien_id=$1', database.employee["id"]) == 2
    assert await read(database) == before
    assert [(r.nhap_trong_ky, r.xuat_trong_ky) for r in before] == [(50, 0), (20, 0), (0, 0)]


# UC-41 AC-3: Kỳ tính theo giờ Việt Nam
async def test_postgres_january_2330_and_half_open_boundary(database):
    late = datetime(2026, 1, 31, 23, 30, tzinfo=LOCAL_TZ)
    boundary = datetime(2026, 2, 1, tzinfo=LOCAL_TZ)
    await post(database, await receipt(database, late, 9), late)
    await post(database, await receipt(database, boundary, 4), boundary)
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
    await post(database, await receipt(database, at, 15), at)
    await post(database, await completion(database, at, 7), at)
    previous, following = await read(database, first), await read(database, second)
    assert [r.ton_cuoi_ky for r in previous] == [15, 7, 0]
    assert [r.ton_dau_ky for r in following] == [15, 7, 0]
    assert [(r.nhap_trong_ky, r.xuat_trong_ky) for r in following] == [(0, 0)] * 3


# UC-41 A2: Mặt hàng không biến động và chưa giao dịch vẫn có dòng, lọc AND
async def test_postgres_unchanged_items_filters_and_tied_timestamps(database):
    at = datetime(2025, 12, 1, tzinfo=LOCAL_TZ)
    await post(database, await receipt(database, at, 10), at)
    await post(database, await receipt(database, at, 5), at)
    rows = await read(database)
    assert [r.mat_hang_id for r in rows] == database.item_ids
    assert [(r.ton_dau_ky, r.nhap_trong_ky, r.xuat_trong_ky, r.ton_cuoi_ky)
            for r in rows] == [(15, 0, 0, 15), (0, 0, 0, 0), (0, 0, 0, 0)]
    assert await read(database, {**JANUARY, "mat_hang_id": database.missing_item_id}) == []
    assert await read(database, {**JANUARY, "mat_hang_id": database.frame["id"], "loai_mat_hang": "thanh_pham"}) == []
    assert [r.mat_hang_id for r in await read(database, {**JANUARY, "loai_mat_hang": "thanh_pham"})] == database.item_ids[1:]
    assert [r.mat_hang_id for r in await read(database, {**JANUARY, "mat_hang_id": database.frame["id"]})] == [database.frame["id"]]
