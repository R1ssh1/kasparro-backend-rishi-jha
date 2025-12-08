"""Tests for CSV ingestion."""
import pytest
from pathlib import Path
from ingestion.csv_loader import CSVIngestion


@pytest.mark.asyncio
async def test_csv_normalize_record(db_session, mock_csv_data):
    """Test normalizing CSV record to unified schema."""
    ingestion = CSVIngestion(db_session)
    
    raw_record = mock_csv_data[0]
    normalized = ingestion.normalize_record(raw_record)
    
    assert normalized is not None
    assert normalized.source == "csv"
    assert normalized.external_id == "btc-csv"
    assert normalized.symbol == "BTC"
    assert normalized.name == "Bitcoin"


@pytest.mark.asyncio
async def test_csv_checkpoint_value(db_session, mock_csv_data):
    """Test checkpoint value generation for CSV."""
    ingestion = CSVIngestion(db_session)
    
    checkpoint = ingestion.get_checkpoint_value(mock_csv_data)
    
    assert checkpoint == "1"  # Number of records processed
