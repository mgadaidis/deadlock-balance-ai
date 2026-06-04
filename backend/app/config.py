"""Centralised configuration loaded from .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    deadlock_api_base: str = "https://api.deadlock-api.com"
    deadlock_assets_base: str = "https://assets.deadlock-api.com"

    database_url: str = "sqlite:///./deadlock.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cache_ttl: int = 3600

    winrate_low: float = 0.47
    winrate_high: float = 0.53

    # Match-mode filter for analytics queries. The Deadlock API supports
    # filtering by mode so we can exclude Street Brawl / Sandbox / Bots.
    # Default = "Normal" (the regular matchmade mode players queue for).
    match_mode: str = "Normal"   # set to "" in .env to disable filtering
    # Minimum matches a hero needs before being included in analysis.
    min_hero_matches: int = 50

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
