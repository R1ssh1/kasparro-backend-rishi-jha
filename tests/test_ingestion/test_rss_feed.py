"""Tests for RSS feed ingestion."""
import pytest
from datetime import datetime, timezone
from ingestion.rss_feed import RSSFeedIngestion
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_rss_normalize_record(db_session):
    """Test RSS feed record normalization to Coin model."""
    rss = RSSFeedIngestion(db_session)
    
    raw_data = {
        "id": "test-article-123",
        "url": "https://example.com/article",
        "title": "Bitcoin Surges to New Heights",
        "content_text": "Bitcoin has reached an all-time high...",
        "date_published": "2025-12-09T10:00:00.000Z",
        "authors": [{"name": "John Doe"}],
        "image": "https://example.com/image.jpg"
    }
    
    coin = rss.normalize_record(raw_data)

    assert coin.symbol == "NEWS"
    assert coin.external_id == "test-article-123"
    assert coin.name == "Bitcoin Surges to New Heights"
    assert coin.current_price == 0.0  # News articles have no price
    assert coin.market_cap == 0.0
    # NormalizedCoin is a Pydantic model - just verify key fields exist
    # The actual metadata is stored in the database after insert
    assert hasattr(coin, 'symbol')
    assert hasattr(coin, 'external_id')
    assert hasattr(coin, 'name')
@pytest.mark.asyncio
async def test_rss_checkpoint_value(db_session):
    """Test RSS feed checkpoint value extraction."""
    rss = RSSFeedIngestion(db_session)
    
    # Create mock raw records (newest first, as returned by RSS feed)
    records = [
        {
            "id": "article-newest",
            "url": "https://example.com/newest",
            "title": "Newest Article",
            "content_text": "Content",
            "date_published": "2025-12-09T12:00:00.000Z"
        },
        {
            "id": "article-middle",
            "url": "https://example.com/middle",
            "title": "Middle Article",
            "content_text": "Content",
            "date_published": "2025-12-09T11:00:00.000Z"
        },
        {
            "id": "article-oldest",
            "url": "https://example.com/oldest",
            "title": "Oldest Article",
            "content_text": "Content",
            "date_published": "2025-12-09T10:00:00.000Z"
        }
    ]
    
    checkpoint = rss.get_checkpoint_value(records)
    
    # Checkpoint should be the ID of the newest article (first in list)
    assert checkpoint == "article-newest"


@pytest.mark.asyncio
async def test_rss_normalize_invalid_record(db_session):
    """Test RSS feed validation rejects invalid data."""
    rss = RSSFeedIngestion(db_session)
    
    # Missing required fields
    invalid_data = {
        "url": "https://example.com/article"
        # Missing id, title, date_published
    }
    
    # normalize_record returns None on validation error (logs error)
    result = rss.normalize_record(invalid_data)
    assert result is None


@pytest.mark.asyncio
async def test_rss_title_truncation(db_session):
    """Test that very long titles are truncated to fit database column."""
    rss = RSSFeedIngestion(db_session)
    
    long_title = "A" * 200  # Longer than 100 char limit
    
    raw_data = {
        "id": "test-long-title",
        "url": "https://example.com/article",
        "title": long_title,
        "content_text": "Content here",
        "date_published": "2025-12-09T10:00:00.000Z"
    }
    
    coin = rss.normalize_record(raw_data)
    
    # Name should be truncated to 100 chars
    assert len(coin.name) == 100
    assert coin.name == "A" * 100
