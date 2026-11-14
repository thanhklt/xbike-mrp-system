"""UC-15–19/BOM-AC-04–06: real v4 bootstrap, never the application database."""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import ConflictException, PreconditionFailedException
from app.dependencies import build_bom_service
from app.modules.bom.schemas import BomFormula, BomListQuery
from app.modules.mat_hang.cache import MatHangCache
from app.modules.mat_hang.repository import SqlAlchemyMatHangRepository
from app.modules.mat_hang.schemas import MatHangCreate
from app.modules.mat_hang.service import MatHangService

MANAGER = {"sub": "1", "roles": ["quan_ly"]}
FORMULA = {"chi_tiet": [{"mat_hang_id": 1, "so_luong": 2}]}


@pytest_asyncio.fixture
async def database():
    value = os.getenv("BOM_TEST_DATABASE_URL")
    if not value:
        pytest.skip("BOM_TEST_DATABASE_URL required; PostgreSQL behavior unverified")
    url = make_url(value)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"127.0.0.1", "localhost"} and url.username == "bom_test"
    assert url.database == "xbike_bom_test" and url.port == 55464
    name = "bom_" + uuid.uuid4().hex + "_test"
    admin = await asyncpg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        connection = await asyncpg.connect(
            url.set(drivername="postgresql", database=name).render_as_string(hide_password=False)
        )
        try:
            assert not await connection.fetchval(
                "SELECT EXISTS(SELECT FROM pg_tables WHERE schemaname='public')"
            )
            await connection.execute(
                (Path(__file__).parents[2] / "infra/postgres/init.sql").read_text(encoding="utf-8")
            )
            await connection.execute("""INSERT INTO "VaiTro"(id,ma_vai_tro,ten_vai_tro) VALUES
                (1,'quan_ly','Manager'),(2,'nhan_vien','Employee'),(3,'quan_tri_vien','Admin');
                INSERT INTO "NhanVien"(id,vai_tro_id,ten_dang_nhap,mat_khau,ma_nhan_vien,trang_thai) VALUES
                (1,1,'manager','test-hash','NV-000001','hoat_dong'),
                (2,2,'employee','test-hash','NV-000002','hoat_dong'),
                (3,3,'admin','test-hash','NV-000003','hoat_dong'),
                (4,1,'locked','test-hash','NV-000004','bi_khoa');
                INSERT INTO "MatHang"(ten_mat_hang,sku,loai_mat_hang,don_vi_tinh,don_gia)
                VALUES ('Frame','frame','linh_kien','chiec',100),('Wheel','wheel','linh_kien','bo',50);""")
        finally:
            await connection.close()
        engine = create_async_engine(url.set(database=name), hide_parameters=True)
        box = SimpleNamespace(
            engine=engine,
            sessions=async_sessionmaker(engine, expire_on_commit=False, autoflush=False),
            cache=MatHangCache(),
        )
        async with box.sessions() as session:
            box.cache.replace(await SqlAlchemyMatHangRepository(session).load_all())
        yield box
    finally:
        if engine:
            await engine.dispose()
        assert name.startswith("bom_") and len(name) == 41 and name.endswith("_test")
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.close()


@asynccontextmanager
async def services(box, *, cache=None):
    async with box.sessions() as session:
        boms = build_bom_service(session, cache if cache is not None else box.cache)
        catalog = MatHangService(
            SqlAlchemyMatHangRepository(session), boms.audit, boms.mutation, boms
        )
        yield boms, catalog, session


async def product(box, sku="bike"):
    async with services(box) as (_, catalog, _session):
        item, _ = await catalog.create_mat_hang(
            MatHangCreate(
                ten_mat_hang="Bike",
                sku=sku,
                loai_mat_hang="thanh_pham",
                don_vi_tinh="chiec",
                don_gia=1000,
                bom=FORMULA,
            ),
            MANAGER,
        )
    async with services(box) as (boms, _, _session):
        context = await boms.repository.context(item.id)
        return item.id, context.active.id


async def scalar(box, sql):
    async with box.sessions() as session:
        return await session.scalar(text(sql))


async def tag(box, bom_id):
    async with services(box) as (boms, _, _session):
        return (await boms.get_bom(bom_id, MANAGER, "test"))[1]


