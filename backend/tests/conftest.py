"""Explicit goods-issue fixtures. Never connect to or seed the application DB."""

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
async def goods_issue_database():
    value = os.getenv("GOODS_ISSUE_TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set GOODS_ISSUE_TEST_DATABASE_URL to the dedicated PostgreSQL test server")
    url = make_url(value)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"localhost", "127.0.0.1"}
    assert url.port == 55465 and url.username == "goods_issue_test"
    assert url.database == "xbike_goods_issue_test"
    admin = await asyncpg.connect(
        host=url.host,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.database,
    )
    name = f"goods_issue_{uuid4().hex}_test"
    assert re.fullmatch(r"goods_issue_[0-9a-f]{32}_test", name)
    await admin.execute(f'CREATE DATABASE "{name}"')
    engine = create_async_engine(url.set(database=name), hide_parameters=True)
    try:
        connection = await asyncpg.connect(
            host=url.host, port=url.port, user=url.username, password=url.password, database=name
        )
        try:
            assert (
                await connection.fetchval(
                    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
                )
                == 0
            )
            await connection.execute(
                (Path(__file__).resolve().parents[2] / "infra/postgres/init.sql").read_text(
                    encoding="utf-8"
                )
            )
        finally:
            await connection.close()
        yield SimpleNamespace(
            engine=engine,
            sessions=async_sessionmaker(engine, expire_on_commit=False, autoflush=False),
        )
    finally:
        await engine.dispose()
        assert re.fullmatch(r"goods_issue_[0-9a-f]{32}_test", name)
        await admin.execute(f'DROP DATABASE "{name}"')
        await admin.close()


@pytest.fixture
async def goods_issue_client(goods_issue_database):
    async def test_db():
        async with goods_issue_database.sessions() as session:
            try:
                yield session
            finally:
                await session.rollback()

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = test_db
    try:
        # ASGITransport does not start lifespan/background cache/traffic application DB access.
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


@pytest.fixture
def goods_issue_auth():
    def headers(employee_id=2, roles=None, credential="fixture-hash"):
        token = create_access_token(
            employee_id, roles or ["quan_tri_vien"], credential_version=password_version(credential)
        )
        return {"Authorization": f"Bearer {token}"}

    return headers


class GoodsIssueScenario:
    def __init__(self, database):
        self.database = database
        self.component_ids = []
        self.output_id = None
        self.bom_id = None
        self.serial = 0

    async def sql(self, statement, **params):
        async with self.database.sessions() as session:
            rows = await session.execute(text(statement), params)
            result = rows.mappings().all() if rows.returns_rows else []
            await session.commit()
            return [dict(row) for row in result]

    async def scalar(self, statement, **params):
        rows = await self.sql(statement, **params)
        return next(iter(rows[0].values())) if rows else None

    async def source(
        self, *, production=7, available=0, assigned=2, kind="dap_ung", state="dang_thuc_hien"
    ):
        self.serial += 1
        source_id = await self.scalar(
            """INSERT INTO "YeuCauSanXuat"
            (ma_yeu_cau_san_xuat,loai_yeu_cau,mat_hang_id,so_luong,han_hoan_thanh,nhan_vien_id,nhan_vien_duoc_giao_id,bom_id,trang_thai,so_luong_dung_thanh_pham,so_luong_can_san_xuat,gui_at,kiem_tra_lan_dau_at)
            VALUES (:code,:kind,:output,:quantity,current_date,1,:assigned,:bom,:state,:available,:production,now(),now()) RETURNING id""",
            code=f"YCSX-202611-{self.serial:06d}",
            kind=kind,
            output=self.output_id,
            quantity=production + available,
            assigned=assigned,
            bom=self.bom_id,
            state=state,
            available=available,
            production=production,
        )
        if production:
            for item, multiplier in zip(self.component_ids, (1, 2), strict=True):
                await self.sql(
                    'INSERT INTO "NhuCauLinhKien" (yeu_cau_san_xuat_id,mat_hang_id,so_luong_can) VALUES (:source,:item,:quantity)',
                    source=source_id,
                    item=item,
                    quantity=production * multiplier,
                )
        return source_id

    async def hold(self, source, item, quantity, kind="linh_kien", completion=None):
        await self.sql(
            """INSERT INTO "GiuHang" (yeu_cau_san_xuat_id,mat_hang_id,so_luong,loai_giu,chung_tu_hoan_thanh_sx_id) VALUES (:source,:item,:quantity,:kind,:completion)""",
            source=source,
            item=item,
            quantity=quantity,
            kind=kind,
            completion=completion,
        )
        await self.sql(
            'UPDATE "MatHang" SET so_luong_dang_giu=so_luong_dang_giu+:quantity WHERE id=:item',
            quantity=quantity,
            item=item,
        )

    async def completion(self, source, quantity, state="da_duyet"):
        completion = await self.scalar(
            """INSERT INTO "ChungTuHoanThanhSx" (ma_phieu,yeu_cau_san_xuat_id,so_luong_hoan_thanh,nhan_vien_id,trang_thai,finish_time,nguoi_xu_ly_id,xu_ly_at) VALUES (:code,:source,:quantity,2,:state,now(),1,now()) RETURNING id""",
            code=f"HTSX-202611-{source:06d}",
            source=source,
            quantity=quantity,
            state=state,
        )
        return completion

    async def snapshot(self):
        result = {}
        for table in (
            "PhieuXuat",
            "ChiTietPhieuXuat",
            "MatHang",
            "GiuHang",
            "GiaoDichKho",
            "YeuCauSanXuat",
            "LichSuThaoTac",
        ):
            result[table] = await self.sql(f'SELECT * FROM "{table}" ORDER BY id')
        return result


