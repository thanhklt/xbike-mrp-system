from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_current_user_payload, get_inventory_service
from app.main import app
from app.modules.inventory.schemas import StockLevelResponse, StockMovementResponse
from app.modules.inventory.service import InventoryService
from app.shared.pagination import PageParams
from app.shared.records import RecordPage


class FakeInventoryRepository:
    def __init__(self):
        self.stock_items = [
            StockLevelResponse(
                id=1,
                mat_hang_id=10,
                so_luong=100,
                updated_at=datetime(2026, 10, 1, 10, 0, 0),
            ),
            StockLevelResponse(
                id=2,
                mat_hang_id=20,
                so_luong=50,
                updated_at=datetime(2026, 10, 2, 10, 0, 0),
            ),
        ]
        self.movement_items = [
            StockMovementResponse(
                id=1,
                mat_hang_id=10,
                loai_giao_dich="nhap_vat_tu",
                so_luong_bien_dong=100,
                so_luong_hieu_luc=90,  # Adjusted by -10
                chi_tiet_phieu_nhap_id=1,
                chi_tiet_phieu_xuat_id=None,
                chung_tu_hoan_thanh_sx_id=None,
                chi_tiet_phieu_dieu_chinh_id=None,
                nhan_vien_id=1,
                posted_at=datetime(2026, 10, 1, 8, 0, 0),
            ),
            StockMovementResponse(
                id=2,
                mat_hang_id=10,
                loai_giao_dich="dieu_chinh_ton_kho",
                so_luong_bien_dong=-10,
                so_luong_hieu_luc=-10,
                chi_tiet_phieu_nhap_id=None,
                chi_tiet_phieu_xuat_id=None,
                chung_tu_hoan_thanh_sx_id=None,
                chi_tiet_phieu_dieu_chinh_id=1,
                nhan_vien_id=1,
                posted_at=datetime(2026, 10, 2, 9, 0, 0),
            ),
        ]
        self.last_stock_filter_mat_hang = None
        self.last_movement_filter_mat_hang = None
        self.last_movement_filter_loai = None

    async def list_stock(
        self, params: PageParams, mat_hang_id: int | None = None
    ) -> RecordPage[StockLevelResponse]:
        self.last_stock_filter_mat_hang = mat_hang_id
        filtered = self.stock_items
        if mat_hang_id is not None:
            filtered = [item for item in filtered if item.mat_hang_id == mat_hang_id]
        return RecordPage(filtered, len(filtered))

    async def get_stock_by_mat_hang(self, mat_hang_id: int) -> StockLevelResponse | None:
        for item in self.stock_items:
            if item.mat_hang_id == mat_hang_id:
                return item
        return None

    async def list_movements(
        self,
        params: PageParams,
        mat_hang_id: int | None = None,
        loai_giao_dich: str | None = None,
    ) -> RecordPage[StockMovementResponse]:
        self.last_movement_filter_mat_hang = mat_hang_id
        self.last_movement_filter_loai = loai_giao_dich
        filtered = self.movement_items
        if mat_hang_id is not None:
            filtered = [m for m in filtered if m.mat_hang_id == mat_hang_id]
        if loai_giao_dich is not None:
            filtered = [m for m in filtered if m.loai_giao_dich == loai_giao_dich]
        return RecordPage(filtered, len(filtered))

    async def get_movement_by_id(self, movement_id: int) -> StockMovementResponse | None:
        for m in self.movement_items:
            if m.id == movement_id:
                return m
        return None


@pytest.fixture
def fake_repo():
    return FakeInventoryRepository()


@pytest.fixture
def client_with_auth(fake_repo):
    fake_service = InventoryService(fake_repo)

    app.dependency_overrides[get_current_user_payload] = lambda: {
        "sub": "1",
        "roles": ["quan_ly"],
    }
    app.dependency_overrides[get_inventory_service] = lambda: fake_service

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client, fake_repo

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_unauthenticated_requests_return_401(async_client: AsyncClient):
    """Mọi request thiếu JWT header đều phải bị chặn 401 Unauthorized."""
    endpoints = [
        "/api/v1/ton_kho",
        "/api/v1/ton_kho/10",
        "/api/v1/giao_dich_kho",
        "/api/v1/giao_dich_kho/1",
    ]
    for url in endpoints:
        resp = await async_client.get(url)
        assert resp.status_code == 401, f"{url} should return 401 unauthenticated"


