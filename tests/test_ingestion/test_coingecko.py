"""Tests for CoinGecko ingestion."""
import pytest
from unittest.mock import AsyncMock, patch
from ingestion.coingecko import CoinGeckoIngestion


@pytest.mark.asyncio
async def test_coingecko_normalize_record(db_session, mock_coingecko_response):
    """Test normalizing CoinGecko record to unified schema."""
    ingestion = CoinGeckoIngestion(db_session)
    
    raw_record = mock_coingecko_response[0]
    normalized = ingestion.normalize_record(raw_record)
    
    assert normalized is not None
    assert normalized.source == "coingecko"
    assert normalized.external_id == "bitcoin"
    assert normalized.symbol == "BTC"
    assert normalized.name == "Bitcoin"
    assert float(normalized.current_price) == 45000.0


@pytest.mark.asyncio
async def test_coingecko_fetch_data_success(db_session, mock_coingecko_response):
    """Test successful data fetch from CoinGecko API."""
    ingestion = CoinGeckoIngestion(db_session)
    
    with patch.object(ingestion, '_make_request', new_callable=AsyncMock) as mock_request:
        # Mock returns same data for both pages (page 1 and page 2)
        mock_request.return_value = mock_coingecko_response
        
        records = await ingestion.fetch_data()
        
        # Should fetch 2 pages, each with 2 records = 4 total
        assert len(records) == 4
        assert records[0]['id'] == 'bitcoin'
        assert records[1]['id'] == 'ethereum'
        # Second page duplicates (same mock data)
        assert records[2]['id'] == 'bitcoin'
        assert records[3]['id'] == 'ethereum'


@pytest.mark.asyncio
async def test_coingecko_normalize_invalid_record(db_session):
    """Test handling of invalid records."""
    ingestion = CoinGeckoIngestion(db_session)
    
    invalid_record = {
        "id": "invalid",
        # Missing required fields
    }
    
    normalized = ingestion.normalize_record(invalid_record)
    assert normalized is None


@pytest.mark.asyncio
async def test_coingecko_checkpoint_value(db_session, mock_coingecko_response):
    """Test checkpoint value generation."""
    ingestion = CoinGeckoIngestion(db_session)
    
    checkpoint = ingestion.get_checkpoint_value(mock_coingecko_response)
    
    assert checkpoint is not None
    assert isinstance(checkpoint, str)
