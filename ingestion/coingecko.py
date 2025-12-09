"""CoinGecko API data ingestion."""
import httpx
from typing import List, Dict, Any, Optional, Set
from decimal import Decimal
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from schemas.ingestion import CoinGeckoRecord, NormalizedCoin
from ingestion.base import BaseIngestion
from ingestion.rate_limiter import rate_limiter_registry


class CoinGeckoIngestion(BaseIngestion):
    """Ingest cryptocurrency data from CoinGecko API."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, session):
        super().__init__("coingecko", session)
        self.api_key = settings.coingecko_api_key
        self.rate_limiter = rate_limiter_registry.get_limiter(
            "coingecko",
            settings.coingecko_rate_limit
        )
    
    def get_expected_schema(self) -> Optional[Set[str]]:
        """Return expected CoinGecko API field names."""
        return {
            "id", "symbol", "name", "current_price", "market_cap",
            "total_volume", "price_change_percentage_24h", "last_updated"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make HTTP request with retry and rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response
        """
        # Acquire rate limit token
        await self.rate_limiter.acquire()
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "x-cg-demo-api-key": self.api_key,
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            self.logger.info(f"Making request to {endpoint}", extra={"params": params})
            
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 429:
                self.logger.warning("Rate limited by CoinGecko API")
                raise httpx.HTTPError("Rate limited")
            
            response.raise_for_status()
            return response.json()
    
    async def fetch_data(self, checkpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch coin market data from CoinGecko.
        
        Args:
            checkpoint: Not used for CoinGecko (always fetches latest)
            
        Returns:
            List of coin records
        """
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 100,  # Max 250, using 100 for safety
            "page": 1,
            "sparkline": False,
            "price_change_percentage": "24h"
        }
        
        try:
            data = await self._make_request("/coins/markets", params)
            
            if isinstance(data, list):
                self.logger.info(f"Fetched {len(data)} coins from CoinGecko")
                return data
            else:
                self.logger.error(f"Unexpected response format: {type(data)}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to fetch CoinGecko data: {str(e)}")
            raise
    
    def normalize_record(self, raw_data: Dict[str, Any]) -> Optional[NormalizedCoin]:
        """
        Normalize CoinGecko record to unified schema.
        
        Args:
            raw_data: Raw CoinGecko API response
            
        Returns:
            Normalized coin record or None if validation fails
        """
        try:
            # Validate with Pydantic
            validated = CoinGeckoRecord(**raw_data)
            
            # Map to normalized schema
            normalized = NormalizedCoin(
                source=self.source_name,
                external_id=validated.id,
                symbol=validated.symbol.upper(),
                name=validated.name,
                current_price=Decimal(str(validated.current_price)) if validated.current_price else None,
                market_cap=Decimal(str(validated.market_cap)) if validated.market_cap else None,
                volume_24h=Decimal(str(validated.total_volume)) if validated.total_volume else None,
                price_change_24h=Decimal(str(validated.price_change_percentage_24h)) if validated.price_change_percentage_24h else None,
                last_updated=validated.last_updated
            )
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"Failed to normalize record {raw_data.get('id')}: {str(e)}")
            return None
    
    def get_checkpoint_value(self, records: List[Dict[str, Any]]) -> Optional[str]:
        """
        CoinGecko doesn't need incremental checkpoint (always fetches latest).
        
        Returns:
            Current timestamp as checkpoint for tracking
        """
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
