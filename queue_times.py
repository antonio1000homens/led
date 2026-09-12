"""Queue-Times.com adapter and cache for Thorpe Park waits."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import threading
import time
from urllib.request import Request, urlopen


QUEUE_TIMES_PARK_URL = "https://queue-times.com/parks/{}/queue_times.json"
DEFAULT_THORPE_PARK_ID = 2


class QueueFeedUnavailable(RuntimeError):
    """No theme-park queue data is currently available."""


def normalize_queue_times(payload):
    """Flatten Queue-Times lands/top-level rides into a stable ride model."""
    rides = []
    seen = set()

    containers = []
    if isinstance(payload, dict):
        top_level = payload.get("rides") or []
        if isinstance(top_level, list):
            containers.append((None, top_level))
        for land in payload.get("lands") or []:
            if not isinstance(land, dict):
                continue
            land_rides = land.get("rides") or []
            if isinstance(land_rides, list):
                containers.append((str(land.get("name") or ""), land_rides))

    for land_name, raw_rides in containers:
        for ride in raw_rides:
            if not isinstance(ride, dict):
                continue
            name = str(ride.get("name") or "").strip()
            if not name:
                continue
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            try:
                wait_minutes = max(0, int(ride.get("wait_time") or 0))
            except (TypeError, ValueError):
                wait_minutes = 0
            rides.append(
                {
                    "name": name,
                    "open": bool(ride.get("is_open")),
                    "wait_minutes": wait_minutes,
                    "last_updated": str(ride.get("last_updated") or ""),
                    "land": land_name or "",
                }
            )
    return rides


class QueueTimesProvider:
    source = "queue_times"

    def __init__(self, park_id=DEFAULT_THORPE_PARK_ID, timeout=10, opener=None):
        self.park_id = int(park_id)
        self.timeout = timeout
        self.opener = opener or urlopen

    def fetch(self):
        request = Request(
            QUEUE_TIMES_PARK_URL.format(self.park_id),
            headers={
                "Accept": "application/json",
                "User-Agent": "antonio1000homens-led/1.0 (+https://github.com/antonio1000homens/led)",
            },
        )
        with self.opener(request, timeout=self.timeout) as response:
            payload = json.load(response)
        rides = normalize_queue_times(payload)
        if not rides:
            raise RuntimeError("Queue-Times returned no rides")
        return rides


class ThorpeParkFeed:
    """Cache Thorpe Park waits and fall back to the last successful response."""

    def __init__(self, provider, cache_seconds=300, monotonic=None, utcnow=None):
        self.provider = provider
        self.cache_seconds = cache_seconds
        self.monotonic = monotonic or time.monotonic
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self._payload = None
        self._last_attempt = None
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            now = self.monotonic()
            if (
                self._payload is not None
                and self._last_attempt is not None
                and now - self._last_attempt < self.cache_seconds
            ):
                return copy.deepcopy(self._payload)

            self._last_attempt = now
            try:
                rides = self.provider.fetch()
            except Exception as error:
                if self._payload is None:
                    raise QueueFeedUnavailable("Thorpe Park queue data is unavailable") from error
                self._payload["stale"] = True
                return copy.deepcopy(self._payload)

            self._payload = {
                "park": "Thorpe Park",
                "source": self.provider.source,
                "fetched_at": self.utcnow().isoformat().replace("+00:00", "Z"),
                "stale": False,
                "rides": rides,
            }
            return copy.deepcopy(self._payload)
