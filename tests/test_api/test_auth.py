"""Tests for API authentication."""
import pytest
from httpx import AsyncClient
from api.main import app
from core.config import settings


@pytest.mark.asyncio
async def test_protected_endpoint_without_api_key():
    """Test that protected endpoints reject requests without API key."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stats")
        assert response.status_code == 422  # Missing required header


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_api_key():
    """Test that protected endpoints reject invalid API keys."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_api_key(db_session):
    """Test that protected endpoints accept valid API keys."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats",
            headers={"X-API-Key": settings.admin_api_key}
        )
        # Should succeed (200) or fail with different error (not 401)
        assert response.status_code != 401


@pytest.mark.asyncio
async def test_runs_endpoint_requires_auth():
    """Test /runs endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Without API key
        response = await client.get("/runs")
        assert response.status_code == 422
        
        # With invalid API key
        response = await client.get(
            "/runs",
            headers={"X-API-Key": "wrong-key"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_compare_runs_requires_auth():
    """Test /compare-runs endpoint requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Without API key
        response = await client.get("/compare-runs?run1_id=abc&run2_id=def")
        assert response.status_code == 422
        
        # With invalid API key
        response = await client.get(
            "/compare-runs?run1_id=abc&run2_id=def",
            headers={"X-API-Key": "invalid"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_public_endpoints_no_auth():
    """Test that public endpoints don't require authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # These should work without API key
        response = await client.get("/")
        assert response.status_code == 200
        
        response = await client.get("/health")
        assert response.status_code == 200
        
        response = await client.get("/data")
        assert response.status_code == 200
        
        response = await client.get("/metrics")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_api_key_header_case_insensitive():
    """Test that X-API-Key header works (FastAPI normalizes header names)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try with different case variations
        response = await client.get(
            "/stats",
            headers={"x-api-key": settings.admin_api_key}
        )
        assert response.status_code != 401  # Should not fail auth
        
        response = await client.get(
            "/stats",
            headers={"X-Api-Key": settings.admin_api_key}
        )
        assert response.status_code != 401
