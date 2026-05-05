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
    panel_title: str = "Pròxims trens"
    panel_subtitle: str = ""
    card_min_width_px: int = Field(default=280, ge=180, le=420)

    schedules_dataset: str = "viajes-de-hoy"
    trip_updates_dataset: str = "trip-updates-gtfs_realtime"
    alerts_dataset: str = "alerts-gtfs_realtime"
    vehicle_positions_dataset: str = "vehicle-positions-gtfs_realtime"

    trains_limit: int = Field(default=5, ge=1, le=10)
    source_records_limit: int = Field(default=500, ge=50, le=1000)
    train_routes: str = "Sant Boi|Barcelona - Plaça Espanya;Barcelona - Plaça Espanya|Sant Boi"
    bus_stop_id: str = ""
    bus_stop_ids: str | None = None
    bus_stop_url: str = "https://www.ambmobilitat.cat/Principales/DatosParada.aspx"
    amb_app_id: str = "5b1fdf3a"
    amb_app_key: str | None = None
    tmb_ibus_base_url: str = "https://api.tmb.cat/v1/ibus/stops"
    bus_arrivals_limit: int = Field(default=6, ge=1, le=12)

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def configured_bus_stop_ids(self) -> list[str]:
        value = self.bus_stop_ids or self.bus_stop_id
        stop_ids = [stop_id.strip() for stop_id in value.split(",") if stop_id.strip()]
        return stop_ids

    @property
    def configured_train_routes(self) -> list[tuple[str, str]]:
        routes = []
        for item in self.train_routes.split(";"):
            parts = [part.strip() for part in item.split("|", maxsplit=1)]
            if len(parts) == 2 and all(parts):
                routes.append((parts[0], parts[1]))
        return routes or [("Sant Boi", "Barcelona - Plaça Espanya"), ("Barcelona - Plaça Espanya", "Sant Boi")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
