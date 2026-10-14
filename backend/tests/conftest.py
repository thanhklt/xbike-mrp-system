import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def async_client():
    """Asynchronous test client fixture for FastAPI app."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
