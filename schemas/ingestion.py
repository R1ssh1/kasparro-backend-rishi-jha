"""Schemas for ingestion data validation."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator


class CoinGeckoRecord(BaseModel):
    """Validation schema for CoinGecko API response."""
    
    id: str
    symbol: str
    name: str
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    total_volume: Optional[float] = None
    price_change_percentage_24h: Optional[float] = None
    last_updated: str
    
    @field_validator('last_updated')
    @classmethod
    def normalize_timezone(cls, v: str) -> datetime:
        """Parse and normalize timestamp to UTC."""
        from dateutil import parser
        dt = parser.parse(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


class CSVRecord(BaseModel):
    """Validation schema for CSV data."""
    
    id: str
    symbol: str
    name: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    timestamp: str
    
    @field_validator('timestamp')
    @classmethod
    def normalize_timezone(cls, v: str) -> datetime:
        """Parse and normalize timestamp to UTC."""
        from dateutil import parser
        dt = parser.parse(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)


class NormalizedCoin(BaseModel):
    """Normalized schema for all data sources."""
    
    source: str
    external_id: str
    symbol: str
    name: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None
    last_updated: datetime


class RSSFeedAuthor(BaseModel):
    """RSS feed author model."""
    name: str


class RSSFeedRecord(BaseModel):
    """Validation schema for RSS feed JSON items."""
    
    id: str
    url: str
    title: str
    content_text: Optional[str] = None
    content_html: Optional[str] = None
    date_published: str
    authors: Optional[List[RSSFeedAuthor]] = None
    image: Optional[str] = None
    
    @field_validator('date_published')
    @classmethod
    def normalize_timezone(cls, v: str) -> str:
        """Validate ISO8601 timestamp - keep as string for now."""
        # Pydantic will handle validation, we'll parse in normalize_record
        return v

