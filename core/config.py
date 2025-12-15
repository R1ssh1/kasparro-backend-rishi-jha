"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str
    database_url_sync: str
    
    # API Keys
    coingecko_api_key: str
    admin_api_key: Optional[str] = None
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    
    # Rate Limiting
    coingecko_rate_limit: int = 30  # calls per minute
    
    # ETL Schedule
    etl_schedule_minutes: int = 60
    
    # Failure Injection (for testing)
    enable_failure_injection: bool = False
    failure_probability: float = 0.0
    fail_at_record: Optional[int] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
