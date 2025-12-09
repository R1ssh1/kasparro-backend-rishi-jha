"""SQLAlchemy database models."""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, Index, UniqueConstraint, func, JSON
from core.database import Base


class RawCoinData(Base):
    """Raw JSON data from various sources before normalization."""
    
    __tablename__ = "raw_coin_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    external_id = Column(String(100), nullable=False)
    raw_json = Column(JSON, nullable=False)
    ingested_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        Index('ix_raw_coin_data_source_external_id', 'source', 'external_id'),
    )


class Coin(Base):
    """Normalized cryptocurrency data from all sources."""
    
    __tablename__ = "coins"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    external_id = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    name = Column(String(200))
    current_price = Column(Numeric(20, 8))
    market_cap = Column(Numeric(30, 2))
    volume_24h = Column(Numeric(30, 2))
    price_change_24h = Column(Numeric(10, 4))
    last_updated = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        UniqueConstraint('source', 'external_id', name='uq_source_external_id'),
        Index('ix_coins_symbol_last_updated', 'symbol', 'last_updated'),
    )


class ETLCheckpoint(Base):
    """Tracks last successful position for incremental ingestion."""
    
    __tablename__ = "etl_checkpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), unique=True, nullable=False)
    last_cursor = Column(String(200))  # page number, timestamp, or ID
    last_successful_run = Column(DateTime(timezone=True))
    records_processed = Column(Integer, default=0)
    status = Column(String(20))  # 'success', 'failed', 'running'
    error_message = Column(Text)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )


class ETLRun(Base):
    """Metadata for each ETL run for observability."""
    
    __tablename__ = "etl_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    source = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # 'started', 'success', 'failed'
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    duration_seconds = Column(Numeric(10, 2))
    error_message = Column(Text)
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    completed_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('ix_etl_runs_source_started_at', 'source', 'started_at'),
    )


class SchemaDriftLog(Base):
    """Logs detected schema drift events."""
    
    __tablename__ = "schema_drift_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    run_id = Column(String(36), index=True)
    schema_name = Column(String(100), nullable=False)
    confidence_score = Column(Numeric(5, 3))  # 0.000 to 1.000
    missing_fields = Column(JSON)  # List of missing field names
    extra_fields = Column(JSON)  # List of unexpected field names
    fuzzy_matches = Column(JSON)  # Dict of possible field renames
    warnings = Column(JSON)  # List of warning messages
    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    __table_args__ = (
        Index('ix_schema_drift_source_detected', 'source', 'detected_at'),
    )
