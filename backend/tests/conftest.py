"""Fixtures for goods flows and opt-in reporting/audit PostgreSQL checks.

Goods flows keep their dedicated test database guards. Reporting/audit uses
TEST_DATABASE_URL: postgres_database rolls back, while committed_postgres_database
persists setup and caller commits as documented by those tests.
"""

import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, password_version
from app.main import app


async def _add_employee(raw, role="quan_ly", prefix="postgres"):
    role_id = await raw.fetchval('SELECT id FROM "VaiTro" WHERE ma_vai_tro=$1', role)
    assert role_id is not None, f"Existing database is missing seed role {role}"
    return await raw.fetchrow(
        """
        INSERT INTO "NhanVien" (vai_tro_id, ten_dang_nhap, mat_khau)
        VALUES ($1, $2, 'test-credential-hash') RETURNING id, ma_nhan_vien
    """,
        role_id,
        f"{prefix}_{uuid4().hex}",
    )


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
        if (
            not statement.lstrip()
            .upper()
            .startswith(("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT"))
        ):
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
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
                autoflush=False,
            )
            async with factory() as session:
                yield SimpleNamespace(
                    engine=postgres_engine.engine,
                    connection=connection,
                    raw=raw,
                    session=session,
                    factory=factory,
                    statements=postgres_engine.statements,
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
            postgres_engine.engine,
            expire_on_commit=False,
            autoflush=False,
        )
        async with factory() as session:
            yield SimpleNamespace(
                engine=postgres_engine.engine,
                connection=connection,
                raw=raw,
                session=session,
                factory=factory,
                statements=postgres_engine.statements,
                add_employee=partial(_add_employee, raw),
            )


