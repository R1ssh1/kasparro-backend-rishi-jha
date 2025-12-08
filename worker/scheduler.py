"""ETL worker scheduler that runs ingestion jobs on a schedule."""
import asyncio
import structlog
from datetime import datetime, timezone

from core.config import settings
from core.database import AsyncSessionLocal
from ingestion.coingecko import CoinGeckoIngestion
from ingestion.csv_loader import CSVIngestion

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


async def run_etl_pipeline():
    """Execute all ETL ingestion sources."""
    logger.info("Starting ETL pipeline run")
    
    async with AsyncSessionLocal() as session:
        # Run CoinGecko ingestion
        try:
            logger.info("Starting CoinGecko ingestion")
            coingecko = CoinGeckoIngestion(session)
            await coingecko.run()
            logger.info("CoinGecko ingestion completed")
        except Exception as e:
            logger.error(f"CoinGecko ingestion failed: {str(e)}", exc_info=True)
    
    async with AsyncSessionLocal() as session:
        # Run CSV ingestion
        try:
            logger.info("Starting CSV ingestion")
            csv_loader = CSVIngestion(session)
            await csv_loader.run()
            logger.info("CSV ingestion completed")
        except Exception as e:
            logger.error(f"CSV ingestion failed: {str(e)}", exc_info=True)
    
    logger.info("ETL pipeline run completed")


async def scheduler_loop():
    """Main scheduler loop that runs ETL at configured intervals."""
    schedule_minutes = settings.etl_schedule_minutes
    logger.info(f"ETL scheduler started (running every {schedule_minutes} minutes)")
    
    while True:
        try:
            start_time = datetime.now(timezone.utc)
            logger.info(f"ETL run started at {start_time.isoformat()}")
            
            await run_etl_pipeline()
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.info(f"ETL run completed in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"ETL pipeline error: {str(e)}", exc_info=True)
        
        # Wait for next scheduled run
        wait_seconds = schedule_minutes * 60
        logger.info(f"Waiting {wait_seconds} seconds until next run...")
        await asyncio.sleep(wait_seconds)


if __name__ == "__main__":
    logger.info("Starting Kasparro ETL Worker")
    asyncio.run(scheduler_loop())
