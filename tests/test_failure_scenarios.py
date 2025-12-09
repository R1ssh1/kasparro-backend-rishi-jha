"""Tests for failure scenarios and error handling."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from sqlalchemy.exc import OperationalError
from ingestion.coingecko import CoinGeckoIngestion


@pytest.mark.asyncio
async def test_database_connection_failure(db_session):
    """Test handling of database connection failures."""
    ingestion = CoinGeckoIngestion(db_session)
    
    with patch.object(db_session, 'execute', side_effect=OperationalError("DB Error", None, None)):
        with pytest.raises(OperationalError):
            await ingestion.create_run_record()


@pytest.mark.asyncio
async def test_api_request_retry_on_failure(db_session):
    """Test retry mechanism for API failures."""
    ingestion = CoinGeckoIngestion(db_session)
    
    # Mock httpx client to fail twice, then succeed
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    
    call_count = 0
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.HTTPError("Network error")
        return mock_response
    
    with patch('httpx.AsyncClient.get', side_effect=mock_get):
        # Should retry and eventually succeed
        records = await ingestion.fetch_data()
        assert call_count >= 3


@pytest.mark.asyncio
async def test_invalid_data_handling(db_session):
    """Test handling of invalid/malformed data."""
    ingestion = CoinGeckoIngestion(db_session)
    
    invalid_record = {
        "id": "test",
        "symbol": None,  # Invalid
        "name": "Test",
    }
    
    # Should return None for invalid records
    normalized = ingestion.normalize_record(invalid_record)
    assert normalized is None
