"""
Prometheus Metrics Module

Provides /metrics endpoint in Prometheus exposition format.
Tracks ETL performance, API usage, and system health.
"""
import structlog
from typing import Dict, List
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.models import ETLRun, Coin, SchemaDriftLog

logger = structlog.get_logger()


class PrometheusMetrics:
    """Generate Prometheus metrics from database."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logger.bind(component="metrics")
    
    async def get_etl_metrics(self) -> List[str]:
        """Get ETL-related metrics."""
        metrics = []
        
        # Total ETL runs by source and status
        result = await self.session.execute(
            select(
                ETLRun.source,
                ETLRun.status,
                func.count(ETLRun.id).label('count')
            ).group_by(ETLRun.source, ETLRun.status)
        )
        
        for row in result:
            metrics.append(
                f'etl_runs_total{{source="{row.source}",status="{row.status}"}} {row.count}'
            )
        
        # Total records processed by source
        result = await self.session.execute(
            select(
                ETLRun.source,
                func.sum(ETLRun.records_processed).label('total')
            ).where(
                ETLRun.status == "success"
            ).group_by(ETLRun.source)
        )
        
        for row in result:
            total = row.total or 0
            metrics.append(
                f'etl_records_processed_total{{source="{row.source}"}} {total}'
            )
        
        # Average duration by source
        result = await self.session.execute(
            select(
                ETLRun.source,
                func.avg(ETLRun.duration_seconds).label('avg_duration')
            ).where(
                ETLRun.status == "success",
                ETLRun.duration_seconds.isnot(None)
            ).group_by(ETLRun.source)
        )
        
        for row in result:
            avg = float(row.avg_duration) if row.avg_duration else 0.0
            metrics.append(
                f'etl_duration_seconds_avg{{source="{row.source}"}} {avg:.2f}'
            )
        
        # Last run timestamp by source
        result = await self.session.execute(
            select(
                ETLRun.source,
                func.max(ETLRun.started_at).label('last_run')
            ).group_by(ETLRun.source)
        )
        
        for row in result:
            if row.last_run:
                timestamp = int(row.last_run.timestamp())
                metrics.append(
                    f'etl_last_run_timestamp{{source="{row.source}"}} {timestamp}'
                )
        
        # Recent failures (last 24h)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.session.execute(
            select(
                ETLRun.source,
                func.count(ETLRun.id).label('count')
            ).where(
                ETLRun.status == "failed",
                ETLRun.started_at >= since
            ).group_by(ETLRun.source)
        )
        
        for row in result:
            metrics.append(
                f'etl_failures_24h{{source="{row.source}"}} {row.count}'
            )
        
        return metrics
    
    async def get_data_metrics(self) -> List[str]:
        """Get data volume metrics."""
        metrics = []
        
        # Total coins by source
        result = await self.session.execute(
            select(
                Coin.source,
                func.count(Coin.id).label('count')
            ).group_by(Coin.source)
        )
        
        for row in result:
            metrics.append(
                f'crypto_coins_total{{source="{row.source}"}} {row.count}'
            )
        
        # Total market cap by source (where available)
        result = await self.session.execute(
            select(
                Coin.source,
                func.sum(Coin.market_cap).label('total_market_cap')
            ).where(
                Coin.market_cap.isnot(None)
            ).group_by(Coin.source)
        )
        
        for row in result:
            total = float(row.total_market_cap) if row.total_market_cap else 0.0
            metrics.append(
                f'crypto_total_market_cap{{source="{row.source}"}} {total:.0f}'
            )
        
        return metrics
    
    async def get_drift_metrics(self) -> List[str]:
        """Get schema drift metrics."""
        metrics = []
        
        # Total drift events by source
        result = await self.session.execute(
            select(
                SchemaDriftLog.source,
                func.count(SchemaDriftLog.id).label('count')
            ).group_by(SchemaDriftLog.source)
        )
        
        for row in result:
            metrics.append(
                f'schema_drift_events_total{{source="{row.source}"}} {row.count}'
            )
        
        # Average confidence score by source
        result = await self.session.execute(
            select(
                SchemaDriftLog.source,
                func.avg(SchemaDriftLog.confidence_score).label('avg_confidence')
            ).group_by(SchemaDriftLog.source)
        )
        
        for row in result:
            avg = float(row.avg_confidence) if row.avg_confidence else 0.0
            metrics.append(
                f'schema_drift_confidence_avg{{source="{row.source}"}} {avg:.3f}'
            )
        
        # Recent drift events (last 24h)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.session.execute(
            select(
                SchemaDriftLog.source,
                func.count(SchemaDriftLog.id).label('count')
            ).where(
                SchemaDriftLog.detected_at >= since
            ).group_by(SchemaDriftLog.source)
        )
        
        for row in result:
            metrics.append(
                f'schema_drift_events_24h{{source="{row.source}"}} {row.count}'
            )
        
        return metrics
    
    async def generate_prometheus_format(self) -> str:
        """
        Generate complete Prometheus metrics in exposition format.
        
        Returns:
            Metrics in Prometheus text format
        """
        all_metrics = []
        
        # Header
        all_metrics.append("# HELP etl_runs_total Total number of ETL runs by source and status")
        all_metrics.append("# TYPE etl_runs_total counter")
        all_metrics.extend(await self.get_etl_metrics())
        
        all_metrics.append("")
        all_metrics.append("# HELP crypto_coins_total Total number of cryptocurrency records by source")
        all_metrics.append("# TYPE crypto_coins_total gauge")
        all_metrics.extend(await self.get_data_metrics())
        
        all_metrics.append("")
        all_metrics.append("# HELP schema_drift_events_total Total schema drift events detected")
        all_metrics.append("# TYPE schema_drift_events_total counter")
        all_metrics.extend(await self.get_drift_metrics())
        
        return "\n".join(all_metrics) + "\n"