@pytest.mark.parametrize("sort,expected", [("version", [1, 3, 2]), ("-version", [2, 1, 3])])
async def test_uc15_ac5_stable_sort_ties_across_pages(database, sort, expected):
    _, first = await product(database, "bike-a")
    async with services(database) as (boms, _, _session):
        await boms.create_version(
            first, BomFormula(**FORMULA), MANAGER, await tag(database, first), "test"
        )
    await product(database, "bike-b")
    async with services(database) as (boms, _, _session):
        ids = []
        for page in range(1, 4):
            result = await boms.list_bom(
                BomListQuery(sort=sort, page=page, page_size=1), MANAGER, "test"
            )
            assert result.meta.total == 3 and result.meta.total_pages == 3
            ids.extend(v.id for v in result.data)
        assert ids == expected


async def test_uc16_ac5_atomic_create_and_generated_code(database):
    item_id, bom_id = await product(database)
    assert item_id == 3
    assert await scalar(database, 'SELECT ma_mat_hang FROM "MatHang" WHERE id=3') == "MH-000003"
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2
    assert await scalar(database, 'SELECT so_luong_ton FROM "MatHang" WHERE id=3') == 0
    assert await scalar(database, 'SELECT count(*) FROM "GiaoDichKho"') == 0
    assert database.cache.snapshot().by_id[item_id].is_active
    assert bom_id > 0


async def test_uc17_uc18_uc19_lifecycle_and_stale_validators(database):
    item_id, first = await product(database)
    original = await tag(database, first)
    async with services(database) as (boms, _, _session):
        result, second_tag = await boms.create_version(
            first,
            BomFormula(chi_tiet=[{"mat_hang_id": 2, "so_luong": 3}]),
            MANAGER,
            original,
            "test",
        )
        second = result.data.id
        assert result.data.version == 2
    assert original != await tag(database, first)
    async with services(database) as (boms, _, _session):
        await boms.activate_bom(first, MANAGER, await tag(database, first), "test")
    assert await scalar(database, f'SELECT is_active FROM "Bom" WHERE id={first}')
    assert await scalar(database, f'SELECT so_luong FROM "ChiTietBom" WHERE bom_id={first}') == 2
    async with services(database) as (boms, _, _session):
        with pytest.raises(PreconditionFailedException):
            await boms.delete_bom(second, MANAGER, second_tag)
    async with services(database) as (boms, _, _session):
        with pytest.raises(ConflictException):
            await boms.activate_bom(first, MANAGER, await tag(database, first), "test")
    async with services(database) as (boms, _, _session):
        await boms.delete_bom(first, MANAGER, await tag(database, first))
    assert not database.cache.snapshot().by_id[item_id].is_active
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 2
    assert await scalar(database, 'SELECT count(*) FROM "Bom" WHERE is_active') == 0
    assert await scalar(database, 'SELECT count(*) FROM "GiaoDichKho"') == 0


@pytest.mark.parametrize("point", ["add", "audit", "commit"])
async def test_bom_ac04_rollback_version_and_cache(database, monkeypatch, point):
    item, first = await product(database)
    old_tag = await tag(database, first)
    async with services(database) as (boms, _, session):
        if point == "add":
            original = boms.repository.add

            async def fail(*args, **kwargs):
                await original(*args, **kwargs)
                raise RuntimeError("injected after header/details")

            monkeypatch.setattr(boms.repository, "add", fail)
        elif point == "audit":

            async def fail(*args):
                raise RuntimeError("injected audit failure")

            monkeypatch.setattr(boms.audit, "append", fail)
        else:

            async def fail():
                raise RuntimeError("injected commit failure")

            monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(RuntimeError):
            await boms.create_version(first, BomFormula(**FORMULA), MANAGER, old_tag, "test")
    assert old_tag == await tag(database, first)
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 1
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == 2
    if point == "commit":
        assert not database.cache._available
    else:
        assert database.cache.snapshot().by_id[item].is_active


