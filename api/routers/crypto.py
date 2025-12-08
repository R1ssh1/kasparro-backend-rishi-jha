"""Cryptocurrency data API endpoints."""
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from core.database import get_db, check_db_connection
from core.models import Coin, ETLCheckpoint
from schemas.crypto import CoinDataResponse, CoinResponse, PaginationMetadata, HealthResponse

router = APIRouter(tags=["crypto"])


@router.get("/data", response_model=CoinDataResponse)
async def get_crypto_data(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    source: Optional[str] = Query(None, description="Filter by data source"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cryptocurrency data with pagination and filtering.
    
    Returns data with request metadata including request_id and api_latency_ms.
    """
    start_time = time.time()
    
    # Build query
    query = select(Coin)
    
    # Apply filters
    if symbol:
        query = query.where(Coin.symbol == symbol.upper())
    
    if min_price is not None:
        query = query.where(Coin.current_price >= min_price)
    
    if max_price is not None:
        query = query.where(Coin.current_price <= max_price)
    
    if source:
        query = query.where(Coin.source == source)
    
    # Order by last_updated descending
    query = query.order_by(desc(Coin.last_updated))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_items = total_result.scalar_one()
    
    # Calculate pagination
    total_pages = (total_items + per_page - 1) // per_page
    offset = (page - 1) * per_page
    
    # Apply pagination
    query = query.limit(per_page).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    coins = result.scalars().all()
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    return CoinDataResponse(
        request_id=request.state.request_id,
        api_latency_ms=round(latency_ms, 2),
        data=[CoinResponse.model_validate(coin) for coin in coins],
        pagination=PaginationMetadata(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages
        )
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint.
    
    Reports:
    - Database connectivity
    - ETL last-run status for each source
    """
    # Check database connection
    db_connected = await check_db_connection()
    
    # Get ETL status for all sources
    etl_status = {}
    try:
        result = await db.execute(
            select(ETLCheckpoint)
        )
        checkpoints = result.scalars().all()
        
        for checkpoint in checkpoints:
            etl_status[checkpoint.source] = {
                "status": checkpoint.status,
                "last_successful_run": checkpoint.last_successful_run.isoformat() if checkpoint.last_successful_run else None,
                "last_cursor": checkpoint.last_cursor,
                "records_processed": checkpoint.records_processed,
                "updated_at": checkpoint.updated_at.isoformat() if checkpoint.updated_at else None
            }
    except Exception as e:
        etl_status = {"error": str(e)}
    
    # Determine overall status
    status = "healthy" if db_connected else "unhealthy"
    
    return HealthResponse(
        status=status,
        database_connected=db_connected,
        etl_status=etl_status,
        timestamp=datetime.now(timezone.utc)
    )
