"""Test configuration and fixtures."""
import pytest
import asyncio
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from core.database import Base
from core.config import settings

# Test database URL - use 'db' when in Docker, 'localhost' otherwise
DB_HOST = os.getenv("DATABASE_HOST", "localhost")
TEST_DATABASE_URL = f"postgresql+asyncpg://kasparro:kasparro@{DB_HOST}:5432/kasparro"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_coingecko_response():
    """Mock CoinGecko API response."""
    return [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 45000.0,
            "market_cap": 850000000000,
            "total_volume": 28000000000,
            "price_change_percentage_24h": 2.5,
            "last_updated": "2025-12-08T10:00:00Z"
        },
        {
            "id": "ethereum",
            "symbol": "eth",
            "name": "Ethereum",
            "current_price": 2500.0,
            "market_cap": 300000000000,
            "total_volume": 15000000000,
            "price_change_percentage_24h": -1.2,
            "last_updated": "2025-12-08T10:00:00Z"
        }
    ]


@pytest.fixture
def mock_csv_data():
    """Mock CSV data."""
    return [
        {
            "id": "btc-csv",
            "symbol": "BTC",
            "name": "Bitcoin",
            "price": "45000.50",
            "market_cap": "850000000000",
            "volume_24h": "28000000000",
            "price_change_24h": "2.5",
            "timestamp": "2025-12-08T10:00:00Z"
        }
    ]
