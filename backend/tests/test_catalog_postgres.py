"""Catalog AC-03–08: real bootstrap, locking, rollback and live receipt projection."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import Mock

import pytest
from sqlalchemy import event, inspect, text
from test_bom_api import client as client
from test_bom_api import headers
from test_bom_postgres import MANAGER, product, scalar, services
from test_bom_postgres import database as database
from test_catalog_service import SUPPLIER

from app.core.errors import ConflictException, PreconditionFailedException
from app.core.sqlalchemy_transaction import SqlAlchemyTransaction
from app.modules.audit.repository import SqlAlchemyAuditRepository
from app.modules.audit.service import AuditService
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.schemas import MatHangCreate, MatHangPatch
from app.modules.nha_cung_cap.models import NhaCungCap
from app.modules.nha_cung_cap.repository import SqlAlchemySupplierRepository
from app.modules.nha_cung_cap.schemas import NhaCungCapCreate, NhaCungCapListQuery, NhaCungCapPatch
from app.modules.nha_cung_cap.service import SupplierService
from app.modules.phieu_nhap.repository import SqlAlchemyPhieuNhapRepository
from app.modules.phieu_nhap.service import PhieuNhapService


@asynccontextmanager
async def suppliers(box):
    async with box.sessions() as session:
        service = SupplierService(
            SqlAlchemySupplierRepository(session),
            AuditService(SqlAlchemyAuditRepository(session)),
            SqlAlchemyTransaction(session),
        )
        yield service, session


async def create_supplier(box, **values):
    async with suppliers(box) as (service, _):
        return await service.create_supplier(
            NhaCungCapCreate(**{**SUPPLIER, **values}), MANAGER, "test"
        )


# UC-11 AC-1: thành phẩm mới có BOM v1 chưa dùng được đổi đơn vị tính.
async def test_finished_item_with_initial_formula_can_change_unit(client, database):
    item_id, bom_id = await product(database)
    read = await client.get(f"/api/v1/mat_hang/{item_id}", headers=headers())
    assert read.status_code == 200, read.text
    response = await client.patch(
        f"/api/v1/mat_hang/{item_id}",
        json={"don_vi_tinh": "bo"},
        headers={**headers(), "If-Match": read.headers["etag"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["don_vi_tinh"] == "bo"
    assert await scalar(database, f'SELECT don_vi_tinh FROM "MatHang" WHERE id={item_id}') == "bo"
    assert await scalar(database, f'SELECT version FROM "Bom" WHERE id={bom_id}') == 1
    assert await scalar(database, f'SELECT is_active FROM "Bom" WHERE id={bom_id}')


# UC-11 AC-2: linh kiện thuộc ChiTietBom không được đổi đơn vị tính.
async def test_formula_component_cannot_change_unit(client, database):
    await product(database)
    read = await client.get("/api/v1/mat_hang/1", headers=headers())
    assert read.status_code == 200, read.text
    audits = await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"')
    response = await client.patch(
        "/api/v1/mat_hang/1",
        json={"don_vi_tinh": "bo"},
        headers={**headers(), "If-Match": read.headers["etag"]},
    )
    assert response.status_code == 409, response.text
    assert await scalar(database, 'SELECT don_vi_tinh FROM "MatHang" WHERE id=1') == "chiec"
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == audits


async def test_cat_ac08_supplier_mapping_matches_real_schema(database):
    async with database.engine.connect() as connection:
        columns = await connection.run_sync(lambda conn: inspect(conn).get_columns("NhaCungCap"))
        checks = await connection.run_sync(
            lambda conn: inspect(conn).get_check_constraints("NhaCungCap")
        )
        unique = await connection.run_sync(
            lambda conn: inspect(conn).get_unique_constraints("NhaCungCap")
        )
    assert NhaCungCap.__name__ == NhaCungCap.__tablename__
    mapped = NhaCungCap.__table__.c
    assert {col["name"] for col in columns} == set(mapped.keys())
    for col in columns:
        assert col["nullable"] == mapped[col["name"]].nullable
        assert col["type"]._type_affinity == mapped[col["name"]].type._type_affinity
    assert next(col for col in columns if col["name"] == "id")["identity"]["always"] is False
    assert {row["name"] for row in checks} == {"ck_nha_cung_cap_ma", "ck_nha_cung_cap_thong_tin"}
    assert any(row["column_names"] == ["ma_ncc"] for row in unique)
    assert await scalar(
        database, "SELECT EXISTS (SELECT FROM pg_trigger WHERE tgname='trg_nha_cung_cap_ma')"
    )


@pytest.mark.parametrize("point", ["audit", "commit"])
async def test_uc11_ac08_update_rollback_keeps_cache_and_audit(database, monkeypatch, point):
    old = database.cache.snapshot()
    async with services(database) as (boms, catalog, session):
        _, tag = await boms.item_detail(1)
        if point == "audit":
            original = catalog.audit.append

            async def fail(entry):
                await original(entry)
                raise RuntimeError("after audit")

            monkeypatch.setattr(catalog.audit, "append", fail)
        else:

            async def fail():
                raise RuntimeError("commit failed")

            monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError):
            await catalog.patch_mat_hang(1, MatHangPatch(don_gia=200), tag, MANAGER)
    assert await scalar(database, 'SELECT don_gia FROM "MatHang" WHERE id=1') == 100
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0
    assert database.cache._snapshot is old
    if point == "commit":
        assert not database.cache._available


async def test_uc11_cat_ac05_two_independent_caches_one_winner(database):
    barrier = asyncio.Barrier(2)
    async with services(database) as (boms, _, _session):
        _, tag = await boms.item_detail(1)

    async def update(price):
        cache = MatHangCache()
        cache.replace(database.cache.snapshot().items)
        async with services(database, cache=cache) as (_, catalog, _session):
            await barrier.wait()
            try:
                await catalog.patch_mat_hang(1, MatHangPatch(don_gia=price), tag, MANAGER)
                return "saved"
            except PreconditionFailedException:
                return "stale"

    assert sorted(await asyncio.wait_for(asyncio.gather(update(120), update(130)), 10)) == [
        "saved",
        "stale",
    ]
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 1


async def test_uc09_ac06_stock_projection_and_read_only(client, database):
    async with database.sessions() as session:
        await session.execute(
            text('UPDATE "MatHang" SET so_luong_ton=10,so_luong_dang_giu=3 WHERE id=1')
        )
        await session.commit()
    from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository

    async with database.sessions() as session:
        database.cache.replace(await SqlAlchemyMatHangRepository(session).load_all())
    statements = []

    def observe(_conn, _cursor, statement, *_args):
        statements.append(statement.lstrip().upper())

    event.listen(database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        for path in ["mat_hang", "danh_muc_mat_hang/", "mat_hang/1"]:
            response = await client.get("/api/v1/" + path, headers=headers(2))
            assert response.status_code == 200, response.text
            data = response.json()["data"]
            row = data[0] if isinstance(data, list) else data
            assert [
                row[key] for key in ["so_luong_ton", "so_luong_dang_giu", "so_luong_con_dung"]
            ] == [10, 3, 7]
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", observe)
    assert not any(sql.startswith(("INSERT", "UPDATE", "DELETE")) for sql in statements)
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0


async def test_uc14_cat_ac08_identity_trigger_and_audit(database):
    first, tag = await create_supplier(database)
    assert first.data.ma_ncc == "NCC-000001"
    async with suppliers(database) as (service, _):
        read, current = await service.get_supplier(first.data.id, MANAGER, "other-request")
        assert current == tag and read.data == first.data
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 1
    snapshot = await scalar(database, 'SELECT du_lieu_sau FROM "LichSuThaoTac"')
    assert snapshot["ten_ncc"] == SUPPLIER["ten_ncc"]
    assert await scalar(database, 'SELECT created_at IS NOT NULL FROM "NhaCungCap"')


@pytest.mark.parametrize("point", ["audit", "commit"])
@pytest.mark.parametrize("operation", ["create", "patch"])
async def test_uc14_uc44_cat_ac04_rollback(database, monkeypatch, point, operation):
    created, tag = await create_supplier(database)
    async with suppliers(database) as (service, session):
        if point == "audit":
            original = service.audit.append

            async def fail(entry):
                await original(entry)
                raise RuntimeError("after audit")

            monkeypatch.setattr(service.audit, "append", fail)
        else:

            async def fail():
                raise RuntimeError("commit failed")

            monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError):
            if operation == "create":
                await service.create_supplier(NhaCungCapCreate(**SUPPLIER), MANAGER, "r")
            else:
                await service.patch_supplier(
                    created.data.id, NhaCungCapPatch(ten_ncc="Changed"), MANAGER, tag, "r"
                )
    assert await scalar(database, 'SELECT count(*) FROM "NhaCungCap"') == 1
    assert await scalar(database, 'SELECT ten_ncc FROM "NhaCungCap"') == SUPPLIER["ten_ncc"]
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 1


async def test_uc14_cat_ac04_concurrent_identity(database):
    barrier = asyncio.Barrier(2)

    async def create():
        await barrier.wait()
        return await create_supplier(database)

    results = await asyncio.wait_for(asyncio.gather(create(), create()), 10)
    assert {value[0].data.ma_ncc for value in results} == {"NCC-000001", "NCC-000002"}
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2


async def test_uc10_cat_ac08_concurrent_item_codes(database):
    barrier = asyncio.Barrier(2)

    async def create(sku):
        cache = MatHangCache()
        cache.replace(database.cache.snapshot().items)
        async with services(database, cache=cache) as (_, catalog, _session):
            await barrier.wait()
            return await catalog.create_mat_hang(
                MatHangCreate(
                    ten_mat_hang="New part",
                    sku=sku,
                    loai_mat_hang="linh_kien",
                    don_vi_tinh="chiec",
                    don_gia=5,
                ),
                MANAGER,
            )

    results = await asyncio.wait_for(asyncio.gather(create("one"), create("two")), 10)
    assert {row[0].ma_mat_hang for row in results} == {"MH-000003", "MH-000004"}
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2


async def test_uc44_cat_ac05_independent_suppliers_both_update(database):
    first, tag1 = await create_supplier(database)
    second, tag2 = await create_supplier(database)
    barrier = asyncio.Barrier(2)

    async def update(row, tag):
        async with suppliers(database) as (service, _session):
            await barrier.wait()
            return await service.patch_supplier(
                row.data.id, NhaCungCapPatch(ten_ncc=f"Changed {row.data.id}"), MANAGER, tag, "r"
            )

    results = await asyncio.wait_for(asyncio.gather(update(first, tag1), update(second, tag2)), 10)
    assert {row[0].data.ten_ncc for row in results} == {"Changed 1", "Changed 2"}
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 4


async def test_uc44_cat_ac05_two_sessions_one_winner(database):
    created, tag = await create_supplier(database)
    barrier = asyncio.Barrier(2)

    async def update(name):
        async with suppliers(database) as (service, _):
            await barrier.wait()
            try:
                await service.patch_supplier(
                    created.data.id, NhaCungCapPatch(ten_ncc=name), MANAGER, tag, "r"
                )
                return "saved"
            except PreconditionFailedException:
                return "stale"

    assert sorted(await asyncio.wait_for(asyncio.gather(update("One"), update("Two")), 10)) == [
        "saved",
        "stale",
    ]
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2


async def test_uc44_ac07_noop_has_no_update_or_audit(database):
    created, tag = await create_supplier(database)
    statements = []

    def observe(_conn, _cursor, statement, *_args):
        statements.append(statement.lstrip().upper())

    event.listen(database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        for body in [{}, SUPPLIER]:
            async with suppliers(database) as (service, _):
                result, current = await service.patch_supplier(
                    created.data.id, NhaCungCapPatch(**body), MANAGER, tag, "r"
                )
                assert current == tag and result.data == created.data
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", observe)
    assert not any(sql.startswith(("UPDATE", "INSERT", "DELETE")) for sql in statements)
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 1


async def test_uc14_cat_ac08_exhausted_code_returns_conflict(database):
    async with database.sessions() as session:
        await session.execute(text('ALTER SEQUENCE "NhaCungCap_id_seq" RESTART WITH 1000000'))
        await session.commit()
    with pytest.raises(ConflictException):
        await create_supplier(database)
    assert await scalar(database, 'SELECT count(*) FROM "NhaCungCap"') == 0
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 0


async def test_uc13_cat_ac03_literal_address_and_stable_pages(database):
    await create_supplier(database, ten_ncc="Same %_", tinh="  Hà Nội  ", phuong=" Phường A ")
    await create_supplier(database, ten_ncc="Same %_", tinh="HÀ NỘI", phuong="PHƯỜNG A")
    await create_supplier(database, ten_ncc="Other", tinh="Ha Noi", phuong="Phuong A")
    async with suppliers(database) as (service, _):
        found = []
        for page in [1, 2]:
            result = await service.list_suppliers(
                NhaCungCapListQuery(
                    q="%_",
                    tinh="hà nội",
                    phuong="phường a",
                    sort="-ten_ncc",
                    page=page,
                    page_size=1,
                ),
                MANAGER,
                "r",
            )
            assert result.meta.total == 2 and result.meta.total_pages == 2
            found.extend(item.id for item in result.data)
        assert found == [1, 2]
        result = await service.list_suppliers(NhaCungCapListQuery(phuong="phường a"), MANAGER, "r")
        assert result.meta.total == 2
        result = await service.list_suppliers(NhaCungCapListQuery(page=2**70), MANAGER, "r")
        assert result.data == [] and result.meta.total == 3


@pytest.mark.parametrize(
    "body", [{}, {"ten_mat_hang": "Frame", "don_gia": 100, "sku": "frame", "is_active": True}]
)
async def test_uc11_ac07_noop_no_update_audit_or_cache_publish(database, monkeypatch, body):
    snapshot = database.cache.snapshot()
    publish = Mock(wraps=database.cache.publish)
    monkeypatch.setattr(database.cache, "publish", publish)
    statements = []

    def observe(_conn, _cursor, statement, *_args):
        statements.append(statement.lstrip().upper())

    event.listen(database.engine.sync_engine, "before_cursor_execute", observe)
    try:
        async with services(database) as (boms, catalog, _):
            original, tag = await boms.item_detail(1)
            result, after = await catalog.patch_mat_hang(1, MatHangPatch(**body), tag, MANAGER)
            assert result == original and after == tag
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", observe)
    assert not any(sql.startswith(("UPDATE", "INSERT", "DELETE")) for sql in statements)
    publish.assert_not_called()
    assert database.cache.snapshot() is snapshot


@pytest.mark.parametrize("field,value", [("sku", "new-frame"), ("don_vi_tinh", "bo")])
async def test_uc11_ac01_referenced_fields_locked(database, field, value):
    await product(database)
    async with services(database) as (boms, catalog, _):
        _, tag = await boms.item_detail(1)
        with pytest.raises(ConflictException):
            await catalog.patch_mat_hang(1, MatHangPatch(**{field: value}), tag, MANAGER)
    assert await scalar(database, 'SELECT sku FROM "MatHang" WHERE id=1') == "frame"


async def test_uc11_ac01_unreferenced_sku_unit_and_audit(database):
    async with services(database) as (boms, catalog, _):
        _, tag = await boms.item_detail(1)
        result, current = await catalog.patch_mat_hang(
            1, MatHangPatch(sku="frame-new", don_vi_tinh="bo", don_gia=123), tag, MANAGER
        )
    assert current != tag and result.sku == "frame-new" and result.don_vi_tinh == "bo"
    assert (result.so_luong_ton, result.so_luong_dang_giu, result.so_luong_con_dung) == (0, 0, 0)
    assert database.cache.snapshot().by_id[1] == result
    before = await scalar(database, 'SELECT du_lieu_truoc FROM "LichSuThaoTac"')
    after = await scalar(database, 'SELECT du_lieu_sau FROM "LichSuThaoTac"')
    assert before["sku"] == "frame" and after["sku"] == "frame-new"


async def test_uc44_ac08_completed_receipt_live_supplier_and_tag_roundtrip(client, database):
    created, tag = await create_supplier(database)
    async with database.sessions() as session:
        await session.execute(
            text("""INSERT INTO "PhieuNhap" (ma_phieu_nhap,nhan_vien_id,ncc_id,ngay_nhap,tong_tien)
            VALUES ('PN-202611-000001',1,1,'2026-11-14',100);
            """)
        )
        await session.execute(
            text(
                """INSERT INTO "ChiTietPhieuNhap"(phieu_nhap_id,mat_hang_id,so_luong,don_gia_thuc,tong_gia) VALUES(1,1,1,100,100)"""
            )
        )
        await session.execute(
            text(
                """UPDATE "PhieuNhap" SET trang_thai='hoan_thanh',hoan_thanh_at=now(),nguoi_hoan_thanh_id=1 WHERE id=1"""
            )
        )
        await session.execute(
            text("""INSERT INTO "GiaoDichKho"(mat_hang_id,loai_giao_dich,so_luong_bien_dong,so_luong_ton_sau,chi_tiet_phieu_nhap_id,nhan_vien_id)
            VALUES (1,'nhap_linh_kien',1,1,1,1)""")
        )
        await session.execute(text('UPDATE "MatHang" SET so_luong_ton=1 WHERE id=1'))
        await session.commit()
    before = await client.get("/api/v1/phieu_nhap/1", headers=headers())
    assert before.status_code == 200, before.text
    async with database.sessions() as session:
        record = await SqlAlchemyPhieuNhapRepository(session).lock_receipt(1)
        assert PhieuNhapService.detail_response(record, "r")[1] == before.headers["etag"]
    async with suppliers(database) as (service, _):
        await service.patch_supplier(
            created.data.id, NhaCungCapPatch(ten_ncc="Current vendor"), MANAGER, tag, "r"
        )
    after = await client.get("/api/v1/phieu_nhap/1", headers=headers())
    assert after.status_code == 200, after.text
    assert after.json()["data"]["nha_cung_cap"]["ten_ncc"] == "Current vendor"
    assert after.headers["etag"] != before.headers["etag"]
    assert {k: v for k, v in before.json()["data"].items() if k != "nha_cung_cap"} == {
        k: v for k, v in after.json()["data"].items() if k != "nha_cung_cap"
    }
    listing = await client.get("/api/v1/phieu_nhap", headers=headers())
    assert (
        listing.status_code == 200
        and listing.json()["data"][0]["nha_cung_cap"]["ten_ncc"] == "Current vendor"
    )
    async with database.sessions() as session:
        record = await SqlAlchemyPhieuNhapRepository(session).lock_receipt(1)
        assert PhieuNhapService.detail_response(record, "r")[1] == after.headers["etag"]
    assert await scalar(database, 'SELECT so_luong_ton FROM "MatHang" WHERE id=1') == 1
    assert await scalar(database, 'SELECT count(*) FROM "GiaoDichKho"') == 1


async def test_uc44_ac08_draft_receipt_projection_and_stale_tag(client, database):
    supplier, tag = await create_supplier(database)
    created = await client.post(
        "/api/v1/phieu_nhap",
        headers=headers(),
        json={
            "ncc_id": supplier.data.id,
            "ngay_nhap": "2026-11-14",
            "chi_tiet": [{"mat_hang_id": 1, "so_luong": 1, "don_gia_thuc": 100}],
        },
    )
    assert created.status_code == 201, created.text
    path = created.headers["location"]
    read = await client.get(path, headers=headers())
    assert read.status_code == 200 and read.headers["etag"] == created.headers["etag"]
    item_read = await client.get("/api/v1/mat_hang/1", headers=headers())
    for payload in [{"don_vi_tinh": "bo"}, {"sku": "changed"}]:
        conflict = await client.patch(
            "/api/v1/mat_hang/1",
            headers={**headers(), "If-Match": item_read.headers["etag"]},
            json=payload,
        )
        assert conflict.status_code == 409, conflict.text
    async with suppliers(database) as (service, _):
        await service.patch_supplier(
            supplier.data.id, NhaCungCapPatch(dia_chi="New address"), MANAGER, tag, "r"
        )
    stale = await client.patch(
        path, json={}, headers={**headers(), "If-Match": read.headers["etag"]}
    )
    assert stale.status_code == 412, stale.text
    fresh = await client.get(path, headers=headers())
    noop = await client.patch(
        path, json={}, headers={**headers(), "If-Match": fresh.headers["etag"]}
    )
    assert noop.status_code == 200 and noop.headers["etag"] == fresh.headers["etag"], noop.text
    assert noop.json()["data"]["nha_cung_cap"]["dia_chi"] == "New address"
    audit = await scalar(
        database, "SELECT du_lieu_sau FROM \"LichSuThaoTac\" WHERE loai_doi_tuong='phieu_nhap'"
    )
    assert "nha_cung_cap" not in audit and audit["ncc_id"] == supplier.data.id
    assert await scalar(database, 'SELECT count(*) FROM "GiaoDichKho"') == 0


async def test_uc44_ac01_ac04_ac06_new_address_filters_and_audit(client, database):
    original, tag = await create_supplier(database)
    path = f"/api/v1/nha_cung_cap/{original.data.id}"
    changes = {"so_dien_thoai": "not-a-phone", "tinh": "  New province  ", "phuong": "\tNew ward\t"}
    response = await client.patch(path, headers={**headers(), "If-Match": tag}, json=changes)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["ma_ncc"] == original.data.ma_ncc
    found = await client.get(
        "/api/v1/nha_cung_cap",
        params={"tinh": "NEW PROVINCE", "phuong": "new WARD"},
        headers=headers(),
    )
    old = await client.get(
        "/api/v1/nha_cung_cap", params={"tinh": SUPPLIER["tinh"]}, headers=headers()
    )
    assert found.json()["meta"]["total"] == 1 and old.json()["data"] == []
    assert {key: response.json()["data"][key] for key in changes} == changes
    before = await scalar(
        database, "SELECT du_lieu_truoc FROM \"LichSuThaoTac\" WHERE thao_tac='sua'"
    )
    after = await scalar(database, "SELECT du_lieu_sau FROM \"LichSuThaoTac\" WHERE thao_tac='sua'")
    assert before == original.data.model_dump(mode="json")
    assert after == response.json()["data"]


async def test_cat_ac01_role_and_account_changes_apply_to_existing_token(client, database):
    auth = headers()
    assert (await client.get("/api/v1/nha_cung_cap", headers=auth)).status_code == 200
    async with database.sessions() as session:
        await session.execute(text('UPDATE "NhanVien" SET vai_tro_id=2 WHERE id=1'))
        await session.commit()
    assert (await client.get("/api/v1/nha_cung_cap", headers=auth)).status_code == 403
    assert (await client.get("/api/v1/mat_hang", headers=auth)).status_code == 200
    async with database.sessions() as session:
        await session.execute(text("UPDATE \"NhanVien\" SET trang_thai='bi_khoa' WHERE id=1"))
        await session.commit()
    assert (await client.get("/api/v1/mat_hang", headers=auth)).status_code == 403


async def test_uc12_ac01_repeated_stop_does_not_publish_or_audit(database, monkeypatch):
    item_id, _bom = await product(database)
    async with services(database) as (boms, catalog, _session):
        _, tag = await boms.item_detail(item_id)
        await catalog.delete_mat_hang(item_id, tag, MANAGER)
    before = await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"')
    publish = Mock(wraps=database.cache.publish)
    monkeypatch.setattr(database.cache, "publish", publish)
    async with services(database) as (boms, catalog, _session):
        _, tag = await boms.item_detail(item_id)
        await catalog.delete_mat_hang(item_id, tag, MANAGER)
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == before
    publish.assert_not_called()


async def test_uc11_q2_stock_prevents_sku_change(database):
    async with database.sessions() as session:
        await session.execute(text('UPDATE "MatHang" SET so_luong_ton=2 WHERE id=1'))
        await session.commit()
    async with services(database) as (boms, catalog, _session):
        _, tag = await boms.item_detail(1)
        with pytest.raises(ConflictException):
            await catalog.patch_mat_hang(1, MatHangPatch(sku="another"), tag, MANAGER)
