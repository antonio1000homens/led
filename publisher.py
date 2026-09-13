"""Scheduled AWS publisher for the renderer-neutral LED screen contract."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from typing import Any

from queue_times import QueueTimesProvider
from server import DEFAULT_THORPE_PARK_RIDES, NationalRailProvider, _queue_screen_duration, _select_rides
from todoist import DEFAULT_FILTER_QUERY, DEFAULT_TIMEZONE, TodoistProvider
from weather import OpenMeteoProvider


STATE_KEY = "state/feed-cache.json"
SCREENS_KEY = "api/screens"
DEFAULT_WEATHER_LATITUDE = 51.4039
DEFAULT_WEATHER_LONGITUDE = -0.256


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _env_int(env: dict[str, str], name: str, default: int, minimum: int = 1) -> int:
    value = int(env.get(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _env_float(env: dict[str, str], name: str, default: float, low: float, high: float) -> float:
    value = float(env.get(name, str(default)))
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


class PublisherConfig:
    def __init__(
        self,
        bucket: str,
        national_rail_token: str,
        station: str = "NEM",
        max_rows: int = 10,
        rail_ttl: int = 60,
        thorpe_park_source: str = "queue_times",
        thorpe_park_ttl: int = 300,
        thorpe_park_rides: tuple[str, ...] = DEFAULT_THORPE_PARK_RIDES,
        weather_source: str = "open_meteo",
        weather_ttl: int = 600,
        weather_latitude: float = DEFAULT_WEATHER_LATITUDE,
        weather_longitude: float = DEFAULT_WEATHER_LONGITUDE,
        calendar_source: str = "off",
        todoist_token: str = "",
        calendar_ttl: int = 300,
        calendar_max_events: int = 6,
        calendar_filter_query: str = DEFAULT_FILTER_QUERY,
        calendar_timezone: str = DEFAULT_TIMEZONE,
        calendar_duration: int = 10,
        calendar_page_seconds: int = 5,
    ):
        self.bucket = bucket
        self.national_rail_token = national_rail_token
        self.station = station
        self.max_rows = max_rows
        self.rail_ttl = rail_ttl
        self.thorpe_park_source = thorpe_park_source
        self.thorpe_park_ttl = thorpe_park_ttl
        self.thorpe_park_rides = thorpe_park_rides
        self.weather_source = weather_source
        self.weather_ttl = weather_ttl
        self.weather_latitude = weather_latitude
        self.weather_longitude = weather_longitude
        self.calendar_source = calendar_source
        self.todoist_token = todoist_token
        self.calendar_ttl = calendar_ttl
        self.calendar_max_events = calendar_max_events
        self.calendar_filter_query = calendar_filter_query
        self.calendar_timezone = calendar_timezone
        self.calendar_duration = calendar_duration
        self.calendar_page_seconds = calendar_page_seconds

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None):
        env = dict(os.environ if env is None else env)
        bucket = env.get("STATE_BUCKET", "").strip()
        token = env.get("NATIONAL_RAIL_TOKEN", "").strip()
        station = env.get("LED_STATION_CRS", "NEM").strip().upper()
        if not bucket:
            raise ValueError("STATE_BUCKET is required")
        if not token:
            raise ValueError("NATIONAL_RAIL_TOKEN is required")
        if len(station) != 3 or not station.isalpha():
            raise ValueError("LED_STATION_CRS must contain exactly three letters")
        max_rows = _env_int(env, "LED_MAX_ROWS", 10)
        if max_rows > 50:
            raise ValueError("LED_MAX_ROWS must be <= 50")
        thorpe_source = env.get("LED_THORPE_PARK_SOURCE", "queue_times").strip()
        if thorpe_source not in ("off", "queue_times"):
            raise ValueError("LED_THORPE_PARK_SOURCE must be off or queue_times")
        weather_source = env.get("LED_WEATHER_SOURCE", "open_meteo").strip()
        if weather_source not in ("off", "open_meteo"):
            raise ValueError("LED_WEATHER_SOURCE must be off or open_meteo")
        calendar_source = env.get("LED_CALENDAR_SOURCE", "off").strip()
        if calendar_source not in ("off", "todoist"):
            raise ValueError("LED_CALENDAR_SOURCE must be off or todoist")
        todoist_token = env.get("TODOIST_TOKEN", "").strip()
        if calendar_source == "todoist" and not todoist_token:
            raise ValueError("TODOIST_TOKEN is required when LED_CALENDAR_SOURCE=todoist")
        rides = tuple(
            item.strip()
            for item in env.get("LED_THORPE_PARK_RIDES", ",".join(DEFAULT_THORPE_PARK_RIDES)).split(",")
            if item.strip()
        )
        if thorpe_source != "off" and not rides:
            raise ValueError("LED_THORPE_PARK_RIDES must contain at least one ride")
        calendar_max_events = _env_int(env, "LED_TODOIST_MAX_EVENTS", 6)
        if calendar_max_events > 20:
            raise ValueError("LED_TODOIST_MAX_EVENTS must be <= 20")
        calendar_duration = _env_int(env, "LED_CALENDAR_DURATION_SECONDS", 10)
        calendar_page_seconds = _env_int(env, "LED_CALENDAR_PAGE_SECONDS", 5)
        if calendar_page_seconds >= calendar_duration:
            raise ValueError("LED_CALENDAR_PAGE_SECONDS must be less than LED_CALENDAR_DURATION_SECONDS")
        return cls(
            bucket=bucket,
            national_rail_token=token,
            station=station,
            max_rows=max_rows,
            rail_ttl=_env_int(env, "LED_CACHE_SECONDS", 60),
            thorpe_park_source=thorpe_source,
            thorpe_park_ttl=_env_int(env, "LED_THORPE_PARK_CACHE_SECONDS", 300),
            thorpe_park_rides=rides,
            weather_source=weather_source,
            weather_ttl=_env_int(env, "LED_WEATHER_CACHE_SECONDS", 600),
            weather_latitude=_env_float(env, "LED_WEATHER_LATITUDE", DEFAULT_WEATHER_LATITUDE, -90, 90),
            weather_longitude=_env_float(env, "LED_WEATHER_LONGITUDE", DEFAULT_WEATHER_LONGITUDE, -180, 180),
            calendar_source=calendar_source,
            todoist_token=todoist_token,
            calendar_ttl=_env_int(env, "LED_TODOIST_CACHE_SECONDS", 300),
            calendar_max_events=calendar_max_events,
            calendar_filter_query=env.get("LED_TODOIST_FILTER_QUERY", DEFAULT_FILTER_QUERY).strip() or DEFAULT_FILTER_QUERY,
            calendar_timezone=env.get("LED_TODOIST_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE,
            calendar_duration=calendar_duration,
            calendar_page_seconds=calendar_page_seconds,
        )


class S3StateStore:
    """Persist feed state and publish the complete screen snapshot to S3."""

    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3

            client = boto3.client("s3")
        self.client = client

    def load(self) -> dict[str, Any]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=STATE_KEY)
        except Exception as error:
            response_meta = getattr(error, "response", {}) or {}
            code = str((response_meta.get("Error") or {}).get("Code") or "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return {"version": 1, "feeds": {}}
            raise
        payload = json.loads(response["Body"].read().decode("utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("feeds"), dict):
            return {"version": 1, "feeds": {}}
        return payload

    def save(self, state: dict[str, Any]) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=STATE_KEY,
            Body=json.dumps(state, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-store",
            ServerSideEncryption="AES256",
        )

    def publish(self, payload: dict[str, Any]) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=SCREENS_KEY,
            Body=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-store, max-age=0",
            ServerSideEncryption="AES256",
        )


class Publisher:
    def __init__(
        self,
        config: PublisherConfig,
        store,
        rail_provider=None,
        queue_provider=None,
        weather_provider=None,
        utcnow=None,
        calendar_provider=None,
    ):
        self.config = config
        self.store = store
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.rail_provider = rail_provider or NationalRailProvider(
            config.national_rail_token,
            config.station,
            config.max_rows,
        )
        self.queue_provider = queue_provider
        if self.queue_provider is None and config.thorpe_park_source == "queue_times":
            self.queue_provider = QueueTimesProvider()
        self.weather_provider = weather_provider
        if self.weather_provider is None and config.weather_source == "open_meteo":
            self.weather_provider = OpenMeteoProvider(config.weather_latitude, config.weather_longitude)
        self.calendar_provider = calendar_provider
        if self.calendar_provider is None and config.calendar_source == "todoist":
            self.calendar_provider = TodoistProvider(
                config.todoist_token,
                filter_query=config.calendar_filter_query,
                timezone_name=config.calendar_timezone,
                max_events=config.calendar_max_events,
                utcnow=self.utcnow,
            )

    def _due(self, previous: dict[str, Any] | None, ttl: int, now: datetime) -> bool:
        if not previous or previous.get("data") is None:
            return True
        last_attempt = _parse_iso(previous.get("last_attempt_at"))
        if last_attempt is None:
            return True
        return (now - last_attempt).total_seconds() >= ttl

    def _refresh(self, name: str, previous: dict[str, Any] | None, ttl: int, fetcher, now: datetime):
        previous = copy.deepcopy(previous or {})
        if not self._due(previous, ttl, now):
            return previous
        attempted_at = _iso(now)
        try:
            data = fetcher()
        except Exception:
            had_cache = previous.get("data") is not None
            print(json.dumps({"event": "feed_refresh_failed", "feed": name, "had_cache": had_cache}))
            if had_cache:
                previous["last_attempt_at"] = attempted_at
                previous["stale"] = True
                return previous
            return {
                "last_attempt_at": attempted_at,
                "last_success_at": None,
                "stale": True,
                "data": None,
            }
        return {
            "last_attempt_at": attempted_at,
            "last_success_at": attempted_at,
            "stale": False,
            "data": data,
        }

    def _fetch_rail(self, now: datetime):
        return {
            "station": self.config.station,
            "source": "national_rail",
            "fetched_at": _iso(now),
            "services": self.rail_provider.fetch(),
        }

    def _fetch_queues(self, now: datetime):
        return {
            "park": "Thorpe Park",
            "source": "queue_times",
            "fetched_at": _iso(now),
            "rides": self.queue_provider.fetch(),
        }

    def _fetch_calendar(self, now: datetime):
        return {
            "source": "todoist",
            "fetched_at": _iso(now),
            "events": self.calendar_provider.fetch(),
        }

    def _fetch_weather(self, now: datetime):
        weather = self.weather_provider.fetch()
        result = {"source": "open_meteo", "fetched_at": _iso(now)}
        result.update(weather)
        return result

    def _screens(self, feeds: dict[str, Any], now: datetime) -> dict[str, Any]:
        screens = []
        rail = feeds.get("rail") or {}
        rail_data = rail.get("data")
        if rail_data is None:
            screens.append({
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "title": "Departures unavailable",
                "source": "unavailable",
                "stale": True,
                "services": [],
            })
        else:
            screens.append({
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "title": f"{rail_data['station']} departures",
                "source": rail_data.get("source", "national_rail"),
                "stale": bool(rail.get("stale")),
                "services": copy.deepcopy((rail_data.get("services") or [])[:3]),
            })

        if self.config.thorpe_park_source != "off":
            queues = feeds.get("queues") or {}
            queue_data = queues.get("data")
            if queue_data is None:
                screens.append({
                    "id": "thorpe-park",
                    "kind": "theme_park_queues",
                    "duration_seconds": 8,
                    "title": "THORPE PARK · queues unavailable",
                    "source": "unavailable",
                    "stale": True,
                    "rides": [],
                    "attribution": "Powered by Queue-Times.com",
                })
            else:
                rides = _select_rides(queue_data.get("rides") or [], self.config.thorpe_park_rides)
                screens.append({
                    "id": "thorpe-park",
                    "kind": "theme_park_queues",
                    "duration_seconds": _queue_screen_duration(len(rides)),
                    "title": "THORPE PARK · Powered by Queue-Times.com",
                    "source": queue_data.get("source", "queue_times"),
                    "stale": bool(queues.get("stale")),
                    "rides": copy.deepcopy(rides),
                    "attribution": "Powered by Queue-Times.com",
                })

        if self.config.calendar_source != "off":
            calendar = feeds.get("calendar") or {}
            calendar_data = calendar.get("data")
            if calendar_data is None:
                screens.append({
                    "id": "calendar",
                    "kind": "calendar_agenda",
                    "duration_seconds": self.config.calendar_duration,
                    "title": "Calendar unavailable",
                    "source": "unavailable",
                    "stale": True,
                    "viewport_size": 3,
                    "page_seconds": self.config.calendar_page_seconds,
                    "events": [],
                })
            else:
                screens.append({
                    "id": "calendar",
                    "kind": "calendar_agenda",
                    "duration_seconds": self.config.calendar_duration,
                    "title": "UPCOMING",
                    "source": calendar_data.get("source", "todoist"),
                    "stale": bool(calendar.get("stale")),
                    "viewport_size": 3,
                    "page_seconds": self.config.calendar_page_seconds,
                    "events": copy.deepcopy((calendar_data.get("events") or [])[: self.config.calendar_max_events]),
                })

        if self.config.weather_source != "off":
            weather = feeds.get("weather") or {}
            weather_data = weather.get("data")
            if weather_data is None:
                overlay = {
                    "source": "unavailable",
                    "stale": True,
                    "temperature_c": None,
                    "weather_code": None,
                    "icon": "unknown",
                }
            else:
                overlay = copy.deepcopy(weather_data)
                overlay["stale"] = bool(weather.get("stale"))
            for screen in screens:
                screen["weather"] = copy.deepcopy(overlay)

        return {"fetched_at": _iso(now), "screens": screens}

    def run(self) -> dict[str, Any]:
        now = self.utcnow()
        state = self.store.load()
        feeds = copy.deepcopy(state.get("feeds") or {})

        feeds["rail"] = self._refresh(
            "rail", feeds.get("rail"), self.config.rail_ttl, lambda: self._fetch_rail(now), now
        )
        if self.config.thorpe_park_source != "off":
            feeds["queues"] = self._refresh(
                "queues", feeds.get("queues"), self.config.thorpe_park_ttl, lambda: self._fetch_queues(now), now
            )
        else:
            feeds.pop("queues", None)
        if self.config.calendar_source != "off":
            feeds["calendar"] = self._refresh(
                "calendar", feeds.get("calendar"), self.config.calendar_ttl, lambda: self._fetch_calendar(now), now
            )
        else:
            feeds.pop("calendar", None)
        if self.config.weather_source != "off":
            feeds["weather"] = self._refresh(
                "weather", feeds.get("weather"), self.config.weather_ttl, lambda: self._fetch_weather(now), now
            )
        else:
            feeds.pop("weather", None)

        next_state = {"version": 1, "updated_at": _iso(now), "feeds": feeds}
        payload = self._screens(feeds, now)
        self.store.save(next_state)
        self.store.publish(payload)
        print(json.dumps({"event": "screens_published", "screens": len(payload["screens"])}))
        return payload


_PUBLISHER = None


def lambda_handler(event, context):
    del event, context
    global _PUBLISHER
    if _PUBLISHER is None:
        config = PublisherConfig.from_env()
        _PUBLISHER = Publisher(config, S3StateStore(config.bucket))
    payload = _PUBLISHER.run()
    return {"published": True, "screen_count": len(payload.get("screens") or [])}
