"""Cryptocurrency data API endpoints."""
import time
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from core.database import get_db, check_db_connection
from core.models import Coin, ETLCheckpoint, ETLRun
from api.auth import verify_api_key
from schemas.crypto import (
    CoinDataResponse, 
    CoinResponse, 
    PaginationMetadata, 
    HealthResponse,
    StatsResponse,
    SourceSummary,
    ETLRunStats,
    RunsListResponse,
    RunComparison,
    CompareRunsResponse
)

router = APIRouter(tags=["crypto"])


@router.get("/data", response_model=CoinDataResponse)
async def get_crypto_data(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (must be >= 1)"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page (1-100)"),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC, ETH)"),
    min_price: Optional[float] = Query(None, description="Minimum price filter (numeric value)"),
    max_price: Optional[float] = Query(None, description="Maximum price filter (numeric value)"),
    source: Optional[str] = Query(None, description="Filter by data source (coingecko, csv, rss_feed)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get cryptocurrency data with pagination and filtering.
    
    Returns data with request metadata including request_id and api_latency_ms.
    
    **Note:** The 422 Validation Error shown in the responses section is an example 
    of what would be returned if invalid parameters are provided (e.g., page=0, per_page=200).
    This endpoint will return 200 OK with valid parameters.
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


@router.get("/stats", response_model=StatsResponse)
async def get_etl_stats(
    request: Request,
    source: Optional[str] = Query(None, description="Filter by data source"),
    limit: int = Query(10, ge=1, le=100, description="Number of recent runs to return"),
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get ETL pipeline statistics and summaries.
    
    Returns:
    - Summary statistics per source (total runs, success/failure counts, avg duration)
    - Recent ETL run details
    - Last success and failure timestamps
    """
    start_time = time.time()
    
    # Build summary statistics per source
    summary_list = []
    
    # Get list of sources
    sources_query = select(ETLRun.source).distinct()
    if source:
        sources_query = sources_query.where(ETLRun.source == source)
    
    sources_result = await db.execute(sources_query)
    sources = [s[0] for s in sources_result.all()]
    
    for src in sources:
        # Total runs
        total_runs_query = select(func.count()).select_from(ETLRun).where(ETLRun.source == src)
        total_runs = (await db.execute(total_runs_query)).scalar_one()
        
        # Successful runs
        success_query = select(func.count()).select_from(ETLRun).where(
            ETLRun.source == src,
            ETLRun.status == 'success'
        )
        successful_runs = (await db.execute(success_query)).scalar_one()
        
        # Failed runs
        failed_runs = total_runs - successful_runs
        
        # Total records processed
        records_query = select(func.sum(ETLRun.records_processed)).where(
            ETLRun.source == src,
            ETLRun.status == 'success'
        )
        total_records = (await db.execute(records_query)).scalar_one() or 0
        
        # Last successful run
        last_success_query = select(ETLRun.completed_at).where(
            ETLRun.source == src,
            ETLRun.status == 'success'
        ).order_by(desc(ETLRun.completed_at)).limit(1)
        last_success_result = await db.execute(last_success_query)
        last_successful_run = last_success_result.scalar_one_or_none()
        
        # Last failed run
        last_failure_query = select(ETLRun.completed_at).where(
            ETLRun.source == src,
            ETLRun.status == 'failed'
        ).order_by(desc(ETLRun.completed_at)).limit(1)
        last_failure_result = await db.execute(last_failure_query)
        last_failed_run = last_failure_result.scalar_one_or_none()
        
        # Average duration
        avg_duration_query = select(func.avg(ETLRun.duration_seconds)).where(
            ETLRun.source == src,
            ETLRun.status == 'success',
            ETLRun.duration_seconds.isnot(None)
        )
        avg_duration = (await db.execute(avg_duration_query)).scalar_one()
        
        summary_list.append(SourceSummary(
            source=src,
            total_runs=total_runs,
            successful_runs=successful_runs,
            failed_runs=failed_runs,
            total_records_processed=total_records,
            last_successful_run=last_successful_run,
            last_failed_run=last_failed_run,
            average_duration_seconds=float(avg_duration) if avg_duration else None
        ))
    
    # Get recent runs
    recent_runs_query = select(ETLRun).order_by(desc(ETLRun.started_at)).limit(limit)
    if source:
        recent_runs_query = recent_runs_query.where(ETLRun.source == source)
    
    recent_runs_result = await db.execute(recent_runs_query)
    recent_runs = recent_runs_result.scalars().all()
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    return StatsResponse(
        request_id=request.state.request_id,
        api_latency_ms=round(latency_ms, 2),
        summary=summary_list,
        recent_runs=[ETLRunStats.model_validate(run) for run in recent_runs],
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/metrics", response_class=Response)
async def get_prometheus_metrics(db: AsyncSession = Depends(get_db)):
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus exposition format:
    - ETL run counts and durations
    - Data volume by source
    - Schema drift events
    - Failure rates
    """
    from core.prometheus import PrometheusMetrics
    
    metrics_generator = PrometheusMetrics(db)
    metrics_text = await metrics_generator.generate_prometheus_format()
    
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4"
    )


@router.get("/runs", response_model=RunsListResponse)
async def get_etl_runs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    source: Optional[str] = Query(None, description="Filter by source"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Number of runs per page"),
    page: int = Query(1, ge=1, description="Page number"),
    api_key: str = Depends(verify_api_key)
):
    """
    Get list of ETL runs with optional filtering.
    
    Query Parameters:
    - source: Filter by data source (e.g., "coingecko", "csv", "rss_feed")
    - status: Filter by run status ("success", "failed", "started")
    - limit: Maximum number of runs per page (1-500)
    - page: Page number (1-indexed)
    """
    # Build query
    query = select(ETLRun).order_by(desc(ETLRun.started_at))
    
    # Apply filters
    if source:
        query = query.where(ETLRun.source == source)
    if status:
        query = query.where(ETLRun.status == status)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar_one()
    
    # Apply pagination
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)
    
    # Execute
    result = await db.execute(query)
    runs = result.scalars().all()
    
    return RunsListResponse(
        request_id=request.state.request_id,
        runs=[ETLRunStats.model_validate(run) for run in runs],
        total_count=total_count,
        page=page,
        per_page=limit,
        timestamp=datetime.now(timezone.utc)
    )


