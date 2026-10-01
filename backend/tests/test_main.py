import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Test standard health check endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data


@pytest.mark.asyncio
async def test_api_v1_ping(async_client: AsyncClient):
    """Test API v1 base ping endpoint."""
    response = await async_client.get("/api/v1/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "xBike MRP API v1 is active"
