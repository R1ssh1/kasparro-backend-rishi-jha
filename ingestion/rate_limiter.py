"""Rate limiter implementation using token bucket algorithm."""
import asyncio
import time
from typing import Dict


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_minute: Maximum number of calls allowed per minute
        """
        self.rate = calls_per_minute
        self.tokens = float(calls_per_minute)
        self.last_refill = time.time()
        self._lock = asyncio.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on time elapsed (tokens per second = rate / 60)
        tokens_to_add = elapsed * (self.rate / 60.0)
        self.tokens = min(self.rate, self.tokens + tokens_to_add)
        self.last_refill = now
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            while self.tokens < 1:
                # Wait a short time before checking again
                await asyncio.sleep(0.1)
                self._refill()
            
            self.tokens -= 1


class RateLimiterRegistry:
    """Registry to manage multiple rate limiters for different sources."""
    
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {}
    
    def get_limiter(self, source: str, calls_per_minute: int) -> RateLimiter:
        """Get or create a rate limiter for a source."""
        if source not in self._limiters:
            self._limiters[source] = RateLimiter(calls_per_minute)
        return self._limiters[source]


# Global registry
rate_limiter_registry = RateLimiterRegistry()


def get_rate_limiter(source: str, calls_per_minute: int) -> RateLimiter:
    """
    Get a rate limiter for a specific source.
    
    Args:
        source: Name of the data source
        calls_per_minute: Maximum calls per minute
        
    Returns:
        RateLimiter instance for the source
    """
    return rate_limiter_registry.get_limiter(source, calls_per_minute)
