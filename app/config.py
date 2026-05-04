from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FGC_", env_file=".env", extra="ignore")

    api_base_url: str = "https://dadesobertes.fgc.cat/api/explore/v2.1/catalog/datasets"
    timezone: str = "Europe/Madrid"
    cache_ttl_seconds: int = Field(default=30, ge=1)
    http_timeout_seconds: float = Field(default=8.0, gt=0)
    log_level: str = "INFO"

    schedules_dataset: str = "viajes-de-hoy"
    trip_updates_dataset: str = "trip-updates-gtfs_realtime"
    alerts_dataset: str = "alerts-gtfs_realtime"
    vehicle_positions_dataset: str = "vehicle-positions-gtfs_realtime"

    trains_limit: int = Field(default=5, ge=1, le=10)
    source_records_limit: int = Field(default=500, ge=50, le=1000)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()
