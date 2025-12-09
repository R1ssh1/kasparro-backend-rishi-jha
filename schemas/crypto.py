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


class ETLRunStats(BaseModel):
    """Statistics for a single ETL run."""
    
    run_id: str
    source: str
    status: str
    records_processed: int
    records_failed: int
    duration_seconds: Optional[Decimal] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class SourceSummary(BaseModel):
    """Summary statistics for a data source."""
    
    source: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    total_records_processed: int
    last_successful_run: Optional[datetime] = None
    last_failed_run: Optional[datetime] = None
    average_duration_seconds: Optional[float] = None


class StatsResponse(BaseModel):
    """Response for /stats endpoint."""
    
    request_id: str
    api_latency_ms: float
    summary: List[SourceSummary]
    recent_runs: List[ETLRunStats]
    timestamp: datetime


class RunsListResponse(BaseModel):
    """Response for /runs endpoint."""
    
    request_id: str
    runs: List[ETLRunStats]
    total_count: int
    page: int
    per_page: int
    timestamp: datetime


class RunComparison(BaseModel):
    """Comparison between two ETL runs."""
    
    run1_id: str
    run2_id: str
    source: str
    records_diff: int
    duration_diff_seconds: Optional[Decimal] = None
    duration_change_percent: Optional[float] = None
    status_changed: bool
    anomalies: List[str] = []


class CompareRunsResponse(BaseModel):
    """Response for /compare-runs endpoint."""
    
    request_id: str
    comparison: RunComparison
    run1: ETLRunStats
    run2: ETLRunStats
    timestamp: datetime