@router.get("/compare-runs", response_model=CompareRunsResponse)
async def compare_runs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    run1_id: str = Query(..., description="First run ID"),
    run2_id: str = Query(..., description="Second run ID"),
    api_key: str = Depends(verify_api_key)
):
    """
    Compare two ETL runs and detect anomalies.
    
    Analyzes differences in:
    - Records processed
    - Duration
    - Status changes
    - Performance anomalies
    
    Query Parameters:
    - run1_id: UUID of first run
    - run2_id: UUID of second run
    """
    # Fetch both runs
    result = await db.execute(
        select(ETLRun).where(ETLRun.run_id.in_([run1_id, run2_id]))
    )
    runs = result.scalars().all()
    
    if len(runs) != 2:
        raise HTTPException(status_code=404, detail="One or both run IDs not found")
    
    # Order runs by started_at (older first)
    runs_sorted = sorted(runs, key=lambda r: r.started_at)
    run1, run2 = runs_sorted
    
    # Ensure same source
    if run1.source != run2.source:
        raise HTTPException(
            status_code=400,
            detail=f"Runs are from different sources: {run1.source} vs {run2.source}"
        )
    
    # Calculate differences
    records_diff = run2.records_processed - run1.records_processed
    
    duration_diff = None
    duration_change_percent = None
    if run1.duration_seconds and run2.duration_seconds:
        duration_diff = run2.duration_seconds - run1.duration_seconds
        if run1.duration_seconds > 0:
            duration_change_percent = float(
                (duration_diff / run1.duration_seconds) * 100
            )
    
    status_changed = run1.status != run2.status
    
    # Detect anomalies
    anomalies = []
    
    # Large record count change (>50%)
    if run1.records_processed > 0:
        change_pct = abs(records_diff / run1.records_processed) * 100
        if change_pct > 50:
            anomalies.append(
                f"Large record count change: {records_diff:+d} ({change_pct:+.1f}%)"
            )
    
    # Significant duration increase (>100%)
    if duration_change_percent and duration_change_percent > 100:
        anomalies.append(
            f"Duration doubled: {duration_change_percent:+.1f}% slower"
        )
    
    # Very fast duration (possible data issue)
    if run2.duration_seconds and run2.duration_seconds < 0.1:
        anomalies.append("Suspiciously fast run (<0.1s)")
    
    # Status change from success to failure
    if run1.status == "success" and run2.status == "failed":
        anomalies.append("Run status degraded from success to failure")
    
    # No records processed
    if run2.records_processed == 0 and run2.status == "success":
        anomalies.append("Success status but 0 records processed")
    
    comparison = RunComparison(
        run1_id=run1.run_id,
        run2_id=run2.run_id,
        source=run1.source,
        records_diff=records_diff,
        duration_diff_seconds=duration_diff,
        duration_change_percent=duration_change_percent,
        status_changed=status_changed,
        anomalies=anomalies
    )
    
    return CompareRunsResponse(
        request_id=request.state.request_id,
        comparison=comparison,
        run1=ETLRunStats.model_validate(run1),
        run2=ETLRunStats.model_validate(run2),
        timestamp=datetime.now(timezone.utc)
    )
