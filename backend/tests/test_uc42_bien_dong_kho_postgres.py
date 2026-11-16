"""UC-42 on the seeded local PostgreSQL database via TEST_DATABASE_URL.

Uses the shared outer rollback transaction and unique UC-41 test data.
Missing URL skips; no bootstrap, separate database or persistent writes.
"""

from datetime import datetime, timedelta

import asyncpg
import pytest
from test_uc41_bao_cao_postgres import completion, issue, receipt
from test_uc41_bao_cao_postgres import database as database

from app.modules.reporting.schemas import BienDongKhoQuery
from app.modules.reporting.service import LOCAL_TZ

AT = datetime(2026, 1, 31, 23, 30, tzinfo=LOCAL_TZ)


async def post(database, source, at=AT, actor=None):
    raw = database.raw
    actor = database.employee["id"] if actor is None else actor
    item, kind, delta, receipt_id, issue_id, completion_id = source
    async with raw.transaction():
        balance = await raw.fetchval('SELECT so_luong_ton FROM "MatHang" WHERE id=$1', item) + delta
        id_ = await raw.fetchval('''
            INSERT INTO "GiaoDichKho" (mat_hang_id, loai_giao_dich, so_luong_bien_dong,
                so_luong_ton_sau, chi_tiet_phieu_nhap_id, chi_tiet_phieu_xuat_id,
                chung_tu_hoan_thanh_sx_id, nhan_vien_id, posted_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id
        ''', item, kind, delta, balance, receipt_id, issue_id, completion_id, actor, at)
        await raw.execute('UPDATE "MatHang" SET so_luong_ton=$2 WHERE id=$1', item, balance)
    return id_


async def read(database, **query):
    query.setdefault("nhan_vien_id", database.employee["id"])
    return await database.service.bien_dong_kho(BienDongKhoQuery(**query))


# UC-42 AC-1: Lịch sử Khung xe kèm đầu phiếu gốc, dấu và số dư, thứ tự mới nhất
async def test_postgres_item_history_resolves_source_headers(database):
    raw = database.raw
    first = await post(database, await receipt(database, AT, 10))
    second = await post(database, await issue(database, AT, 3))
    await post(database, await completion(database, AT, 5))
    result = await read(database, mat_hang_id=database.frame["id"])
    assert [r.id for r in result.data] == [second, first]
    assert [(r.so_luong_bien_dong, r.so_luong_ton_sau) for r in result.data] == [(-3, 7), (10, 10)]
    for row, table, column in ((result.data[0], "PhieuXuat", "ma_phieu_xuat"),
                               (result.data[1], "PhieuNhap", "ma_phieu_nhap")):
        source = await raw.fetchrow(f'SELECT id, {column} AS ma FROM "{table}" WHERE id=$1', row.chung_tu.id)
        assert row.chung_tu.id == source["id"]
        assert row.chung_tu.ma == source["ma"]
        assert row.mat_hang.id == database.frame["id"]
        assert row.mat_hang.ma_mat_hang == database.frame["ma_mat_hang"]
        assert row.mat_hang.ten_mat_hang == "Frame"
        assert row.nhan_vien.id == database.employee["id"]
        assert row.nhan_vien.ma_nhan_vien == database.employee["ma_nhan_vien"]
        assert row.nhan_vien.ho_ten is None
        assert row.posted_at == AT
    assert [r.chung_tu.loai for r in result.data] == ["phieu_xuat", "phieu_nhap"]
    assert result.pagination.total_items == 2
    assert len(database.statements) == 2
    assert all(s.lstrip().startswith("SELECT") for s in database.statements)


# UC-42 AC-2: Phiếu xuất từ chối tồn tại nhưng trigger chặn ghi sổ, không xuất hiện
async def test_postgres_rejected_issue_is_not_in_history(database):
    raw = database.raw
    await post(database, await receipt(database, AT, 10))
    before = await read(database)
    rejected = await issue(database, AT, 3, state="tu_choi")
    assert await raw.fetchval('SELECT count(*) FROM "PhieuXuat" WHERE trang_thai=\'tu_choi\' AND nhan_vien_id=$1', database.employee["id"]) == 1
    with pytest.raises(asyncpg.RaiseError, match="Phiếu xuất chưa duyệt"):
        await post(database, rejected)
    after = await read(database)
    assert after == before
    assert after.pagination.total_items == 1
    assert [r.chung_tu.loai for r in after.data] == ["phieu_nhap"]
    assert await raw.fetchval('SELECT count(*) FROM "GiaoDichKho" WHERE nhan_vien_id=$1', database.employee["id"]) == 1
    assert await raw.fetchval('SELECT so_luong_ton FROM "MatHang" WHERE id=$1', database.frame["id"]) == 10


