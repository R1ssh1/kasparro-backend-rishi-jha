"""
RSS Feed Ingestion Module for Cryptocurrency News

Ingests cryptocurrency news from RSS feed (https://rss.app/feeds/v1.1/tRI0JxEaEvcKz0HW.json)
Demonstrates schema unification with news articles alongside market data.
"""
import httpx
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.models import Coin
from schemas.ingestion import RSSFeedRecord, NormalizedCoin
from ingestion.base import BaseIngestion
from ingestion.rate_limiter import get_rate_limiter
import structlog

logger = structlog.get_logger()


class RSSFeedIngestion(BaseIngestion):
    """Ingestion from RSS.app cryptocurrency news feed"""
    
    SOURCE_NAME = "rss_feed"
    FEED_URL = "https://rss.app/feeds/v1.1/tRI0JxEaEvcKz0HW.json"
    
    def __init__(self, session: AsyncSession):
        super().__init__("rss_feed", session)
        self.rate_limiter = get_rate_limiter(self.SOURCE_NAME, calls_per_minute=20)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def _make_request(self) -> Dict[str, Any]:
        """Make HTTP request to RSS feed with retry logic"""
        await self.rate_limiter.acquire()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self.FEED_URL)
            response.raise_for_status()
            return response.json()
    
    async def fetch_data(self, last_cursor: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch RSS feed items
        
        Args:
            last_cursor: Last processed article ID (for incremental ingestion)
            
        Returns:
            List of RSS feed items (articles)
        """
        logger.info("Fetching RSS feed data", source=self.SOURCE_NAME, last_cursor=last_cursor)
        
        try:
            data = await self._make_request()
            items = data.get("items", [])
            
            # Filter to only new items if we have a cursor
            if last_cursor:
                # Items are sorted newest first, so we stop at the last seen ID
                new_items = []
                for item in items:
                    if item.get("id") == last_cursor:
                        break
                    new_items.append(item)
                items = new_items
            
            logger.info(
                f"Fetched {len(items)} RSS feed items",
                source=self.SOURCE_NAME,
                total_items=len(items),
                has_cursor=last_cursor is not None
            )
            
            return items
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {str(e)}", source=self.SOURCE_NAME, error=str(e))
            raise
    
    def normalize_record(self, raw_data: Dict[str, Any]) -> Coin:
        """
        Transform RSS feed item to normalized Coin model
        
        For RSS news articles, we create pseudo-coin records with:
        - symbol: "NEWS" (all news articles)
        - external_id: RSS item ID
        - name: Article title
        - current_price: 0.0 (news doesn't have price)
        - market_cap: 0.0
        - metadata: Full article data including URL, content, authors
        
        Args:
            raw_data: Raw RSS feed item
            
        Returns:
            Normalized Coin Pydantic model
        """
        try:
            # Validate with Pydantic schema
            validated = RSSFeedRecord(**raw_data)
            
            # Parse publication date
            last_updated = datetime.fromisoformat(validated.date_published.replace('Z', '+00:00'))
            
            # Build metadata with article details
            metadata = {
                "url": validated.url,
                "title": validated.title,
                "content_text": validated.content_text[:500] if validated.content_text else None,  # Truncate
                "authors": [author.name for author in validated.authors] if validated.authors else [],
                "image": validated.image,
                "date_published": validated.date_published,
                "type": "news_article"
            }
            
            # Return NormalizedCoin Pydantic model
            return NormalizedCoin(
                source=self.source_name,
                external_id=validated.id,
                symbol="NEWS",  # All news articles use same symbol
                name=validated.title[:100],  # Truncate to fit column
                current_price=Decimal("0.0"),  # News doesn't have price
                market_cap=Decimal("0.0"),
                volume_24h=Decimal("0.0"),
                price_change_24h=Decimal("0.0"),
                last_updated=last_updated
            )
        except Exception as e:
            logger.warning(f"Failed to normalize RSS record {raw_data.get('id')}: {str(e)}")
            return None
    
    def get_checkpoint_value(self, records: List[Dict[str, Any]]) -> str:
        """
        Get checkpoint value for RSS feed (most recent article ID)
        
        Args:
            records: List of raw RSS feed items
            
        Returns:
            Most recent article ID
        """
        if not records:
            return ""
        
        # Records are already sorted newest first from RSS feed
        # Use the first record's id as checkpoint
        checkpoint = records[0].get("id", "")
        logger.info(f"RSS checkpoint: {checkpoint}", source=self.SOURCE_NAME, checkpoint=checkpoint)
        return checkpoint
