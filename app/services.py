import logging
import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any

from google.transit import gtfs_realtime_pb2

from .config import Settings
from .fgc_client import FGCClient
from .models import Alert, NextTrainsResponse, RouteSense, Train

logger = logging.getLogger(__name__)

ROUTES = {
    "santboi-espanya": RouteSense(
        sense="santboi-espanya",
        origin="Sant Boi",
        destination="Barcelona - Plaça Espanya",
        title="Sant Boi -> Plaça Espanya",
    ),
    "espanya-santboi": RouteSense(
        sense="espanya-santboi",
        origin="Barcelona - Plaça Espanya",
        destination="Sant Boi",
        title="Plaça Espanya -> Sant Boi",
    ),
}


@dataclass
class RealtimeStopUpdate:
    stop_id: str | None
    route_id: str | None
    trip_id: str | None
    departure_ts: int | None
    arrival_ts: int | None
    delay_seconds: int | None
    cancelled: bool


def now_local(settings: Settings) -> datetime:
    return datetime.now(settings.tzinfo)


def normalize(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def parse_hms(value: str | None) -> time | None:
    if not value:
        return None
    hour, minute, second = [int(part) for part in value.split(":")]
    hour = hour % 24
    return time(hour, minute, second)


def service_datetime(record: dict[str, Any], field: str, settings: Settings) -> datetime | None:
    hms = parse_hms(record.get(field))
    if not hms:
        return None
    service_date = datetime.strptime(record["date"], "%Y-%m-%d").date()
    hour = int(record[field].split(":")[0])
    dt = datetime.combine(service_date, hms, tzinfo=settings.tzinfo)
    if hour >= 24:
        dt += timedelta(days=hour // 24)
    return dt


def display_hms(dt: datetime | None) -> str | None:
    return dt.strftime("%H:%M:%S") if dt else None


def platform(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def is_same_trip_candidate(origin: dict[str, Any], destination: dict[str, Any]) -> bool:
    comparable_fields = ("route_short_name", "shape_id", "trip_headsign")
    if any(origin.get(field) != destination.get(field) for field in comparable_fields):
        return False
    origin_seq = origin.get("stop_sequence")
    dest_seq = destination.get("stop_sequence")
    if origin_seq is None or dest_seq is None:
        return False
    return int(dest_seq) > int(origin_seq)


def relevant_alert_text(alert: Alert) -> str:
    return normalize(" ".join(filter(None, [alert.title, alert.description])))


class FGCService:
    def __init__(self, client: FGCClient, settings: Settings):
        self.client = client
        self.settings = settings

    def routes(self) -> list[RouteSense]:
        return list(ROUTES.values())

    async def next_trains(self, sense: str) -> NextTrainsResponse:
        if sense not in ROUTES:
            raise ValueError(f"Unknown sense: {sense}")

        route = ROUTES[sense]
        current = now_local(self.settings)
        origin_query = self._stop_query(route.origin)
        destination_query = self._stop_query(route.destination)

        origin_records = await self.client.get_records(
            self.settings.schedules_dataset,
            where=origin_query,
        )
        destination_records = await self.client.get_records(
            self.settings.schedules_dataset,
            where=destination_query,
        )
        realtime_updates = await self._safe_realtime_updates()
        alerts = await self.alerts()

        trains: list[Train] = []
        for origin in sorted(origin_records, key=lambda item: item.get("departure_time", "")):
            departure_dt = service_datetime(origin, "departure_time", self.settings)
            if not departure_dt or departure_dt <= current:
                continue

            destination = self._find_destination(origin, destination_records)
            if not destination:
                continue

            arrival_dt = service_datetime(destination, "arrival_time", self.settings)
            rt = self._match_realtime(origin, departure_dt, realtime_updates)
            estimated_departure = departure_dt
            estimated_arrival = arrival_dt
            delay_minutes: int | None = None
            status = "unknown_realtime"

            if rt:
                if rt.cancelled:
                    status = "cancelled"
                else:
                    delay_seconds = rt.delay_seconds
                    if delay_seconds is None and rt.departure_ts:
                        delay_seconds = int(rt.departure_ts - departure_dt.timestamp())
                    delay_minutes = max(0, math.ceil((delay_seconds or 0) / 60))
                    status = "delayed" if delay_minutes > 0 else "on_time"
                    estimated_departure = departure_dt + timedelta(minutes=delay_minutes)
                    if arrival_dt:
                        estimated_arrival = arrival_dt + timedelta(minutes=delay_minutes)

            route_alerts = self._alerts_for_train(origin, alerts)
            if status == "unknown_realtime" and route_alerts:
                status = "service_alert"

            trains.append(
                Train(
                    line=str(origin.get("route_short_name") or ""),
                    origin_stop=str(origin.get("stop_name") or route.origin),
                    destination_stop=str(destination.get("stop_name") or route.destination),
                    headsign=origin.get("trip_headsign"),
                    scheduled_departure=display_hms(departure_dt) or origin.get("departure_time"),
                    scheduled_arrival=display_hms(arrival_dt),
                    estimated_departure=display_hms(estimated_departure),
                    estimated_arrival=display_hms(estimated_arrival),
                    delay_minutes=delay_minutes,
                    platform=platform(origin.get("platform_code")),
                    status=status,
                    route_color=origin.get("route_color"),
                    route_text_color=origin.get("route_text_color"),
                    raw={
                        "origin": origin,
                        "destination": destination,
                        "matching_strategy": "route_short_name+shape_id+trip_headsign+stop_sequence+time_window",
                    },
                )
            )
            if len(trains) >= self.settings.trains_limit:
                break

        return NextTrainsResponse(
            sense=sense,
            origin=route.origin,
            destination=route.destination,
            updated_at=current.isoformat(),
            trains=trains,
            alerts=self._route_alerts(alerts),
        )

    async def alerts(self) -> list[Alert]:
        try:
            feed = await self.client.get_realtime_feed(self.settings.alerts_dataset)
        except Exception as exc:
            logger.warning("Could not read FGC alerts: %s", exc)
            return [
                Alert(
                    title="No se han podido consultar las alertas de FGC",
                    description="La aplicación seguirá mostrando horarios previstos.",
                    severity="unknown",
                )
            ]
        if not feed:
            return []

        alerts: list[Alert] = []
        for entity in feed.entity:
            if not entity.HasField("alert"):
                continue
            item = entity.alert
            title = self._translated_text(item.header_text)
            description = self._translated_text(item.description_text)
            severity = gtfs_realtime_pb2.Alert.SeverityLevel.Name(item.severity_level) if item.severity_level else None
            url = self._translated_text(item.url)
            alerts.append(
                Alert(
                    title=title or "Alerta de servicio FGC",
                    description=description,
                    severity=severity,
                    url=url,
                    raw={"id": entity.id, "cause": item.cause, "effect": item.effect},
                )
            )
        return self._route_alerts(alerts)

    async def vehicle_positions_summary(self) -> dict[str, Any]:
        try:
            feed = await self.client.get_realtime_feed(self.settings.vehicle_positions_dataset)
        except Exception as exc:
            logger.warning("Could not read vehicle positions: %s", exc)
            return {"available": False, "vehicles": 0}
        if not feed:
            return {"available": False, "vehicles": 0}
        return {"available": True, "vehicles": sum(1 for entity in feed.entity if entity.HasField("vehicle"))}

    def _stop_query(self, stop_name: str) -> str:
        if "Plaça Espanya" in stop_name:
            return 'stop_name like "Espanya"'
        return f'stop_name like "{stop_name}"'

    def _find_destination(
        self,
        origin: dict[str, Any],
        destinations: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        departure_dt = service_datetime(origin, "departure_time", self.settings)
        candidates: list[tuple[float, dict[str, Any]]] = []
        for destination in destinations:
            if not is_same_trip_candidate(origin, destination):
                continue
            arrival_dt = service_datetime(destination, "arrival_time", self.settings)
            if not departure_dt or not arrival_dt:
                continue
            minutes = (arrival_dt - departure_dt).total_seconds() / 60
            if 2 <= minutes <= 90:
                candidates.append((minutes, destination))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    async def _safe_realtime_updates(self) -> list[RealtimeStopUpdate]:
        try:
            feed = await self.client.get_realtime_feed(self.settings.trip_updates_dataset)
        except Exception as exc:
            logger.warning("Could not read trip updates: %s", exc)
            return []
        if not feed:
            return []

        updates: list[RealtimeStopUpdate] = []
        for entity in feed.entity:
            if not entity.HasField("trip_update"):
                continue
            trip_update = entity.trip_update
            cancelled = (
                trip_update.trip.schedule_relationship
                == gtfs_realtime_pb2.TripDescriptor.ScheduleRelationship.CANCELED
            )
            for stop_update in trip_update.stop_time_update:
                departure = stop_update.departure if stop_update.HasField("departure") else None
                arrival = stop_update.arrival if stop_update.HasField("arrival") else None
                updates.append(
                    RealtimeStopUpdate(
                        stop_id=stop_update.stop_id or None,
                        route_id=trip_update.trip.route_id or None,
                        trip_id=trip_update.trip.trip_id or None,
                        departure_ts=departure.time if departure and departure.time else None,
                        arrival_ts=arrival.time if arrival and arrival.time else None,
                        delay_seconds=departure.delay if departure and departure.HasField("delay") else None,
                        cancelled=cancelled,
                    )
                )
        return updates

    def _match_realtime(
        self,
        origin: dict[str, Any],
        departure_dt: datetime,
        updates: list[RealtimeStopUpdate],
    ) -> RealtimeStopUpdate | None:
        stop_id = origin.get("stop_id")
        if not stop_id:
            return None
        best: tuple[float, RealtimeStopUpdate] | None = None
        for update in updates:
            if update.stop_id != stop_id or not update.departure_ts:
                continue
            diff = abs(update.departure_ts - departure_dt.timestamp())
            if diff <= 20 * 60 and (best is None or diff < best[0]):
                best = (diff, update)
        return best[1] if best else None

    def _alerts_for_train(self, origin: dict[str, Any], alerts: list[Alert]) -> list[Alert]:
        haystack_values = [
            origin.get("route_short_name"),
            origin.get("route_long_name"),
            origin.get("stop_name"),
            origin.get("trip_headsign"),
            "llobregat",
            "anoia",
            "fgc",
        ]
        haystack = [normalize(str(value)) for value in haystack_values if value]
        return [alert for alert in alerts if any(token and token in relevant_alert_text(alert) for token in haystack)]

    def _route_alerts(self, alerts: list[Alert]) -> list[Alert]:
        tokens = ["llobregat", "anoia", "sant boi", "espanya", "placa espanya", "fgc"]
        return [alert for alert in alerts if any(token in relevant_alert_text(alert) for token in tokens)]

    def _translated_text(self, translated_string: Any) -> str | None:
        if not translated_string or not translated_string.translation:
            return None
        preferred = None
        fallback = None
        for translation in translated_string.translation:
            text = translation.text.strip()
            if not text:
                continue
            fallback = fallback or text
            if translation.language.lower() in {"ca", "es", "cat", "spa"}:
                preferred = text
                break
        return preferred or fallback