async def test_bom_ac05_two_real_sessions_same_etag(database):
    _, first = await product(database)
    old_tag = await tag(database, first)
    barrier = asyncio.Barrier(2)

    async def create():
        cache = MatHangCache()
        cache.replace(database.cache.snapshot().items)
        async with services(database, cache=cache) as (boms, _, _session):
            await barrier.wait()
            try:
                await boms.create_version(first, BomFormula(**FORMULA), MANAGER, old_tag, "test")
                return "created"
            except PreconditionFailedException:
                return "stale"

    assert sorted(await asyncio.wait_for(asyncio.gather(create(), create()), 10)) == [
        "created",
        "stale",
    ]
    assert await scalar(database, 'SELECT count(*) FROM "Bom" WHERE is_active') == 1
    assert await scalar(database, 'SELECT count(*) FROM "Bom"') == 2
    assert (
        await scalar(
            database, "SELECT count(*) FROM \"LichSuThaoTac\" WHERE thao_tac='tao_phien_ban'"
        )
        == 1
    )


async def test_uc15_filter_pagination_and_legacy_planning_port(database):
    _, first = await product(database)
    async with services(database) as (boms, _, _session):
        await boms.create_version(
            first, BomFormula(**FORMULA), MANAGER, await tag(database, first), "test"
        )
    async with services(database) as (boms, _, _session):
        result = await boms.list_bom(
            BomListQuery(is_active=False, version=1, page_size=1), MANAGER, "test"
        )
        assert result.meta.total == 1 and result.data[0].id == first
        empty = await boms.list_bom(BomListQuery(page=10**30), MANAGER, "test")
        assert empty.data == [] and empty.meta.total == 2
        from app.modules.bom.service import BomPlanningReader

        graph = await BomPlanningReader(boms.repository).active_graph()
        assert graph[3].components == ((1, 2),)


async def test_uc19_bom_ac06_trigger_blocks_hard_delete_and_detail_update(database):
    _, first = await product(database)
    from sqlalchemy.exc import DBAPIError

    for statement in [
        f'DELETE FROM "Bom" WHERE id={first}',
        f'UPDATE "ChiTietBom" SET so_luong=3 WHERE bom_id={first}',
    ]:
        async with database.sessions() as session:
            with pytest.raises(DBAPIError):
                await session.execute(text(statement))
            await session.rollback()
    assert await scalar(database, 'SELECT so_luong FROM "ChiTietBom" LIMIT 1') == 2


@pytest.mark.parametrize("action", ["stop", "activate"])
async def test_bom_ac04_state_and_audit_rollback(database, monkeypatch, action):
    item, first = await product(database)
    if action == "activate":
        async with services(database) as (boms, _, _session):
            await boms.delete_bom(first, MANAGER, await tag(database, first))
    before_tag = await tag(database, first)
    before_count = await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"')
    previous_state = database.cache.snapshot().by_id[item].is_active
    async with services(database) as (boms, _, _session):
        original = boms.audit.append

        async def fail(entry):
            await original(entry)
            raise RuntimeError("after audit, before commit")

        monkeypatch.setattr(boms.audit, "append", fail)
        with pytest.raises(RuntimeError):
            if action == "stop":
                await boms.delete_bom(first, MANAGER, before_tag)
            else:
                await boms.activate_bom(first, MANAGER, before_tag, "test")
    assert await tag(database, first) == before_tag
    assert await scalar(database, 'SELECT count(*) FROM "LichSuThaoTac"') == before_count
    assert database.cache.snapshot().by_id[item].is_active == previous_state


async def test_uc17_ac1_to4_uc19_ac6_preserves_committed_request_and_balances(database):
    item, first = await product(database)
    async with database.sessions() as session:
        await session.execute(
            text("""INSERT INTO "YeuCauSanXuat"(ma_yeu_cau_san_xuat,mat_hang_id,so_luong,
            han_hoan_thanh,nhan_vien_id,nhan_vien_duoc_giao_id,bom_id,trang_thai,gui_at)
            VALUES ('YCSX-202611-000001',:item,5,'2026-12-01',1,2,:bom,'da_gui',now())"""),
            {"item": item, "bom": first},
        )
        await session.execute(
            text("""INSERT INTO "NhuCauLinhKien"(yeu_cau_san_xuat_id,mat_hang_id,so_luong_can)
            VALUES (1,1,10)""")
        )
        await session.commit()

    async def snapshots():
        return [
            await scalar(database, statement)
            for statement in [
                'SELECT jsonb_agg(to_jsonb(y)) FROM "YeuCauSanXuat" y',
                'SELECT jsonb_agg(to_jsonb(n)) FROM "NhuCauLinhKien" n',
                'SELECT jsonb_agg(jsonb_build_array(id,so_luong_ton,so_luong_dang_giu,ton_kho_updated_at) ORDER BY id) FROM "MatHang"',
                'SELECT count(*) FROM "GiaoDichKho"',
                'SELECT count(*) FROM "GiuHang"',
            ]
        ]

    before = await snapshots()
    async with services(database) as (boms, _, _session):
        old, first_tag = await boms.get_bom(first, MANAGER, "test")
        assert old.data.da_duoc_su_dung
        new, second_tag = await boms.create_version(
            first,
            BomFormula(chi_tiet=[{"mat_hang_id": 2, "so_luong": 9}]),
            MANAGER,
            first_tag,
            "test",
        )
        second = new.data.id
    async with services(database) as (boms, _, _session):
        await boms.delete_bom(second, MANAGER, second_tag)
    assert await snapshots() == before