@pytest.mark.asyncio
async def test_get_ton_kho_list(client_with_auth):
    """API-029: GET /api/v1/ton_kho trả danh sách phân trang chuẩn."""
    client, repo = client_with_auth
    resp = await client.get("/api/v1/ton_kho?page=1&page_size=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "data" in data
    assert len(data["data"]) == 2
    assert data["pagination"]["total_items"] == 2
    assert data["pagination"]["page"] == 1


@pytest.mark.asyncio
async def test_get_ton_kho_list_with_filter(client_with_auth):
    """API-029: Lọc tồn kho theo mat_hang_id."""
    client, repo = client_with_auth
    resp = await client.get("/api/v1/ton_kho?mat_hang_id=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["mat_hang_id"] == 10
    assert repo.last_stock_filter_mat_hang == 10


@pytest.mark.asyncio
async def test_get_ton_kho_detail_success_with_etag(client_with_auth):
    """API-030: GET /api/v1/ton_kho/{mat_hang_id} trả detail kèm header ETag."""
    client, _ = client_with_auth
    resp = await client.get("/api/v1/ton_kho/10")
    assert resp.status_code == 200
    assert "etag" in resp.headers
    etag = resp.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    body = resp.json()
    assert body["mat_hang_id"] == 10
    assert body["so_luong"] == 100


@pytest.mark.asyncio
async def test_get_ton_kho_detail_not_found(client_with_auth):
    """API-030: Mặt hàng không tồn tại trả 404."""
    client, _ = client_with_auth
    resp = await client.get("/api/v1/ton_kho/999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_get_giao_dich_kho_list_and_effective_quantity(client_with_auth):
    """API-031: GET /api/v1/giao_dich_kho phân biệt so_luong_bien_dong và so_luong_hieu_luc."""
    client, _ = client_with_auth
    resp = await client.get("/api/v1/giao_dich_kho")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    items = data["data"]
    assert len(items) == 2

    # Giao dịch nhập nguồn: biến động +100 nhưng lượng hiệu lực đã điều chỉnh còn +90
    item_nhap = next(m for m in items if m["loai_giao_dich"] == "nhap_vat_tu")
    assert item_nhap["so_luong_bien_dong"] == 100
    assert item_nhap["so_luong_hieu_luc"] == 90

    # Giao dịch điều chỉnh: biến động -10, lượng hiệu lực -10
    item_dc = next(m for m in items if m["loai_giao_dich"] == "dieu_chinh_ton_kho")
    assert item_dc["so_luong_bien_dong"] == -10
    assert item_dc["so_luong_hieu_luc"] == -10


@pytest.mark.asyncio
async def test_get_giao_dich_kho_list_filters(client_with_auth):
    """API-031: Lọc giao dịch kho theo mat_hang_id và loai_giao_dich."""
    client, repo = client_with_auth
    resp = await client.get("/api/v1/giao_dich_kho?mat_hang_id=10&loai_giao_dich=nhap_vat_tu")
    assert resp.status_code == 200
    assert repo.last_movement_filter_mat_hang == 10
    assert repo.last_movement_filter_loai == "nhap_vat_tu"
    data = resp.json()
    assert len(data["data"]) == 1


@pytest.mark.asyncio
async def test_get_giao_dich_kho_detail_success_with_etag(client_with_auth):
    """API-032: GET /api/v1/giao_dich_kho/{id} trả detail kèm header ETag."""
    client, _ = client_with_auth
    resp = await client.get("/api/v1/giao_dich_kho/1")
    assert resp.status_code == 200
    assert "etag" in resp.headers
    etag = resp.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    body = resp.json()
    assert body["id"] == 1
    assert body["so_luong_bien_dong"] == 100
    assert body["so_luong_hieu_luc"] == 90


@pytest.mark.asyncio
async def test_get_giao_dich_kho_detail_not_found(client_with_auth):
    """API-032: Giao dịch không tồn tại trả 404."""
    client, _ = client_with_auth
    resp = await client.get("/api/v1/giao_dich_kho/999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_validation_errors_return_422(client_with_auth):
    """Test validation query / path trả mã lỗi 422."""
    client, _ = client_with_auth
    # mat_hang_id must be > 0
    resp1 = await client.get("/api/v1/ton_kho?mat_hang_id=0")
    assert resp1.status_code == 422

    resp2 = await client.get("/api/v1/ton_kho/-5")
    assert resp2.status_code == 422

    resp3 = await client.get("/api/v1/giao_dich_kho/invalid_id")
    assert resp3.status_code == 422