# UC-42 AC-3: Đủ bốn nghiệp vụ, lọc nhập kho chỉ trả phiếu nhập
async def test_postgres_four_types_resolve_all_source_kinds(database):
    raw = database.raw
    await post(database, await receipt(database, AT, 10))
    await post(database, await issue(database, AT, 3))
    await post(database, await completion(database, AT, 5))
    await post(database, await issue(database, AT, 2, item_id=database.bike["id"]))
    all_rows = await read(database)
    assert {r.loai_giao_dich: r.chung_tu.loai for r in all_rows.data} == {
        "nhap_linh_kien": "phieu_nhap", "xuat_linh_kien": "phieu_xuat",
        "nhap_san_pham_san_xuat": "chung_tu_hoan_thanh_sx", "xuat_thanh_pham": "phieu_xuat",
    }
    production = next(r for r in all_rows.data if r.chung_tu.loai == "chung_tu_hoan_thanh_sx")
    header = await raw.fetchrow('SELECT id, ma_phieu FROM "ChungTuHoanThanhSx" WHERE id=$1', production.chung_tu.id)
    assert production.chung_tu.id == header["id"]
    assert production.chung_tu.ma == header["ma_phieu"]
    filtered = await read(database, loai_giao_dich="nhap_linh_kien")
    assert filtered.pagination.total_items == 1
    assert [(r.loai_giao_dich, r.chung_tu.loai) for r in filtered.data] == [("nhap_linh_kien", "phieu_nhap")]


# UC-42 R1: Lọc AND theo người ghi sổ, độc lập người lập phiếu và COUNT cùng điều kiện
async def test_postgres_combined_filters_and_actor(database):
    raw = database.raw
    recorder = await database.add_employee(prefix="recorder")
    await post(database, await receipt(database, AT, 10), actor=database.employee["id"])
    expected = await post(database, await receipt(database, AT, 4), actor=recorder["id"])
    await post(database, await issue(database, AT, 2), actor=recorder["id"])
    await post(database, await completion(database, AT, 5), actor=recorder["id"])
    later = AT + timedelta(days=1)
    await post(database, await receipt(database, later, 6), at=later, actor=recorder["id"])
    result = await read(database, mat_hang_id=database.frame["id"], loai_giao_dich="nhap_linh_kien", nhan_vien_id=recorder["id"],
                        tu_ngay="2026-01-31", den_ngay="2026-01-31", page_size=1)
    assert [r.id for r in result.data] == [expected]
    assert result.pagination.total_items == 1
    assert result.data[0].nhan_vien.id == recorder["id"]
    assert await raw.fetchval('SELECT nhan_vien_id FROM "PhieuNhap" WHERE id=$1', result.data[0].chung_tu.id) == database.employee["id"]


# UC-42 R3: Biên ngày giờ Việt Nam bao gồm hai đầu ngày và loại ngày kế tiếp
async def test_postgres_vietnam_day_boundaries(database):
    start = datetime(2026, 1, 31, tzinfo=LOCAL_TZ)
    end = datetime(2026, 2, 1, tzinfo=LOCAL_TZ)
    ids = []
    for at in (start - timedelta(microseconds=1), start, AT, end, end + timedelta(minutes=10)):
        ids.append(await post(database, await receipt(database, at, 2), at=at))
    result = await read(database, tu_ngay="2026-01-31", den_ngay="2026-01-31")
    assert [r.id for r in result.data] == [ids[2], ids[1]]
    assert result.pagination.total_items == 2
    assert (await read(database, tu_ngay="2026-02-01")).pagination.total_items == 2
    assert (await read(database, den_ngay="2026-01-30")).pagination.total_items == 1


# UC-42 A1: Phân trang ổn định, trang ngoài và mặt hàng không tồn tại trả rỗng
async def test_postgres_pagination_ties_and_empty_results(database):
    ids = [await post(database, await receipt(database, AT, 2)) for _ in range(3)]
    first = await read(database, page_size=2)
    second = await read(database, page=2, page_size=2)
    assert [r.id for r in first.data] == list(reversed(ids[1:]))
    assert [r.id for r in second.data] == ids[:1]
    assert first.pagination.total_items == second.pagination.total_items == 3
    assert first.pagination.has_next is True
    assert second.pagination.has_prev is True
    beyond = await read(database, page=3, page_size=2)
    assert beyond.data == []
    assert beyond.pagination.total_items == 3
    empty = await read(database, mat_hang_id=database.missing_item_id)
    assert empty.data == []
    assert empty.pagination.total_items == 0
