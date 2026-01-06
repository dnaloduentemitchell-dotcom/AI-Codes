from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "NewsTracker"
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/forex"
    redis_url: str = "redis://redis:6379/0"

    price_provider: str = "demo"  # demo|alphavantage
    news_provider: str = "demo"  # demo|rss
    macro_provider: str = "demo"  # demo|csv

    alphavantage_api_key: str | None = None
    news_rss_urls: str = "https://www.ecb.europa.eu/rss/press.html"

    poll_prices_seconds: int = 60
    poll_news_seconds: int = 300
    poll_macro_seconds: int = 1800
    predict_seconds: int = 300

    signal_horizon_minutes: int = 60
    demo_mode: bool = True

    log_level: str = "INFO"
    model_dir: str = "app/ml/models"

    alert_confidence_threshold: float = 0.65


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