@pytest.fixture
async def receipt_api():
    """Real ASGI/service/inventory SQL with isolated in-memory persistence, no DB."""
    from fastapi import FastAPI, Request
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.exceptions import register_exception_handlers
    from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
    from app.dependencies import get_current_user_payload, get_receiving_service
    from app.modules.inventory.ports import InventoryWriter, ReceiptStock
    from app.modules.inventory.repository import SqlAlchemyInventoryRepository
    from app.modules.phieu_nhap.ports import ReceiptPart, ReceiptPosting, ReceivingRepository
    from app.modules.phieu_nhap.router import router
    from app.modules.phieu_nhap.schemas import PhieuNhapRead
    from app.modules.phieu_nhap.service import PhieuNhapService
    from app.shared.records import RecordPage

    data = {
        "receipts": {},
        "stock": {1: 10, 2: 20},
        "ledger": [],
        "audit": [],
        "parts": {
            1: ReceiptPart(1, "linh_kien", True),
            2: ReceiptPart(2, "linh_kien", True),
            3: ReceiptPart(3, "thanh_pham", True),
        },
        "production": {7: {"trang_thai": "cho_bo_sung_linh_kien"}},
    }
    pending = None
    sql_calls = []
    repository = AsyncMock(spec=ReceivingRepository)
    inventory = AsyncMock(spec=InventoryWriter)
    session = AsyncMock(spec=AsyncSession)
    audit = SimpleNamespace(append=AsyncMock())

    def current():
        return pending if pending is not None else data

    def begin():
        nonlocal pending
        if pending is None:
            pending = deepcopy(data)

    async def lock_receipt(record_id):
        begin()
        return current()["receipts"].get(record_id)

    async def lock_supplier(record_id):
        begin()
        return record_id == 1

    async def lock_parts(ids):
        begin()
        return [current()["parts"][key] for key in sorted(ids) if key in current()["parts"]]

    async def add_draft(payload, *, created_at):
        record_id = max(current()["receipts"], default=0) + 1
        record = PhieuNhapRead(
            id=record_id,
            ma_phieu_nhap=f"PN-202611-{record_id:06d}",
            nha_cung_cap={
                "id": payload.ncc_id,
                "ma_ncc": f"NCC-{payload.ncc_id:06d}",
                "ten_ncc": "Fixture supplier",
                "so_dien_thoai": "0900000000",
                "dia_chi": "Fixture address",
                "phuong": "Fixture ward",
                "tinh": "Fixture province",
            },
            **payload.model_dump(exclude={"items"}),
            created_at=created_at,
            updated_at=created_at,
            hoan_thanh_at=None,
            nguoi_hoan_thanh_id=None,
            phien_ban=1,
            items=[
                {"id": record_id * 100 + index, **item.model_dump()}
                for index, item in enumerate(payload.items, 1)
            ],
        )
        current()["receipts"][record_id] = record
        return record

    async def patch_draft(record_id, changes, items):
        before = current()["receipts"][record_id]
        updates = {
            **changes,
            "updated_at": datetime.now(timezone.utc),
            "phien_ban": before.phien_ban + 1,
        }
        if items is not None:
            updates["chi_tiet"] = [
                type(before.chi_tiet[0])(id=record_id * 100 + index, **item.model_dump())
                for index, item in enumerate(items, 1)
            ]
        after = before.model_copy(update=updates)
        current()["receipts"][record_id] = after
        return after

    async def delete_draft(record_id):
        del current()["receipts"][record_id]

    async def mark_completed(record_id, *, expected_version, actor_id, completed_at):
        before = current()["receipts"][record_id]
        if before.trang_thai != "nhap" or before.phien_ban != expected_version:
            return None
        after = before.model_copy(
            update={
                "trang_thai": "hoan_thanh",
                "hoan_thanh_at": completed_at,
                "nguoi_hoan_thanh_id": actor_id,
                "updated_at": completed_at,
                "phien_ban": expected_version + 1,
            }
        )
        current()["receipts"][record_id] = after
        return after

    async def postings(record_id):
        receipt = current()["receipts"][record_id]
        ids = {line.id for line in receipt.chi_tiet}
        return [
            ReceiptPosting(row["id"], row["source"], row["item"], row["quantity"], "nhap_linh_kien")
            for row in current()["ledger"]
            if row["source"] in ids
        ]

    async def lock_stock(ids):
        return [
            ReceiptStock(
                key,
                current()["parts"][key].loai_mat_hang,
                current()["parts"][key].is_active,
                current()["stock"][key],
                0,
                current()["stock"][key],
            )
            for key in sorted(ids)
            if key in current()["parts"] and key in current()["stock"]
        ]

    async def scalar(statement, params):
        assert pending is not None
        sql = " ".join(str(statement).split())
        sql_calls.append((sql, params.copy()))
        if sql.startswith('UPDATE "MatHang"'):
            current()["stock"][params["id"]] += params["quantity"]
            return current()["stock"][params["id"]]
        assert sql.startswith('INSERT INTO "GiaoDichKho"')
        assert "'nhap_linh_kien'" in sql and "so_luong_ton_sau" in sql
        assert any(
            record.trang_thai == "hoan_thanh"
            and any(line.id == params["source"] for line in record.chi_tiet)
            for record in current()["receipts"].values()
        )
        movement_id = len(current()["ledger"]) + 1
        current()["ledger"].append({"id": movement_id, **params})
        return movement_id

    async def append(entry):
        current()["audit"].append({**entry.model_dump(), "created_at": datetime.now(timezone.utc)})

    async def commit():
        nonlocal pending
        assert pending is not None
        data.clear()
        data.update(pending)
        pending = None

    async def rollback():
        nonlocal pending
        pending = None

    async def list_receipts(params):
        records = list(current()["receipts"].values())
        return RecordPage(records, len(records))

    repository.lock_receipt.side_effect = lock_receipt
    repository.lock_supplier.side_effect = lock_supplier
    repository.lock_parts.side_effect = lock_parts
    repository.add_draft.side_effect = add_draft
    repository.patch_draft.side_effect = patch_draft
    repository.delete_draft.side_effect = delete_draft
    repository.mark_completed.side_effect = mark_completed
    repository.receipt_postings.side_effect = postings
    repository.get_receipt.side_effect = lambda key: current()["receipts"].get(key)
    repository.list_receipts.side_effect = list_receipts
    inventory.lock_receipt_stock.side_effect = lock_stock
    inventory.receive_receipt.side_effect = SqlAlchemyInventoryRepository(session).receive_receipt
    audit.append.side_effect = append
    session.scalar.side_effect = scalar
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    service = PhieuNhapService(repository, audit, SqlAlchemyTransaction(session), inventory)
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(router, prefix="/api/v1")

    async def actor(request: Request):
        return {"sub": "10", "roles": [request.headers.get("x-role", "quan_ly")]}

    test_app.dependency_overrides[get_current_user_payload] = actor
    test_app.dependency_overrides[get_receiving_service] = lambda: service
    payload = {
        "ncc_id": 1,
        "ngay_nhap": "2026-11-16",
        "ghi_chu": "Draft",
        "chi_tiet": [{"mat_hang_id": 1, "so_luong": 50, "don_gia_thuc": 100}],
    }
    async with AsyncClient(
        transport=ASGITransport(test_app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        yield SimpleNamespace(
            client=client,
            data=data,
            repo=repository,
            inventory=inventory,
            session=session,
            audit=audit,
            service=service,
            payload=payload,
            sql_calls=sql_calls,
        )


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
        self, *, production=7, available=0, assigned=2, kind="xuat_giao", state="dang_thuc_hien"
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
    stock_source = await scenario.source(production=100, kind="nhap_kho")
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
