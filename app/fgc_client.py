import json
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx
from google.transit import gtfs_realtime_pb2

from .config import Settings

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


class FGCClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = TTLCache(settings.cache_ttl_seconds)
        self.client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    async def get_records(
        self,
        dataset: str,
        *,
        where: str | None = None,
        limit: int | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        limit = limit or self.settings.source_records_limit
        params = [f"limit={limit}"]
        if where:
            params.append(f"where={quote(where)}")
        if order_by:
            params.append(f"order_by={quote(order_by)}")
        url = f"{self.settings.api_base_url.rstrip('/')}/{dataset}/records?{'&'.join(params)}"
        cached = self.cache.get(url)
        if cached is not None:
            return cached

        logger.info("Fetching FGC records dataset=%s where=%s limit=%s", dataset, where, limit)
        results: list[dict[str, Any]] = []
        page_size = min(limit, 100)
        total_count: int | None = None
        offset = 0

        while len(results) < limit:
            page_params = [f"limit={page_size}", f"offset={offset}"]
            if where:
                page_params.append(f"where={quote(where)}")
            if order_by:
                page_params.append(f"order_by={quote(order_by)}")
            page_url = f"{self.settings.api_base_url.rstrip('/')}/{dataset}/records?{'&'.join(page_params)}"
            response = await self.client.get(page_url)
            response.raise_for_status()
            data = json.loads(response.content.decode("utf-8"))
            page_results = data.get("results", [])
            total_count = data.get("total_count", total_count)
            results.extend(page_results)

            if not page_results or (total_count is not None and len(results) >= total_count):
                break
            offset += page_size

        results = results[:limit]
        self.cache.set(url, results)
        return results

    async def get_realtime_feed(self, dataset: str) -> gtfs_realtime_pb2.FeedMessage | None:
        cache_key = f"realtime:{dataset}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        records = await self.get_records(dataset, limit=1)
        file_url = records[0].get("file", {}).get("url") if records else None
        if not file_url:
            logger.warning("Realtime dataset %s did not expose a file URL", dataset)
            self.cache.set(cache_key, None)
            return None

        logger.info("Fetching FGC realtime protobuf dataset=%s", dataset)
        response = await self.client.get(file_url)
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        self.cache.set(cache_key, feed)
        return feed

    async def ping(self) -> None:
        await self.get_records(self.settings.schedules_dataset, where='stop_name like "Sant Boi"', limit=1)
