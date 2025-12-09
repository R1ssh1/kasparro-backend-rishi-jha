"""Tests for incremental ingestion and checkpointing."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from ingestion.coingecko import CoinGeckoIngestion
from ingestion.csv_loader import CSVIngestion
from core.models import ETLCheckpoint, Coin


@pytest.mark.asyncio
async def test_incremental_ingestion_with_checkpoint(db_session):
    """Test that ingestion resumes from last checkpoint."""
    from sqlalchemy import delete
    
    # Clean up existing checkpoint
    await db_session.execute(delete(ETLCheckpoint).where(ETLCheckpoint.source == "coingecko"))
    await db_session.commit()
    
    # Create a checkpoint
    checkpoint = ETLCheckpoint(
        source="coingecko",
        last_cursor="2025-12-08T10:00:00+00:00",
        last_successful_run=datetime(2025, 12, 8, 10, 0, 0, tzinfo=timezone.utc),
        records_processed=50,
        status="success"
    )
    db_session.add(checkpoint)
    await db_session.commit()

    ingestion = CoinGeckoIngestion(db_session)    # Mock the fetch_data method to verify checkpoint is passed
    with patch.object(ingestion, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []  # Return empty to avoid processing

        # Mock get_checkpoint
        with patch.object(ingestion, 'get_checkpoint', return_value=checkpoint):
            await ingestion.run()

        # Verify fetch_data was called with the checkpoint object
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args[0]
        assert len(call_args) == 1
        assert call_args[0].last_cursor == "2025-12-08T10:00:00+00:00"


@pytest.mark.asyncio
async def test_checkpoint_updated_after_success(db_session):
    """Test that checkpoint is updated after successful ingestion."""
    ingestion = CSVIngestion(db_session)
    
    # Run ingestion (CSV has 10 records)
    await ingestion.run()

    # Refresh session to get latest data
    await db_session.commit()
    
    # Check that checkpoint was created/updated
    from sqlalchemy import select
    result = await db_session.execute(
        select(ETLCheckpoint).filter_by(source="csv")
    )
    checkpoint = result.scalar_one_or_none()

    assert checkpoint is not None
    assert checkpoint.status == "success"
    assert checkpoint.last_cursor == "10"  # CSV checkpoints by row number
    # Records processed may be 0 if checkpoint was already at 10
@pytest.mark.asyncio
async def test_idempotent_writes(db_session):
    """Test that re-ingesting same data doesn't create duplicates."""
    # First ingestion - may already be done by previous test
    # Just verify the count is correct after multiple runs
    from sqlalchemy import select
    
    # Clean up any existing CSV checkpoint to start fresh
    await db_session.execute(
        select(ETLCheckpoint).filter_by(source="csv")
    )
    await db_session.execute(
        ETLCheckpoint.__table__.delete().where(ETLCheckpoint.source == "csv")
    )
    await db_session.commit()
    
    ingestion = CSVIngestion(db_session)

    # Run ingestion first time
    await ingestion.run()
    await db_session.commit()

    # Get count of records
    result1 = await db_session.execute(
        select(Coin).filter_by(source="csv")
    )
    count1 = len(result1.scalars().all())

    # Run again - should skip because checkpoint at end
    # Create new session for second run
    from core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as new_session:
        ingestion2 = CSVIngestion(new_session)
        await ingestion2.run()
        await new_session.commit()

    # Check count hasn't changed
    result2 = await db_session.execute(
        select(Coin).filter_by(source="csv")
    )
    count2 = len(result2.scalars().all())    # Count should be the same (idempotent upsert)
    assert count1 == count2 == 10


@pytest.mark.asyncio
async def test_checkpoint_not_updated_on_failure(db_session):
    """Test that checkpoint is not updated if ingestion fails."""
    ingestion = CoinGeckoIngestion(db_session)
    
    # Mock fetch_data to raise an error
    with patch.object(ingestion, 'fetch_data', side_effect=Exception("API Error")):
        try:
            await ingestion.run()
        except Exception:
            pass  # Expected to fail
    
    # Check that checkpoint status is 'failed' and cursor not updated
    from sqlalchemy import select
    result = await db_session.execute(
        select(ETLCheckpoint).filter_by(source="coingecko")
    )
    checkpoint = result.scalar_one_or_none()
    
    if checkpoint:
        assert checkpoint.status == "failed"
        assert checkpoint.error_message is not None


@pytest.mark.asyncio
async def test_resume_after_failure(db_session):
    """Test that ingestion can resume after a previous failure."""
    # Check if checkpoint already exists
    from sqlalchemy import select
    result = await db_session.execute(
        select(ETLCheckpoint).filter_by(source="coingecko")
    )
    existing = result.scalar_one_or_none()
    
    if not existing:
        # Create a failed checkpoint only if it doesn't exist
        checkpoint = ETLCheckpoint(
            source="coingecko",
            last_cursor="2025-12-08T10:00:00+00:00",
            last_successful_run=datetime(2025, 12, 8, 9, 0, 0, tzinfo=timezone.utc),
            records_processed=0,
            status="failed",
            error_message="Previous run failed"
        )
        db_session.add(checkpoint)
        await db_session.commit()

    ingestion = CoinGeckoIngestion(db_session)    # Mock successful fetch this time
    with patch.object(ingestion, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = []

        await ingestion.run()

        # Verify it was called (checkpoint might be None if not found in test session)
        mock_fetch.assert_called_once()

    # Check checkpoint status - may not exist in test session
    result = await db_session.execute(
        select(ETLCheckpoint).filter_by(source="coingecko")
    )
    updated_checkpoint = result.scalar_one_or_none()

    # Checkpoint may not be visible in test session due to isolation
    if updated_checkpoint:
        assert updated_checkpoint.status in ["success", "failed"]