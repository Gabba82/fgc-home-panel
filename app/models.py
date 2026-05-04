from typing import Any, Literal

from pydantic import BaseModel, Field


TrainStatus = Literal["on_time", "delayed", "cancelled", "unknown_realtime", "service_alert"]


class RouteSense(BaseModel):
    sense: str
    origin: str
    destination: str
    title: str


class Alert(BaseModel):
    title: str
    description: str | None = None
    severity: str | None = None
    url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class Train(BaseModel):
    line: str
    origin_stop: str
    destination_stop: str
    headsign: str | None = None
    scheduled_departure: str
    scheduled_arrival: str | None = None
    estimated_departure: str | None = None
    estimated_arrival: str | None = None
    delay_minutes: int | None = None
    platform: str | None = None
    status: TrainStatus
    route_color: str | None = None
    route_text_color: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class NextTrainsResponse(BaseModel):
    sense: str
    origin: str
    destination: str
    updated_at: str
    trains: list[Train]
    alerts: list[Alert] = Field(default_factory=list)


class BusArrival(BaseModel):
    line: str
    destination: str | None = None
    wait_text: str
    minutes: int | None = None
    scheduled_time: str | None = None
    route_color: str | None = None
    route_text_color: str | None = None


class BusStopResponse(BaseModel):
    stop_id: str
    stop_name: str | None = None
    updated_at: str
    arrivals: list[BusArrival]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    fgc_api: Literal["ok", "error"]
    updated_at: str
    detail: str | None = None
