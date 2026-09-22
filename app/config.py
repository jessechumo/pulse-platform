from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PULSE_", env_file=".env", extra="ignore")

    app_name: str = "pulse-platform"
    environment: str = "development"
    log_level: str = "INFO"
    version: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://pulse:pulse@localhost:5432/pulse"


@lru_cache
def get_settings() -> Settings:
    return Settings()
