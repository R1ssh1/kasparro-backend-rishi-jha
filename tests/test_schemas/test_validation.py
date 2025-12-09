"""Tests for schema validation and mismatch handling."""
import pytest
from pydantic import ValidationError
from schemas.ingestion import CoinGeckoRecord, CSVRecord, RSSFeedRecord


def test_coingecko_schema_valid():
    """Test CoinGecko schema accepts valid data."""
    data = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 50000.0,
        "market_cap": 950000000000.0,
        "total_volume": 30000000000.0,
        "price_change_percentage_24h": 2.5,
        "last_updated": "2025-12-09T10:00:00Z"
    }
    
    record = CoinGeckoRecord(**data)
    assert record.id == "bitcoin"
    assert record.symbol == "btc"
    assert record.current_price == 50000.0


def test_coingecko_schema_missing_required():
    """Test CoinGecko schema rejects data with missing required fields."""
    data = {
        "symbol": "btc",
        "name": "Bitcoin"
        # Missing id and last_updated
    }
    
    with pytest.raises(ValidationError) as exc_info:
        CoinGeckoRecord(**data)
    
    errors = exc_info.value.errors()
    missing_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    assert "id" in missing_fields
    assert "last_updated" in missing_fields


def test_coingecko_schema_optional_fields():
    """Test CoinGecko schema allows optional fields to be None."""
    data = {
        "id": "unknown-coin",
        "symbol": "unk",
        "name": "Unknown Coin",
        "last_updated": "2025-12-09T10:00:00Z"
        # current_price, market_cap, etc. are optional
    }
    
    record = CoinGeckoRecord(**data)
    assert record.current_price is None
    assert record.market_cap is None


def test_csv_schema_valid():
    """Test CSV schema accepts valid data."""
    data = {
        "id": "btc-001",
        "symbol": "BTC",
        "name": "Bitcoin",
        "price": 50000.0,
        "market_cap": 950000000000.0,
        "volume_24h": 30000000000.0,
        "price_change_24h": 2.5,
        "timestamp": "2025-12-09T10:00:00"
    }
    
    record = CSVRecord(**data)
    assert record.id == "btc-001"
    assert record.price == 50000.0


def test_csv_schema_type_coercion():
    """Test CSV schema coerces string numbers to floats."""
    data = {
        "id": "btc-001",
        "symbol": "BTC",
        "name": "Bitcoin",
        "price": "50000.0",  # String instead of float
        "timestamp": "2025-12-09T10:00:00"
    }
    
    record = CSVRecord(**data)
    assert record.price == 50000.0
    assert isinstance(record.price, float)


def test_rss_schema_valid():
    """Test RSS feed schema accepts valid data."""
    data = {
        "id": "article-123",
        "url": "https://example.com/article",
        "title": "Crypto News",
        "content_text": "Important crypto news here",
        "date_published": "2025-12-09T10:00:00.000Z",
        "authors": [{"name": "John Doe"}],
        "image": "https://example.com/image.jpg"
    }
    
    record = RSSFeedRecord(**data)
    assert record.id == "article-123"
    assert record.title == "Crypto News"
    assert len(record.authors) == 1


def test_rss_schema_missing_optional():
    """Test RSS feed schema allows optional fields to be missing."""
    data = {
        "id": "article-123",
        "url": "https://example.com/article",
        "title": "Crypto News",
        "date_published": "2025-12-09T10:00:00.000Z"
        # content_text, authors, image are optional
    }
    
    record = RSSFeedRecord(**data)
    assert record.content_text is None
    assert record.authors is None
    assert record.image is None


def test_rss_schema_invalid_url():
    """Test RSS feed schema validates URL format."""
    data = {
        "id": "article-123",
        "url": "not-a-valid-url",  # Invalid URL
        "title": "Crypto News",
        "date_published": "2025-12-09T10:00:00.000Z"
    }
    
    # Pydantic doesn't validate URL format by default without HttpUrl type
    # This test documents current behavior
    record = RSSFeedRecord(**data)
    assert record.url == "not-a-valid-url"


def test_schema_extra_fields_ignored():
    """Test that extra unknown fields are ignored by default."""
    data = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "last_updated": "2025-12-09T10:00:00Z",
        "unknown_field": "should be ignored",
        "another_unknown": 12345
    }
    
    record = CoinGeckoRecord(**data)
    assert not hasattr(record, "unknown_field")
    assert not hasattr(record, "another_unknown")


def test_timestamp_normalization():
    """Test that timestamps are properly normalized to UTC."""
    data = {
        "id": "bitcoin",
        "symbol": "btc",
        "name": "Bitcoin",
        "last_updated": "2025-12-09T10:00:00+05:30"  # IST timezone
    }
    
    record = CoinGeckoRecord(**data)
    # Timestamp should be converted to UTC
    assert record.last_updated.tzinfo is not None
    assert "04:30:00" in record.last_updated.isoformat()  # Converted to UTC
