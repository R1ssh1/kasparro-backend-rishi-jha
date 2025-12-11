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


class MasterEntity(Base):
    """Master entity table to link cryptocurrency records across different sources.
    
    This provides a canonical view of cryptocurrencies by linking records from
    different data sources (CoinGecko, CSV, RSS) that represent the same asset.
    """
    
    __tablename__ = "master_entities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_symbol = Column(String(20), nullable=False, unique=True, index=True)
    canonical_name = Column(String(200), nullable=False)
    entity_type = Column(String(50), default="cryptocurrency")  # Future: tokens, stablecoins, etc.
    
    # Primary source - the "golden source" for this entity
    primary_source = Column(String(50), nullable=False)
    primary_coin_id = Column(Integer, nullable=True)  # FK to Coin table
    
    # Metadata
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
        Index('ix_master_entities_symbol_name', 'canonical_symbol', 'canonical_name'),
    )


class EntityMapping(Base):
    """Maps individual coin records to their master entity.
    
    This table creates the many-to-one relationship between source-specific
    coin records and their canonical master entity.
    """
    
    __tablename__ = "entity_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    master_entity_id = Column(Integer, nullable=False, index=True)
    coin_id = Column(Integer, nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    confidence = Column(Numeric(5, 3), default=1.0)  # Matching confidence (0.0-1.0)
    is_primary = Column(Integer, default=0)  # 1 if this is the primary source record
    
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    __table_args__ = (
        UniqueConstraint('coin_id', name='uq_coin_id'),  # Each coin can map to only one master entity
        Index('ix_entity_mappings_master_entity', 'master_entity_id'),
        Index('ix_entity_mappings_source', 'source', 'master_entity_id'),
    )

