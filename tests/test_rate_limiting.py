"""Tests for rate limiting functionality."""
import pytest
import time
import asyncio
from ingestion.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Test basic rate limiting functionality."""
    limiter = RateLimiter(calls_per_minute=60)
    
    # Should allow immediate calls
    await limiter.acquire()
    await limiter.acquire()
    
    # Tokens should be reduced
    assert limiter.tokens < 60


@pytest.mark.asyncio
async def test_rate_limiter_refill():
    """Test token refill mechanism."""
    limiter = RateLimiter(calls_per_minute=60)
    
    # Use some tokens
    await limiter.acquire()
    initial_tokens = limiter.tokens
    
    # Wait and check refill
    await asyncio.sleep(1)
    limiter._refill()
    
    assert limiter.tokens > initial_tokens


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_exhausted():
    """Test that rate limiter blocks when tokens are exhausted."""
    limiter = RateLimiter(calls_per_minute=2)  # Very low limit
    
    # Exhaust tokens
    await limiter.acquire()
    await limiter.acquire()
    
    # Next call should take time (waiting for refill)
    start = time.time()
    await limiter.acquire()
    duration = time.time() - start
    
    # Should have waited at least some time
    assert duration > 0.1
