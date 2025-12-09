"""Tests for /stats endpoint."""
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from core.models import ETLRun
from core.config import settings
from api.main import app


@pytest.mark.asyncio
async def test_stats_endpoint(db_session):
    """Test /stats endpoint returns ETL statistics."""
    # Create some ETL run records
    run1 = ETLRun(
        run_id="test-run-1",
        source="coingecko",
        status="success",
        records_processed=100,
        records_failed=0,
        duration_seconds=5.5,
        started_at=datetime(2025, 12, 8, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 12, 8, 10, 0, 5, tzinfo=timezone.utc)
    )
    run2 = ETLRun(
        run_id="test-run-2",
        source="coingecko",
        status="success",
        records_processed=100,
        records_failed=0,
        duration_seconds=4.8,
        started_at=datetime(2025, 12, 9, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 12, 9, 10, 0, 4, tzinfo=timezone.utc)
    )
    run3 = ETLRun(
        run_id="test-run-3",
        source="csv",
        status="failed",
        records_processed=0,
        records_failed=10,
        duration_seconds=1.2,
        started_at=datetime(2025, 12, 9, 11, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2025, 12, 9, 11, 0, 1, tzinfo=timezone.utc),
        error_message="Connection timeout"
    )

    db_session.add_all([run1, run2, run3])
    await db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats",
            headers={"X-API-Key": settings.admin_api_key}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert "request_id" in data
    assert "api_latency_ms" in data
    assert "summary" in data
    assert "recent_runs" in data
    assert "timestamp" in data
    
    # Check summary statistics
    summaries = {s["source"]: s for s in data["summary"]}
    
    assert "coingecko" in summaries
    assert summaries["coingecko"]["total_runs"] == 2
    assert summaries["coingecko"]["successful_runs"] == 2
    assert summaries["coingecko"]["failed_runs"] == 0
    assert summaries["coingecko"]["total_records_processed"] == 200
    assert summaries["coingecko"]["average_duration_seconds"] is not None
    
    assert "csv" in summaries
    assert summaries["csv"]["total_runs"] == 1
    assert summaries["csv"]["successful_runs"] == 0
    assert summaries["csv"]["failed_runs"] == 1
    
    # Check recent runs (at least 3, could be more from other tests)
    assert len(data["recent_runs"]) >= 3
    # Find our test runs by run_id
    our_run_ids = {"test-run-1", "test-run-2", "test-run-3"}
    our_runs = [r for r in data["recent_runs"] if r["run_id"] in our_run_ids]
    assert len(our_runs) == 3
    # Should be ordered by started_at descending (newest first)
    assert our_runs[0]["run_id"] == "test-run-3"
    assert our_runs[1]["run_id"] == "test-run-2"
    assert our_runs[2]["run_id"] == "test-run-1"


@pytest.mark.asyncio
async def test_stats_endpoint_filter_by_source(db_session):
    """Test /stats endpoint filtering by source."""
    import uuid
    run1 = ETLRun(
        run_id=str(uuid.uuid4()),
        source="coingecko",
        status="success",
        records_processed=100,
        records_failed=0,
        duration_seconds=5.0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    run2 = ETLRun(
        run_id=str(uuid.uuid4()),
        source="csv",
        status="success",
        records_processed=10,
        records_failed=0,
        duration_seconds=1.0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    
    db_session.add_all([run1, run2])
    await db_session.commit()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats?source=coingecko",
            headers={"X-API-Key": settings.admin_api_key}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only show coingecko summary
    assert len(data["summary"]) == 1
    assert data["summary"][0]["source"] == "coingecko"
    
    # Should show coingecko runs (may include runs from previous tests)
    assert len(data["recent_runs"]) >= 1
    assert all(run["source"] == "coingecko" for run in data["recent_runs"])


@pytest.mark.asyncio
async def test_stats_endpoint_limit_recent_runs(db_session):
    """Test /stats endpoint limit parameter for recent runs."""
    import uuid
    # Create 5 runs
    for i in range(5):
        run = ETLRun(
            run_id=str(uuid.uuid4()),
            source="coingecko",
            status="success",
            records_processed=10,
            records_failed=0,
            duration_seconds=1.0,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc)
        )
        db_session.add(run)
    
    await db_session.commit()
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats?limit=3",
            headers={"X-API-Key": settings.admin_api_key}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should only return 3 most recent runs
    assert len(data["recent_runs"]) == 3


@pytest.mark.asyncio
async def test_stats_endpoint_empty_database():
    """Test /stats endpoint returns valid structure even with existing data."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/stats",
            headers={"X-API-Key": settings.admin_api_key}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "summary" in data
    assert "recent_runs" in data
    assert isinstance(data["summary"], list)
    assert isinstance(data["recent_runs"], list)
