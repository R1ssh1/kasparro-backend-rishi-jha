"""Base class for all ingestion sources."""
import uuid
import structlog
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.models import RawCoinData, Coin, ETLCheckpoint, ETLRun
from core.config import settings
from schemas.ingestion import NormalizedCoin
from ingestion.rate_limiter import rate_limiter_registry
from core.schema_drift import SchemaDriftDetector
from core.failure_injector import failure_injector, FailureType

logger = structlog.get_logger()


class BaseIngestion(ABC):
    """Base class for all data ingestion sources."""
    
    def __init__(self, source_name: str, session: AsyncSession):
        """
        Initialize ingestion source.
        
        Args:
            source_name: Unique identifier for this data source
            session: Database session
        """
        self.source_name = source_name
        self.session = session
        self.run_id = str(uuid.uuid4())
        self.logger = logger.bind(run_id=self.run_id, source=source_name)
        self.drift_detector = SchemaDriftDetector(source_name, session)
        
        # Configure failure injector from settings
        if settings.enable_failure_injection:
            failure_injector.enabled = True
            failure_injector.configure(
                probability=settings.failure_probability,
                failure_type=FailureType.DATABASE_ERROR,
                fail_at_record=settings.fail_at_record
            )
            self.logger.warning(
                "Failure injection enabled",
                probability=settings.failure_probability,
                fail_at_record=settings.fail_at_record
            )
    
    def get_expected_schema(self) -> Optional[Set[str]]:
        """
        Get expected field names for this source's schema.
        Override in subclasses to enable drift detection.
        
        Returns:
            Set of expected field names or None
        """
        return None
    
    @abstractmethod
    async def fetch_data(self, checkpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch raw data from the source.
        
        Args:
            checkpoint: Last cursor position for incremental fetch
            
        Returns:
            List of raw data records
        """
        pass
    
    @abstractmethod
    def normalize_record(self, raw_data: Dict[str, Any]) -> Optional[NormalizedCoin]:
        """
        Normalize a raw record to the unified schema.
        
        Args:
            raw_data: Raw data record
            
        Returns:
            Normalized coin record or None if validation fails
        """
        pass
    
    @abstractmethod
    def get_checkpoint_value(self, records: List[Dict[str, Any]]) -> Optional[str]:
        """
        Extract checkpoint value from processed records.
        
        Args:
            records: List of processed records
            
        Returns:
            Checkpoint value for next incremental run
        """
        pass
    
    async def save_raw_data(self, records: List[Dict[str, Any]]) -> None:
        """Save raw JSON data to database."""
        if not records:
            return
        
        raw_records = [
            {
                "source": self.source_name,
                "external_id": record.get("id", "unknown"),
                "raw_json": record,
            }
            for record in records
        ]
        
        await self.session.execute(
            insert(RawCoinData),
            raw_records
        )
        self.logger.info(f"Saved {len(raw_records)} raw records")
    
    async def upsert_normalized_data(self, normalized_records: List[NormalizedCoin]) -> int:
        """
        Upsert normalized data with conflict resolution.
        
        Returns:
            Number of records processed
        """
        if not normalized_records:
            return 0
        
        values = [record.model_dump() for record in normalized_records]
        
        stmt = pg_insert(Coin).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint='uq_source_external_id',
            set_={
                'symbol': stmt.excluded.symbol,
                'name': stmt.excluded.name,
                'current_price': stmt.excluded.current_price,
                'market_cap': stmt.excluded.market_cap,
                'volume_24h': stmt.excluded.volume_24h,
                'price_change_24h': stmt.excluded.price_change_24h,
                'last_updated': stmt.excluded.last_updated,
                'updated_at': datetime.now(timezone.utc),
            }
        )
        
        await self.session.execute(stmt)
        self.logger.info(f"Upserted {len(normalized_records)} normalized records")
        
        return len(normalized_records)
    
    async def update_checkpoint(self, checkpoint_value: Optional[str], status: str, error_msg: Optional[str] = None) -> None:
        """Update checkpoint after successful batch processing."""
        stmt = pg_insert(ETLCheckpoint).values(
            source=self.source_name,
            last_cursor=checkpoint_value,
            last_successful_run=datetime.now(timezone.utc) if status == "success" else None,
            status=status,
            error_message=error_msg,
        )
        
        stmt = stmt.on_conflict_do_update(
            constraint='etl_checkpoints_source_key',
            set_={
                'last_cursor': stmt.excluded.last_cursor,
                'last_successful_run': stmt.excluded.last_successful_run,
                'status': stmt.excluded.status,
                'error_message': stmt.excluded.error_message,
                'updated_at': datetime.now(timezone.utc),
            }
        )
        
        await self.session.execute(stmt)
        self.logger.info(f"Updated checkpoint: {checkpoint_value}")
    
    async def get_checkpoint(self) -> Optional[str]:
        """Retrieve last checkpoint for this source."""
        result = await self.session.execute(
            select(ETLCheckpoint.last_cursor)
            .where(ETLCheckpoint.source == self.source_name)
        )
        row = result.first()
        return row[0] if row else None
    
    async def create_run_record(self) -> None:
        """Create ETL run record at start."""
        await self.session.execute(
            insert(ETLRun).values(
                run_id=self.run_id,
                source=self.source_name,
                status="started",
                started_at=datetime.now(timezone.utc),
            )
        )
        await self.session.commit()
        self.logger.info("Created ETL run record")
    
    async def update_run_record(self, status: str, records_processed: int, error_msg: Optional[str] = None) -> None:
        """Update ETL run record at completion."""
        from sqlalchemy import update
        
        completed_at = datetime.now(timezone.utc)
        
        # Get start time
        result = await self.session.execute(
            select(ETLRun.started_at)
            .where(ETLRun.run_id == self.run_id)
        )
        started_at = result.scalar_one()
        duration = (completed_at - started_at).total_seconds()
        
        await self.session.execute(
            update(ETLRun)
            .where(ETLRun.run_id == self.run_id)
            .values(
                status=status,
                records_processed=records_processed,
                duration_seconds=duration,
                completed_at=completed_at,
                error_message=error_msg,
            )
        )
        await self.session.commit()
        self.logger.info(f"Updated ETL run: {status}, {records_processed} records, {duration:.2f}s")
    
    async def process_batch_with_transaction(
        self,
        raw_records: List[Dict[str, Any]],
        checkpoint_value: Optional[str]
    ) -> int:
        """
        Process a batch atomically: save raw + normalize + upsert + update checkpoint.
        
        Returns:
            Number of records processed
        """
        # Schema drift detection (if schema defined)
        expected_schema = self.get_expected_schema()
        if expected_schema and raw_records:
            schema_name = f"{self.source_name}_schema"
            self.drift_detector.register_schema(schema_name, expected_schema)
            
            # Analyze batch for drift
            drift_report = await self.drift_detector.analyze_batch(
                schema_name=schema_name,
                records=raw_records,
                run_id=self.run_id,
                sample_size=10
            )
            
            if drift_report.get("drift_detected"):
                self.logger.warning(
                    "Schema drift detected during ingestion",
                    drift_ratio=drift_report.get("drift_ratio"),
                    warnings=drift_report.get("warnings")
                )
        
        # Save raw data
        await self.save_raw_data(raw_records)
        
        # Inject failure BEFORE normalization (mid-run failure)
        if len(raw_records) > 0:
            mid_point = len(raw_records) // 2
            failure_injector.inject_if_enabled(
                record_index=mid_point,
                message=f"Injected failure during {self.source_name} ingestion at record {mid_point}"
            )
        
        # Normalize and validate
        normalized_records = []
        for idx, raw in enumerate(raw_records, start=1):
            normalized = self.normalize_record(raw)
            if normalized:
                normalized_records.append(normalized)
            else:
                self.logger.warning(f"Failed to normalize record: {raw.get('id')}")
        
        # Upsert normalized data
        count = await self.upsert_normalized_data(normalized_records)
        
        # Update checkpoint (same transaction)
        await self.update_checkpoint(checkpoint_value, "success")
        
        await self.session.commit()
        
        return count
    
    async def run(self) -> None:
        """Execute the full ETL pipeline with error handling."""
        self.logger.info("Starting ETL run")
        
        try:
            # Create run record
            await self.create_run_record()
            
            # Get last checkpoint
            checkpoint = await self.get_checkpoint()
            self.logger.info(f"Starting from checkpoint: {checkpoint}")
            
            # Fetch data
            raw_records = await self.fetch_data(checkpoint)
            self.logger.info(f"Fetched {len(raw_records)} records")
            
            if not raw_records:
                self.logger.info("No new records to process")
                await self.update_run_record("success", 0)
                return
            
            # Get new checkpoint value
            new_checkpoint = self.get_checkpoint_value(raw_records)
            
            # Process batch with transaction
            count = await self.process_batch_with_transaction(raw_records, new_checkpoint)
            
            # Update run record
            await self.update_run_record("success", count)
            
            self.logger.info(f"ETL run completed successfully: {count} records")
            
        except Exception as e:
            self.logger.error(f"ETL run failed: {str(e)}", exc_info=True)
            await self.update_checkpoint(None, "failed", str(e))
            await self.update_run_record("failed", 0, str(e))
            raise
