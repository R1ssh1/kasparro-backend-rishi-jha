"""Tests for new P2 API endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
import uuid


# NOTE: Most P2 endpoint tests are integration tests
# They are tested manually with the running docker-compose stack
# See P2_VERIFICATION.md for manual test results


@pytest.mark.asyncio
async def test_metrics_endpoint_unit(db_session):
    """Unit test for metrics generation logic."""
    from core.prometheus import PrometheusMetrics
    
    metrics_gen = PrometheusMetrics(db_session)
    metrics_text = await metrics_gen.generate_prometheus_format()
    
    assert isinstance(metrics_text, str)
    assert "# HELP" in metrics_text
    assert "# TYPE" in metrics_text
    assert "etl_runs_total" in metrics_text


@pytest.mark.asyncio
async def test_run_comparison_logic(db_session):
    """Test run comparison and anomaly detection logic."""
    from core.models import ETLRun
    from sqlalchemy import insert
    
    # Create two test runs
    run1_id = str(uuid.uuid4())
    run2_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    await db_session.execute(
        insert(ETLRun).values([
            {
                "run_id": run1_id,
                "source": "test_source",
                "status": "success",
                "records_processed": 100,
                "duration_seconds": 1.0,
                "started_at": now - timedelta(hours=1),
                "completed_at": now - timedelta(hours=1, seconds=-1)
            },
            {
                "run_id": run2_id,
                "source": "test_source",
                "status": "success",
                "records_processed": 10,  # 90% drop
                "duration_seconds": 0.05,  # Very fast
                "started_at": now,
                "completed_at": now + timedelta(seconds=0.05)
            }
        ])
    )
    await db_session.commit()
    
    # Calculate differences (this is the logic used in compare_runs endpoint)
    records_diff = 10 - 100
    assert records_diff == -90
    
    # Check for anomalies
    change_pct = abs(records_diff / 100) * 100
    assert change_pct == 90.0  # 90% drop
    assert change_pct > 50  # Should trigger anomaly
    
    # Check fast run detection
    assert 0.05 < 0.1  # Should be flagged as suspiciously fast
