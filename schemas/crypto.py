"""Schemas for cryptocurrency data API."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class CoinResponse(BaseModel):
    """Response schema for a single coin."""
    
    id: int
    source: str
    external_id: str
    symbol: str
    name: Optional[str] = None
    current_price: Optional[Decimal] = None
    market_cap: Optional[Decimal] = None
    volume_24h: Optional[Decimal] = None
    price_change_24h: Optional[Decimal] = None
    last_updated: datetime
    
    class Config:
        from_attributes = True


class PaginationMetadata(BaseModel):
    """Pagination metadata."""
    
    page: int
    per_page: int
    total_items: int
    total_pages: int


class CoinDataResponse(BaseModel):
    """Response for /data endpoint with pagination."""
    
    request_id: str
    api_latency_ms: float
    data: List[CoinResponse]
    pagination: PaginationMetadata


class HealthResponse(BaseModel):
    """Response for /health endpoint."""
    
    status: str
    database_connected: bool
    etl_status: Optional[dict] = None
    timestamp: datetime