@pytest.fixture
async def goods_issue_scenario(goods_issue_database):
    scenario = GoodsIssueScenario(goods_issue_database)
    for identifier, role in enumerate(("quan_ly", "nhan_vien", "quan_tri_vien"), 1):
        await scenario.sql(
            'INSERT INTO "VaiTro" (id,ma_vai_tro,ten_vai_tro) VALUES (:id,:role,:role)',
            id=identifier,
            role=role,
        )
    for identifier, role in ((1, 1), (2, 2), (3, 2), (4, 3), (5, 2)):
        await scenario.sql(
            "INSERT INTO \"NhanVien\" (id,vai_tro_id,ten_dang_nhap,mat_khau,ma_nhan_vien,trang_thai) VALUES (:id,:role,:login,'fixture-hash',:code,:state)",
            id=identifier,
            role=role,
            login=f"fixture{identifier}",
            code=f"NV-{identifier:06d}",
            state="bi_khoa" if identifier == 5 else "hoat_dong",
        )
    for kind, name, price in (
        ("linh_kien", "Frame", 12500),
        ("linh_kien", "Tyre", 5000),
        ("thanh_pham", "Bike", 123456),
    ):
        item = await scenario.scalar(
            "INSERT INTO \"MatHang\" (ten_mat_hang,sku,loai_mat_hang,don_vi_tinh,don_gia) VALUES (:name,:name,:kind,'piece',:price) RETURNING id",
            name=name,
            kind=kind,
            price=price,
        )
        if kind == "linh_kien":
            scenario.component_ids.append(item)
        else:
            scenario.output_id = item
    scenario.bom_id = await scenario.scalar(
        'INSERT INTO "Bom" (mat_hang_id,version) VALUES (:item,1) RETURNING id',
        item=scenario.output_id,
    )
    for item, quantity in zip(scenario.component_ids, (1, 2), strict=True):
        await scenario.sql(
            'INSERT INTO "ChiTietBom" (bom_id,mat_hang_id,so_luong) VALUES (:bom,:item,:quantity)',
            bom=scenario.bom_id,
            item=item,
            quantity=quantity,
        )
    ncc = await scenario.scalar(
        """INSERT INTO "NhaCungCap" (ten_ncc,so_dien_thoai,dia_chi,phuong,tinh) VALUES ('Fixture','1','Street','Ward','City') RETURNING id"""
    )
    receipt = await scenario.scalar(
        """INSERT INTO "PhieuNhap" (ma_phieu_nhap,nhan_vien_id,ncc_id,ngay_nhap) VALUES ('PN-202611-000001',1,:ncc,current_date) RETURNING id""",
        ncc=ncc,
    )
    details = []
    for item in scenario.component_ids:
        details.append(
            (
                item,
                await scenario.scalar(
                    'INSERT INTO "ChiTietPhieuNhap" (phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia) VALUES (:receipt,:item,100,1,100) RETURNING id',
                    receipt=receipt,
                    item=item,
                ),
            )
        )
    await scenario.sql(
        """UPDATE "PhieuNhap" SET trang_thai='hoan_thanh', tong_tien=200, hoan_thanh_at=now(),nguoi_hoan_thanh_id=1 WHERE id=:id""",
        id=receipt,
    )
    for item, detail in details:
        await scenario.sql(
            """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chi_tiet_phieu_nhap_id,nhan_vien_id) VALUES (:item,'nhap_linh_kien',100,100,:detail,1)""",
            item=item,
            detail=detail,
        )
        await scenario.sql('UPDATE "MatHang" SET so_luong_ton=100 WHERE id=:id', id=item)
    stock_source = await scenario.source(production=100, kind="cho_kho")
    completion = await scenario.completion(stock_source, 100)
    await scenario.sql(
        """INSERT INTO "GiaoDichKho" (mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chung_tu_hoan_thanh_sx_id,nhan_vien_id) VALUES (:item,'nhap_san_pham_san_xuat',100,100,:completion,1)""",
        item=scenario.output_id,
        completion=completion,
    )
    await scenario.sql('UPDATE "MatHang" SET so_luong_ton=100 WHERE id=:id', id=scenario.output_id)
    return scenario


@pytest.fixture
def goods_issue_pending(goods_issue_client, goods_issue_auth, goods_issue_scenario):
    async def create(*, kind="xuat_linh_kien", source=None, production=7, available=0):
        scenario = goods_issue_scenario
        if source is None:
            source = await scenario.source(production=production, available=available)
            if kind == "xuat_linh_kien":
                for item, multiplier in zip(scenario.component_ids, (1, 2), strict=True):
                    await scenario.hold(source, item, production * multiplier)
            else:
                if available:
                    await scenario.hold(source, scenario.output_id, available, "thanh_pham_co_san")
                if production:
                    completion = await scenario.completion(source, production)
                    await scenario.hold(
                        source, scenario.output_id, production, "thanh_pham_san_xuat", completion
                    )
        created = await goods_issue_client.post(
            "/api/v1/phieu_xuat",
            headers=goods_issue_auth(),
            json={"loai_phieu": kind, "yeu_cau_san_xuat_id": source},
        )
        assert created.status_code == 201, created.text
        submitted = await goods_issue_client.post(
            created.headers["location"] + "/gui",
            headers={**goods_issue_auth(), "If-Match": created.headers["etag"]},
            json={},
        )
        assert submitted.status_code == 200, submitted.text
        return created, submitted, source

    return create
