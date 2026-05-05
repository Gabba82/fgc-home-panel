import asyncio
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

    def get(self, key: str, *, allow_stale: bool = False) -> Any | None:
        item = self._values.get(key)
        if not item:
            return None
        created_at, value = item
        if not allow_stale and time.monotonic() - created_at > self.ttl_seconds:
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._values[key] = (time.monotonic(), value)


class FGCClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = TTLCache(settings.cache_ttl_seconds)
        self.client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
        self._inflight_records: dict[str, asyncio.Task[list[dict[str, Any]]]] = {}
        self._inflight_realtime: dict[str, asyncio.Task[gtfs_realtime_pb2.FeedMessage | None]] = {}

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
        inflight = self._inflight_records.get(url)
        if inflight is not None:
            return await inflight

        task = asyncio.create_task(self._fetch_records(url, dataset, where, limit, order_by))
        self._inflight_records[url] = task
        try:
            return await task
        finally:
            self._inflight_records.pop(url, None)

    async def get_realtime_feed(self, dataset: str) -> gtfs_realtime_pb2.FeedMessage | None:
        cache_key = f"realtime:{dataset}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        inflight = self._inflight_realtime.get(cache_key)
        if inflight is not None:
            return await inflight

        task = asyncio.create_task(self._fetch_realtime_feed(dataset, cache_key))
        self._inflight_realtime[cache_key] = task
        try:
            return await task
        finally:
            self._inflight_realtime.pop(cache_key, None)

    async def _fetch_records(
        self,
        url: str,
        dataset: str,
        where: str | None,
        limit: int,
        order_by: str | None,
    ) -> list[dict[str, Any]]:
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
            data = await self._get_json_with_retry(page_url)
            page_results = data.get("results", [])
            total_count = data.get("total_count", total_count)
            results.extend(page_results)

            if not page_results or (total_count is not None and len(results) >= total_count):
                break
            offset += page_size

        results = results[:limit]
        self.cache.set(url, results)
        return results

    async def _fetch_realtime_feed(self, dataset: str, cache_key: str) -> gtfs_realtime_pb2.FeedMessage | None:
        records = await self.get_records(dataset, limit=1)
        file_url = records[0].get("file", {}).get("url") if records else None
        if not file_url:
            logger.warning("Realtime dataset %s did not expose a file URL", dataset)
            self.cache.set(cache_key, None)
            return None

        logger.info("Fetching FGC realtime protobuf dataset=%s", dataset)
        response = await self._request_with_retry(file_url)
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        self.cache.set(cache_key, feed)
        return feed

    async def _get_json_with_retry(self, url: str) -> dict[str, Any]:
        response = await self._request_with_retry(url)
        return json.loads(response.content.decode("utf-8"))

    async def _request_with_retry(self, url: str) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                    break
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt == 2:
                    break
            await asyncio.sleep(0.75 * (attempt + 1))
        assert last_error is not None
        raise last_error

    def get_stale_records(
        self,
        dataset: str,
        *,
        where: str | None = None,
        limit: int | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]] | None:
        limit = limit or self.settings.source_records_limit
        params = [f"limit={limit}"]
        if where:
            params.append(f"where={quote(where)}")
        if order_by:
            params.append(f"order_by={quote(order_by)}")
        url = f"{self.settings.api_base_url.rstrip('/')}/{dataset}/records?{'&'.join(params)}"
        return self.cache.get(url, allow_stale=True)

    async def ping(self) -> None:
        probe_origin = self.settings.configured_train_routes[0][0]
        await self.get_records(self.settings.schedules_dataset, where=f'stop_name like "{probe_origin}"', limit=1)
