"""Opt-in receipt fixtures, guarded PostgreSQL v4 DBs; never use the app database."""

import os
import re
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.main import app


@pytest.fixture
async def goods_receipt_database():
    value = os.getenv("GOODS_RECEIPT_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set GOODS_RECEIPT_TEST_DATABASE_URL to the dedicated PostgreSQL test server")
    url = make_url(value)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"localhost", "127.0.0.1"} and url.port == 55466
    assert url.username == "goods_receipt_test" and url.database == "xbike_goods_receipt_test"
    admin = await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.database,
    )
    name = f"goods_receipt_{uuid4().hex}_test"
    assert re.fullmatch(r"goods_receipt_[0-9a-f]{32}_test", name)
    await admin.execute(f'CREATE DATABASE "{name}"')
    engine = create_async_engine(url.set(database=name), hide_parameters=True)
    try:
        bootstrap = await asyncpg.connect(
            host=url.host, port=url.port, user=url.username, password=url.password, database=name
        )
        try:
            assert (
                await bootstrap.fetchval(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                )
                == 0
            )
            await bootstrap.execute(
                (Path(__file__).resolve().parents[2] / "infra/postgres/init.sql").read_text(
                    encoding="utf-8"
                )
            )
        finally:
            await bootstrap.close()
        yield SimpleNamespace(
            engine=engine,
            sessions=async_sessionmaker(engine, expire_on_commit=False, autoflush=False),
        )
    finally:
        await engine.dispose()
        assert re.fullmatch(r"goods_receipt_[0-9a-f]{32}_test", name)
        await admin.execute(f'DROP DATABASE "{name}"')
        await admin.close()


@pytest.fixture
async def goods_receipt_client(goods_receipt_database):
    async def test_db():
        async with goods_receipt_database.sessions() as session:
            try:
                yield session
            finally:
                await session.rollback()

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    try:
        # ASGITransport does not run lifespan/cache listeners/traffic recorder on the app DB.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def goods_receipt_auth():
    def headers(employee_id=1, *, roles=None, credential="fixture-hash"):
        token = create_access_token(
            employee_id, roles or ["quan_tri_vien"], credential_version=password_version(credential)
        )
        return {"Authorization": f"Bearer {token}"}

    return headers


class ReceiptScenario:
    def __init__(self, database):
        self.database = database
        self.items = []
        self.suppliers = []
        self.output = None

    async def sql(self, statement, **params):
        async with self.database.sessions() as session:
            rows = await session.execute(text(statement), params)
            result = [dict(row) for row in rows.mappings()] if rows.returns_rows else []
            await session.commit()
            return result

    async def scalar(self, statement, **params):
        rows = await self.sql(statement, **params)
        return next(iter(rows[0].values())) if rows else None

    def payload(self, *, quantity=50, price=12500):
        return {
            "ncc_id": self.suppliers[0],
            "ngay_nhap": "2026-11-14",
            "ghi_chu": "Fixture receipt",
            "chi_tiet": [
                {"mat_hang_id": self.items[0], "so_luong": quantity, "don_gia_thuc": price}
            ],
        }

    async def snapshot(self):
        result = {}
        for table in (
            "PhieuNhap",
            "ChiTietPhieuNhap",
            "MatHang",
            "GiaoDichKho",
            "LichSuThaoTac",
            "GiuHang",
            "YeuCauSanXuat",
            "NhuCauLinhKien",
        ):
            result[table] = await self.sql(f'SELECT * FROM "{table}" ORDER BY id')
        return result


