"""Application configuration settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # DynamoDB Configuration
    dynamodb_table_name: str = "TimeTrack-Transit-DB"
    dynamodb_endpoint_url: Optional[str] = None  # For local development

    # Application Configuration
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # Station Configuration (Humble, TX)
    station_name: str = "Humble Transit Station"
    station_timezone: str = "America/Chicago"

    # Late departure threshold in minutes
    late_threshold_minutes: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
