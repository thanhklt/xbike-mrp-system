import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


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
