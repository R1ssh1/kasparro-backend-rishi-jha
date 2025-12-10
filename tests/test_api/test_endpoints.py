"""Tests for API endpoints."""
import pytest
from httpx import AsyncClient
from api.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test /health endpoint returns status."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "database_connected" in data
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_data_endpoint_pagination():
    """Test /data endpoint with pagination."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/data?page=1&per_page=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "request_id" in data
        assert "api_latency_ms" in data
        assert "data" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["per_page"] == 10


@pytest.mark.asyncio
async def test_data_endpoint_filtering():
    """Test /data endpoint with filters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test symbol filter
        response = await client.get("/data?symbol=BTC")
        assert response.status_code == 200
        
        # Test price range filter
        response = await client.get("/data?min_price=1000&max_price=50000")
        assert response.status_code == 200
        
        # Test source filter
        response = await client.get("/data?source=coingecko")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns dashboard HTML."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Kasparro Crypto Dashboard" in response.content
