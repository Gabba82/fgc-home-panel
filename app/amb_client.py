import logging
import re
import time
from datetime import datetime, time as datetime_time, timedelta
from html import unescape
from html.parser import HTMLParser
from typing import Any

import httpx

from .config import Settings
from .models import BusArrival, BusStopResponse

logger = logging.getLogger(__name__)


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl_seconds = ttl_seconds
        self._values: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        item = self._values.get(key)
        if not item:
            return None
        created_at, value = item
        if time.monotonic() - created_at > self.ttl_seconds:
            self._values.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._values[key] = (time.monotonic(), value)


class AMBStopParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: dict[str, dict[str, Any]] = {}
        self.stop_name: str | None = None
        self._capture: tuple[str, str] | None = None
        self._current_row_id: str | None = None
        self._title_depth = 0
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        element_id = attributes.get("id", "")
        css_class = attributes.get("class", "")

        if tag == "h3" and "title" in css_class.split():
            self._title_depth = 1
            self._title_parts = []
            return
        if self._title_depth:
            self._title_depth += 1

        row_id = self._row_id(element_id) or self._current_row_id
        if not row_id:
            return

        self._current_row_id = row_id
        self.rows.setdefault(row_id, {})
        if tag == "span" and "LNum" in css_class:
            self._capture = (row_id, "line")
            self.rows[row_id].update(self._colors(attributes.get("style", "")))
        elif element_id.endswith("lblSentido"):
            self._capture = (row_id, "destination")
        elif element_id.endswith("lblTiempo2"):
            self._capture = (row_id, "wait_text")

    def handle_endtag(self, tag: str) -> None:
        if self._title_depth:
            self._title_depth -= 1
            if self._title_depth == 0:
                title = self._clean("".join(self._title_parts))
                match = re.search(r"Parada\s+\d+\s+-\s+(.+)", title)
                if match:
                    self.stop_name = match.group(1)
        if self._capture:
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._title_depth:
            self._title_parts.append(data)
        if not self._capture:
            return
        row_id, field = self._capture
        current = self.rows.setdefault(row_id, {}).get(field, "")
        self.rows[row_id][field] = self._clean(f"{current} {data}")

    def arrivals(self, limit: int, settings: Settings) -> list[BusArrival]:
        arrivals: list[BusArrival] = []
        for row_id in sorted(self.rows):
            row = self.rows[row_id]
            line = row.get("line")
            wait_text = row.get("wait_text")
            if not line or not wait_text:
                continue
            minutes = self._minutes(wait_text)
            scheduled_time = self._scheduled_time(wait_text)
            destination = row.get("destination")
            arrivals.append(
                BusArrival(
                    line=line,
                    destination=destination.replace("Sentit:", "").strip() if destination else None,
                    wait_text=wait_text,
                    minutes=minutes,
                    scheduled_time=scheduled_time,
                    route_color=row.get("route_color"),
                    route_text_color=row.get("route_text_color"),
                )
            )
        arrivals.sort(key=lambda arrival: self._sort_key(arrival, settings))
        return arrivals[:limit]

    def _sort_key(self, arrival: BusArrival, settings: Settings) -> tuple[int, float]:
        if arrival.minutes is not None:
            return (0, arrival.minutes)
        if arrival.scheduled_time:
            parsed_time = self._parse_scheduled_time(arrival.scheduled_time)
            if parsed_time:
                current = datetime.now(settings.tzinfo)
                scheduled = datetime.combine(current.date(), parsed_time, tzinfo=settings.tzinfo)
                if scheduled < current:
                    scheduled += timedelta(days=1)
                return (1, scheduled.timestamp())
        return (2, float("inf"))

    def _parse_scheduled_time(self, value: str) -> datetime_time | None:
        try:
            hour, minute = [int(part) for part in value.split(":", maxsplit=1)]
        except ValueError:
            return None
        return datetime_time(hour % 24, minute)

    def _row_id(self, element_id: str) -> str | None:
        match = re.search(r"rLineasConParada_(ctl\d+)_", element_id)
        return match.group(1) if match else None

    def _colors(self, style: str) -> dict[str, str]:
        colors: dict[str, str] = {}
        background = re.search(r"background-color:\s*#?([0-9a-fA-F]{6})", style)
        text = re.search(r"(?:^|;)\s*color:\s*#?([0-9a-fA-F]{6})", style)
        if background:
            colors["route_color"] = background.group(1)
        if text:
            colors["route_text_color"] = text.group(1)
        return colors

    def _clean(self, value: str) -> str:
        return re.sub(r"\s+", " ", unescape(value)).strip()

    def _minutes(self, value: str) -> int | None:
        match = re.search(r"\b(\d+)\s*min\b", value, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _scheduled_time(self, value: str) -> str | None:
        match = re.search(r"\bProg\.\s*(\d{1,2}:\d{2})", value, re.IGNORECASE)
        return match.group(1) if match else None


class AMBClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = TTLCache(settings.cache_ttl_seconds)
        self.client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    async def stop_arrivals(self, stop_id: str) -> BusStopResponse:
        cache_key = f"amb-stop:{stop_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self._api_stop_arrivals(stop_id)
        if result and result.arrivals:
            self.cache.set(cache_key, result)
            return result

        logger.info("TMB iBus returned no arrivals for stop=%s; falling back to AMB public stop page", stop_id)
        result = await self._public_stop_arrivals(stop_id)
        self.cache.set(cache_key, result)
        return result

    async def _api_stop_arrivals(self, stop_id: str) -> BusStopResponse | None:
        if not self.settings.amb_app_key:
            return None

        response = await self.client.get(
            f"{self.settings.tmb_ibus_base_url.rstrip('/')}/{stop_id}",
            params={"app_id": self.settings.amb_app_id, "app_key": self.settings.amb_app_key},
        )
        response.raise_for_status()
        data = response.json()
        arrivals = []
        ibus = sorted(
            data.get("data", {}).get("ibus", []),
            key=lambda item: (item.get("t-in-s") is None, item.get("t-in-s") or item.get("t-in-min") or float("inf")),
        )
        for item in ibus[: self.settings.bus_arrivals_limit]:
            minutes = item.get("t-in-min")
            wait_text = item.get("text-ca") or item.get("text") or (f"{minutes} min" if minutes is not None else "")
            arrivals.append(
                BusArrival(
                    line=str(item.get("line") or ""),
                    destination=item.get("destination"),
                    wait_text=wait_text,
                    minutes=minutes,
                    scheduled_time=None,
                )
            )
        return BusStopResponse(
            stop_id=stop_id,
            stop_name=None,
            updated_at=datetime.now(self.settings.tzinfo).isoformat(),
            arrivals=arrivals,
        )

    async def _public_stop_arrivals(self, stop_id: str) -> BusStopResponse:
        response = await self.client.get(
            self.settings.bus_stop_url,
            params={"cerca": "1", "linea": "0", "punto": stop_id, "version": "0"},
        )
        response.raise_for_status()

        parser = AMBStopParser()
        parser.feed(response.text)
        result = BusStopResponse(
            stop_id=stop_id,
            stop_name=parser.stop_name,
            updated_at=datetime.now(self.settings.tzinfo).isoformat(),
            arrivals=parser.arrivals(self.settings.bus_arrivals_limit, self.settings),
        )
        return result
