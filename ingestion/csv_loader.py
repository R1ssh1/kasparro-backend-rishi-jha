"""CSV file data ingestion."""
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from decimal import Decimal

from schemas.ingestion import CSVRecord, NormalizedCoin
from ingestion.base import BaseIngestion


class CSVIngestion(BaseIngestion):
    """Ingest cryptocurrency data from CSV files."""
    
    def __init__(self, session, csv_path: str = "data/crypto_data.csv"):
        super().__init__("csv", session)
        self.csv_path = Path(csv_path)
    
    async def fetch_data(self, checkpoint: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Read data from CSV file.
        
        Args:
            checkpoint: Row number to start from (for incremental loading)
            
        Returns:
            List of CSV records
        """
        if not self.csv_path.exists():
            self.logger.warning(f"CSV file not found: {self.csv_path}")
            return []
        
        records = []
        start_row = int(checkpoint) if checkpoint else 0
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for idx, row in enumerate(reader):
                    if idx >= start_row:
                        records.append(row)
            
            self.logger.info(f"Read {len(records)} records from CSV (starting at row {start_row})")
            return records
            
        except Exception as e:
            self.logger.error(f"Failed to read CSV file: {str(e)}")
            raise
    
    def normalize_record(self, raw_data: Dict[str, Any]) -> Optional[NormalizedCoin]:
        """
        Normalize CSV record to unified schema.
        
        Args:
            raw_data: Raw CSV row
            
        Returns:
            Normalized coin record or None if validation fails
        """
        try:
            # Validate with Pydantic
            validated = CSVRecord(**raw_data)
            
            # Map to normalized schema
            normalized = NormalizedCoin(
                source=self.source_name,
                external_id=validated.id,
                symbol=validated.symbol.upper(),
                name=validated.name,
                current_price=Decimal(str(validated.price)) if validated.price else None,
                market_cap=Decimal(str(validated.market_cap)) if validated.market_cap else None,
                volume_24h=Decimal(str(validated.volume_24h)) if validated.volume_24h else None,
                price_change_24h=Decimal(str(validated.price_change_24h)) if validated.price_change_24h else None,
                last_updated=validated.timestamp
            )
            
            return normalized
            
        except Exception as e:
            self.logger.warning(f"Failed to normalize CSV record {raw_data.get('id')}: {str(e)}")
            return None
    
    def get_checkpoint_value(self, records: List[Dict[str, Any]]) -> Optional[str]:
        """
        Return total rows processed as checkpoint.
        
        Returns:
            Number of rows processed
        """
        return str(len(records))