@pytest.fixture
async def goods_receipt_scenario(goods_receipt_database):
    scenario = ReceiptScenario(goods_receipt_database)
    for identifier, role in enumerate(("quan_ly", "nhan_vien", "quan_tri_vien"), 1):
        await scenario.sql(
            'INSERT INTO "VaiTro" (id,ma_vai_tro,ten_vai_tro) VALUES (:id,:role,:role)',
            id=identifier,
            role=role,
        )
    for identifier, role in ((1, 1), (2, 1), (3, 2), (4, 3), (5, 1)):
        await scenario.sql(
            """INSERT INTO "NhanVien" (id,vai_tro_id,ten_dang_nhap,mat_khau,ma_nhan_vien,trang_thai) VALUES (:id,:role,:login,'fixture-hash',:code,:state)""",
            id=identifier,
            role=role,
            login=f"fixture{identifier}",
            code=f"NV-{identifier:06d}",
            state="bi_khoa" if identifier == 5 else "hoat_dong",
        )
    for name in ("Supplier A", "Supplier B"):
        scenario.suppliers.append(
            await scenario.scalar(
                """INSERT INTO "NhaCungCap" (ten_ncc,so_dien_thoai,dia_chi,phuong,tinh) VALUES (:name,'1','Street','Ward','City') RETURNING id""",
                name=name,
            )
        )
    for kind, name, price in (
        ("linh_kien", "Frame", 20000),
        ("linh_kien", "Tyre", 5000),
        ("thanh_pham", "Bike", 123456),
    ):
        item = await scenario.scalar(
            """INSERT INTO "MatHang" (ten_mat_hang,sku,loai_mat_hang,don_vi_tinh,don_gia) VALUES (:name,:name,:kind,'piece',:price) RETURNING id""",
            name=name,
            kind=kind,
            price=price,
        )
        if kind == "linh_kien":
            scenario.items.append(item)
        else:
            scenario.output = item
    receipt = await scenario.scalar(
        """INSERT INTO "PhieuNhap" (ma_phieu_nhap,nhan_vien_id,ncc_id,ngay_nhap,created_at,updated_at) VALUES ('PN-200001-000001',1,:ncc,'2000-01-01','2000-01-01T00:00:00Z','2000-01-01T00:00:00Z') RETURNING id""",
        ncc=scenario.suppliers[0],
    )
    details = []
    for item, quantity in zip(scenario.items, (10, 20), strict=True):
        detail = await scenario.scalar(
            'INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia) VALUES (:receipt,:item,:quantity,1,:amount) RETURNING id',
            receipt=receipt,
            item=item,
            quantity=quantity,
            amount=quantity,
        )
        details.append((item, quantity, detail))
    await scenario.sql(
        """UPDATE "PhieuNhap" SET trang_thai='hoan_thanh', tong_tien=30, hoan_thanh_at='2000-01-01T00:00:00Z',nguoi_hoan_thanh_id=1 WHERE id=:id""",
        id=receipt,
    )
    for item, quantity, detail in details:
        await scenario.sql(
            """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chi_tiet_phieu_nhap_id,nhan_vien_id) VALUES (:item,'nhap_linh_kien',:quantity,:quantity,:detail,1)""",
            item=item,
            quantity=quantity,
            detail=detail,
        )
        await scenario.sql(
            'UPDATE "MatHang" SET so_luong_ton=:quantity WHERE id=:id', quantity=quantity, id=item
        )
    bom = await scenario.scalar(
        'INSERT INTO "Bom" (mat_hang_id,version) VALUES (:item,1) RETURNING id',
        item=scenario.output,
    )
    await scenario.sql(
        'INSERT INTO "ChiTietBom" (bom_id,mat_hang_id,so_luong) VALUES (:bom,:item,1)',
        bom=bom,
        item=scenario.items[0],
    )
    for serial, quantity, state in ((1, 10, "cho_bo_sung_linh_kien"), (2, 5, "dang_thuc_hien")):
        source = await scenario.scalar(
            """INSERT INTO "YeuCauSanXuat" (ma_yeu_cau_san_xuat,mat_hang_id,so_luong,han_hoan_thanh,nhan_vien_id,nhan_vien_duoc_giao_id,bom_id,trang_thai,so_luong_dung_thanh_pham,so_luong_can_san_xuat,gui_at,kiem_tra_lan_dau_at) VALUES (:code,:output,:quantity,current_date,1,3,:bom,:state,0,:quantity,now(),now()) RETURNING id""",
            code=f"YCSX-202611-{serial:06d}",
            output=scenario.output,
            quantity=quantity,
            bom=bom,
            state=state,
        )
        await scenario.sql(
            'INSERT INTO "NhuCauLinhKien" (yeu_cau_san_xuat_id,mat_hang_id,so_luong_can) VALUES (:source,:item,:quantity)',
            source=source,
            item=scenario.items[0],
            quantity=quantity,
        )
        if serial == 2:
            await scenario.sql(
                """INSERT INTO "GiuHang" (yeu_cau_san_xuat_id,mat_hang_id,loai_giu,so_luong) VALUES (:source,:item,'linh_kien',5)""",
                source=source,
                item=scenario.items[0],
            )
            await scenario.sql(
                'UPDATE "MatHang" SET so_luong_dang_giu=5 WHERE id=:id', id=scenario.items[0]
            )
    return scenario


@pytest.fixture
def goods_receipt_draft(goods_receipt_client, goods_receipt_auth, goods_receipt_scenario):
    async def create(payload=None):
        response = await goods_receipt_client.post(
            "/api/v1/phieu_nhap",
            headers=goods_receipt_auth(),
            json=payload or goods_receipt_scenario.payload(),
        )
        assert response.status_code == 201, response.text
        return response

    return create