async def test_bom_ac05_independent_items_and_two_stops(database):
    first_item, first = await product(database, "bike-a")
    second_item, second = await product(database, "bike-b")
    first_tag, second_tag = await tag(database, first), await tag(database, second)
    barrier = asyncio.Barrier(2)

    async def stop(bom_id, etag):
        cache = MatHangCache()
        cache.replace(database.cache.snapshot().items)
        async with services(database, cache=cache) as (boms, _, _session):
            await barrier.wait()
            await boms.delete_bom(bom_id, MANAGER, etag)

    await asyncio.wait_for(asyncio.gather(stop(first, first_tag), stop(second, second_tag)), 10)
    assert not await scalar(database, f'SELECT is_active FROM "MatHang" WHERE id={first_item}')
    assert not await scalar(database, f'SELECT is_active FROM "MatHang" WHERE id={second_item}')


async def test_uc16_uc17_mapping_matches_actual_v4_schema(database):
    from sqlalchemy import inspect

    from app.modules.audit.models import LichSuThaoTac
    from app.modules.bom.models import Bom, ChiTietBom
    from app.modules.mat_hang.models import MatHang

    async with database.engine.connect() as connection:

        def verify(sync):
            inspector = inspect(sync)
            for model in (Bom, ChiTietBom, MatHang, LichSuThaoTac):
                columns = {c["name"]: c for c in inspector.get_columns(model.__tablename__)}
                assert set(columns) == set(model.__table__.columns.keys())
                for name, column in model.__table__.columns.items():
                    assert columns[name]["nullable"] == column.nullable, (model.__name__, name)
                    assert str(columns[name]["type"].compile(dialect=sync.dialect)) == str(
                        column.type.compile(dialect=sync.dialect)
                    )
                checks = {c["name"] for c in inspector.get_check_constraints(model.__tablename__)}
                mapped = {
                    c.name
                    for c in model.__table__.constraints
                    if c.__class__.__name__ == "CheckConstraint"
                }
                assert checks == mapped
                actual_fk = {
                    (tuple(f["constrained_columns"]), f["referred_table"])
                    for f in inspector.get_foreign_keys(model.__tablename__)
                }
                mapped_fk = {
                    ((f.parent.name,), f.column.table.name) for f in model.__table__.foreign_keys
                }
                assert actual_fk == mapped_fk
                assert columns["id"]["identity"]["always"] is False
            indexes = {i["name"] for i in inspector.get_indexes("Bom")}
            assert {"uq_bom_version", "uq_bom_dang_dung"} <= indexes

        await connection.run_sync(verify)


async def test_uc17_ac4_new_version_reactivates_stopped_product(database):
    item, first = await product(database)
    async with services(database) as (boms, _, _session):
        await boms.delete_bom(first, MANAGER, await tag(database, first))
    async with services(database) as (boms, _, _session):
        result, _ = await boms.create_version(
            first, BomFormula(**FORMULA), MANAGER, await tag(database, first), "test"
        )
        assert result.data.version == 2 and result.data.is_active
    assert database.cache.snapshot().by_id[item].is_active
    assert (
        await scalar(database, "SELECT count(*) FROM \"LichSuThaoTac\" WHERE thao_tac='dung_lai'")
        == 1
    )
