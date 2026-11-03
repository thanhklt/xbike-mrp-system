import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def production_request_factory():
    from app.modules.san_xuat.schemas import YeuCauRead

    def make_request(**changes):
        values = dict(
            id=101,
            ma_yeu_cau_san_xuat="YCSX-202611-000101",
            mat_hang_id=1,
            so_luong=10,
            nhan_vien_id=2,
            nhan_vien_duoc_giao_id=3,
            trang_thai="nhap",
            created_at=datetime(2026, 11, 3, tzinfo=timezone.utc),
            completed_at=None,
            so_luong_con_phai_xuat=10,
        )
        return YeuCauRead(**(values | changes))

    return make_request


@pytest.fixture
def production_harness(production_request_factory, item_factory):
    from app.modules.san_xuat.service import YeuCauSanXuatService

    harness = SimpleNamespace(
        current=production_request_factory(),
        orders=[],
        repository=AsyncMock(),
        audit=AsyncMock(),
        transaction=AsyncMock(),
        items=AsyncMock(),
        employees=AsyncMock(),
        boms=AsyncMock(),
        issues=AsyncMock(),
    )
    harness.repository.get_by_id.side_effect = lambda resource_id: harness.current
    harness.repository.get_for_update.side_effect = lambda resource_id: harness.current
    harness.repository.has_dependencies.return_value = False
    harness.repository.lenh_cua_yeu_cau.side_effect = lambda *args, **kwargs: harness.orders
    harness.repository.add_lenh_tree.side_effect = lambda *args: harness.orders
    harness.repository.chung_tu_hoan_thanh_cua_lenh.return_value = []
    harness.issues.tong_da_xuat_thanh_pham.return_value = {}
    harness.issues.co_phieu_da_ghi_so.return_value = False
    harness.boms.active_graph.return_value = {}
    harness.items.read_items.return_value = [
        item_factory(1, loai_mat_hang="thanh_pham", so_luong_ton=20)
    ]

    async def update_request(resource_id, changes):
        harness.current = harness.current.model_copy(update=changes)
        return harness.current

    harness.repository.update.side_effect = update_request
    harness.repository.add.side_effect = lambda *args: harness.current
    harness.service = YeuCauSanXuatService(
        harness.repository,
        harness.audit,
        harness.transaction,
        harness.items,
        harness.employees,
        harness.boms,
        harness.issues,
    )
    return harness


@pytest.fixture
def item_factory():
    from app.modules.mat_hang.schemas import MatHangRead

    def make_item(item_id=1, **changes):
        values = dict(
            id=item_id,
            ma_mat_hang=f"MH-{item_id:06d}",
            sku=f"SKU-{item_id}",
            ten_mat_hang=f"Mặt hàng {item_id}",
            loai_mat_hang="linh_kien",
            don_vi_tinh="chiec",
            mau_sac=None,
            mo_ta=None,
            don_gia=None,
            is_active=True,
            so_luong_ton=0,
            ton_kho_updated_at=None,
        )
        return MatHangRead(**(values | changes))

    return make_item


@pytest.fixture
async def async_client():
    """Asynchronous test client fixture for FastAPI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def bootstrapped_connection():
    """Tests may write only inside a rollback on an explicitly separate test DB."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Requires a dedicated PostgreSQL database bootstrapped from init.sql and seed.sql"
        )
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("PostgreSQL tests require a database name ending in _test")
    engine = create_async_engine(url, hide_parameters=True)
    try:
        async with engine.connect() as connection:
            async with connection.begin() as transaction:
                yield connection
                await transaction.rollback()
    finally:
        await engine.dispose()
