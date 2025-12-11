"""Utilities for managing master entity normalization.

This module provides functions to create and manage master entities,
linking cryptocurrency records across different data sources.
"""
from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Coin, MasterEntity, EntityMapping

logger = structlog.get_logger(__name__)


# Known symbol mappings for common cryptocurrencies
KNOWN_SYMBOLS = {
    "BTC": {"name": "Bitcoin", "variants": ["bitcoin", "btc"]},
    "ETH": {"name": "Ethereum", "variants": ["ethereum", "eth"]},
    "BNB": {"name": "Binance Coin", "variants": ["binance coin", "bnb", "binance"]},
    "XRP": {"name": "XRP", "variants": ["xrp", "ripple"]},
    "ADA": {"name": "Cardano", "variants": ["cardano", "ada"]},
    "SOL": {"name": "Solana", "variants": ["solana", "sol"]},
    "DOGE": {"name": "Dogecoin", "variants": ["dogecoin", "doge"]},
    "DOT": {"name": "Polkadot", "variants": ["polkadot", "dot"]},
    "MATIC": {"name": "Polygon", "variants": ["polygon", "matic"]},
    "AVAX": {"name": "Avalanche", "variants": ["avalanche", "avax"]},
}


async def find_or_create_master_entity(
    session: AsyncSession,
    coin: Coin,
    confidence: float = 1.0
) -> Optional[int]:
    """Find or create a master entity for a given coin record.
    
    Args:
        session: Database session
        coin: Coin record to find or create master entity for
        confidence: Matching confidence score (0.0-1.0)
        
    Returns:
        master_entity_id if found or created, None if failed
    """
    try:
        # Normalize symbol for matching
        normalized_symbol = coin.symbol.upper().strip()
        normalized_name = coin.name.lower().strip() if coin.name else ""
        
        # Try to find existing master entity by symbol
        result = await session.execute(
            select(MasterEntity).where(MasterEntity.canonical_symbol == normalized_symbol)
        )
        master_entity = result.scalar_one_or_none()
        
        if master_entity:
            logger.info(
                "found_existing_master_entity",
                symbol=normalized_symbol,
                master_entity_id=master_entity.id,
                source=coin.source
            )
            return master_entity.id
        
        # Check if we know this symbol
        canonical_name = coin.name
        if normalized_symbol in KNOWN_SYMBOLS:
            canonical_name = KNOWN_SYMBOLS[normalized_symbol]["name"]
            logger.info(
                "using_known_symbol_mapping",
                symbol=normalized_symbol,
                canonical_name=canonical_name
            )
        
        # Create new master entity
        new_master = MasterEntity(
            canonical_symbol=normalized_symbol,
            canonical_name=canonical_name or normalized_symbol,
            entity_type="cryptocurrency",
            primary_source=coin.source,
            primary_coin_id=coin.id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        session.add(new_master)
        await session.flush()  # Get the ID without committing
        
        logger.info(
            "created_master_entity",
            master_entity_id=new_master.id,
            symbol=normalized_symbol,
            name=canonical_name,
            source=coin.source
        )
        
        return new_master.id
        
    except Exception as e:
        logger.error(
            "error_finding_or_creating_master_entity",
            error=str(e),
            coin_id=coin.id,
            symbol=coin.symbol
        )
        return None


async def link_coin_to_master_entity(
    session: AsyncSession,
    coin_id: int,
    master_entity_id: int,
    source: str,
    confidence: float = 1.0,
    is_primary: bool = False
) -> bool:
    """Link a coin record to its master entity.
    
    Args:
        session: Database session
        coin_id: ID of the coin record
        master_entity_id: ID of the master entity
        source: Data source name
        confidence: Matching confidence (0.0-1.0)
        is_primary: Whether this is the primary source for the entity
        
    Returns:
        True if successfully linked, False otherwise
    """
    try:
        # Check if mapping already exists
        result = await session.execute(
            select(EntityMapping).where(EntityMapping.coin_id == coin_id)
        )
        existing_mapping = result.scalar_one_or_none()
        
        if existing_mapping:
            # Update existing mapping
            existing_mapping.master_entity_id = master_entity_id
            existing_mapping.confidence = confidence
            existing_mapping.is_primary = 1 if is_primary else 0
            logger.info(
                "updated_entity_mapping",
                coin_id=coin_id,
                master_entity_id=master_entity_id
            )
        else:
            # Create new mapping
            mapping = EntityMapping(
                master_entity_id=master_entity_id,
                coin_id=coin_id,
                source=source,
                confidence=confidence,
                is_primary=1 if is_primary else 0,
                created_at=datetime.now(timezone.utc)
            )
            session.add(mapping)
            logger.info(
                "created_entity_mapping",
                coin_id=coin_id,
                master_entity_id=master_entity_id,
                source=source
            )
        
        await session.flush()
        return True
        
    except Exception as e:
        logger.error(
            "error_linking_coin_to_master_entity",
            error=str(e),
            coin_id=coin_id,
            master_entity_id=master_entity_id
        )
        return False


async def process_coin_for_master_entity(
    session: AsyncSession,
    coin: Coin
) -> bool:
    """Process a coin record to find or create its master entity and link them.
    
    This is the main entry point for the normalization process.
    
    Args:
        session: Database session
        coin: Coin record to process
        
    Returns:
        True if successfully processed, False otherwise
    """
    try:
        # Find or create master entity
        master_entity_id = await find_or_create_master_entity(session, coin)
        
        if not master_entity_id:
            logger.warning(
                "failed_to_find_or_create_master_entity",
                coin_id=coin.id,
                symbol=coin.symbol
            )
            return False
        
        # Link coin to master entity
        # Consider CoinGecko as primary source due to comprehensive data
        is_primary = coin.source == "coingecko"
        
        success = await link_coin_to_master_entity(
            session=session,
            coin_id=coin.id,
            master_entity_id=master_entity_id,
            source=coin.source,
            confidence=1.0,
            is_primary=is_primary
        )
        
        return success
        
    except Exception as e:
        logger.error(
            "error_processing_coin_for_master_entity",
            error=str(e),
            coin_id=coin.id
        )
        return False
