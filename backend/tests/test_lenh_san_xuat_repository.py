"""Exercise aggregate SQL on a disposable in-memory v2 fixture.

These tests do not verify PostgreSQL locking or the existing bootstrap schema.
"""

import pytest
from sqlalchemy import create_engine, text

from app.modules.lenh_san_xuat.repository import SqlAlchemyLenhSanXuatRepository
from app.modules.lenh_san_xuat.schemas import LenhListQuery

TABLES = {
    "LenhSanXuat": "id int, ma_lenh_san_xuat text, yeu_cau_san_xuat_id int, lenh_san_xuat_cha_id int, mat_hang_id int, bom_id int, so_luong int, nhan_vien_id int, trang_thai text, created_at text, started_at text, completed_at text",
    "ChiTietLenhSanXuat": "id int, lenh_san_xuat_id int, mat_hang_id int, so_luong_can int",
    "MatHang": "id int, so_luong_ton int",
    "PhieuXuat": "id int, lenh_san_xuat_id int, loai_phieu text, trang_thai text",
    "ChiTietPhieuXuat": "id int, phieu_xuat_id int, mat_hang_id int",
    "ChungTuHoanThanhSx": "id int, lenh_san_xuat_id int, trang_thai text",
    "PhieuDieuChinhKho": "id int, trang_thai text",
    "ChiTietPhieuDieuChinhKho": "id int, phieu_dieu_chinh_kho_id int, giao_dich_goc_id int",
    "GiaoDichKho": "id int, mat_hang_id int, loai_giao_dich text, so_luong_bien_dong int, chi_tiet_phieu_nhap_id int, chi_tiet_phieu_xuat_id int, chung_tu_hoan_thanh_sx_id int, chi_tiet_phieu_dieu_chinh_id int",
}

FIXTURES = [
    "INSERT INTO LenhSanXuat VALUES (1,'LSX-202611-000001',1,NULL,2,3,10,7,'da_gui','2026-11-03T00:00:00Z',NULL,NULL)",
    "INSERT INTO ChiTietLenhSanXuat VALUES (1,1,4,20)",
    "INSERT INTO MatHang VALUES (4,999)",
    "INSERT INTO PhieuXuat VALUES (1,1,'xuat_vat_tu','da_duyet'),(2,1,'xuat_vat_tu','cho_duyet')",
    "INSERT INTO ChiTietPhieuXuat VALUES (1,1,4),(2,2,4)",
    "INSERT INTO ChungTuHoanThanhSx VALUES (1,1,'da_duyet')",
    "INSERT INTO PhieuDieuChinhKho VALUES (1,'da_duyet'),(2,'cho_duyet')",
    "INSERT INTO ChiTietPhieuDieuChinhKho VALUES (1,1,1),(2,1,2),(3,2,1),(4,1,NULL)",
    "INSERT INTO GiaoDichKho VALUES (1,4,'xuat_vat_tu',-20,NULL,1,NULL,NULL),(2,2,'nhap_san_pham_san_xuat',8,NULL,NULL,1,NULL),(3,4,'dieu_chinh_ton_kho',5,NULL,NULL,NULL,1),(4,2,'dieu_chinh_ton_kho',-2,NULL,NULL,NULL,2),(5,4,'dieu_chinh_ton_kho',10,NULL,NULL,NULL,3),(6,4,'dieu_chinh_ton_kho',100,NULL,NULL,NULL,4),(7,4,'xuat_vat_tu',-100,NULL,2,NULL,NULL)",
]


class AsyncConnection:
    def __init__(self, connection):
        self.connection = connection

    async def execute(self, statement, parameters=None):
        return self.connection.execute(statement, parameters or {})

    async def scalar(self, statement, parameters=None):
        return self.connection.scalar(statement, parameters or {})


@pytest.fixture
def repository():
    engine = create_engine("sqlite://")
    with engine.connect() as connection:
        connection.connection.create_function("strpos", 2, lambda s, q: s.find(q) + 1)
        for name, columns in TABLES.items():
            connection.execute(text(f'CREATE TABLE "{name}" ({columns})'))
        for sql in FIXTURES:
            connection.execute(text(sql))
        yield SqlAlchemyLenhSanXuatRepository(AsyncConnection(connection)), connection
    engine.dispose()


async def test_effective_output_counts_adjustments_once(repository):
    repo, _ = repository
    order = await repo.get_order(1)
    assert order.so_luong_da_hoan_thanh == 6
    assert order.so_luong_con_phai_hoan_thanh == 4
    assert order.nhu_cau_truc_tiep[0].so_luong_can == 20


async def test_materials_use_posted_source_not_current_stock(repository):
    repo, _ = repository
    result = await repo.materials(await repo.get_order(1))
    line = result.chi_tiet[0]
    assert line.so_luong_da_cap == 15
    assert line.so_luong_con_phai_cap == 5
    assert line.ton_hien_tai == 999
    assert result.du_dieu_kien_bat_dau is False


async def test_enough_materials_after_reversal(repository):
    repo, connection = repository
    connection.execute(text("UPDATE PhieuDieuChinhKho SET trang_thai='tu_choi' WHERE id=1"))
    result = await repo.materials(await repo.get_order(1))
    assert result.chi_tiet[0].so_luong_da_cap == 20
    assert result.du_dieu_kien_bat_dau is True


async def test_list_filter_and_pagination(repository):
    repo, _ = repository
    result = await repo.list_orders(LenhListQuery(q="202611", nhan_vien_id=7, sort="-id"))
    assert result.total == 1
    assert result.items[0].id == 1
    assert (await repo.list_orders(LenhListQuery(page=2, page_size=1))).items == []
    assert (await repo.list_orders(LenhListQuery(trang_thai="nhap"))).total == 0


async def test_cancel_is_blocked_even_if_net_quantity_is_zero(repository):
    repo, connection = repository
    connection.execute(text("UPDATE GiaoDichKho SET so_luong_bien_dong=20 WHERE id=3"))
    assert await repo.has_postings(1)
