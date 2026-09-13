"""Scheduled AWS publisher for the renderer-neutral LED screen contract."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from typing import Any

from config_api import DEFAULT_DISPLAY_CONFIG, validate_config
from queue_times import QueueTimesProvider
from server import DEFAULT_THORPE_PARK_RIDES, NationalRailProvider, _select_rides
from todoist import DEFAULT_FILTER_QUERY, DEFAULT_TIMEZONE, SecretsManagerOAuthStore, TodoistOAuthSession, TodoistProvider
from weather import OpenMeteoProvider

STATE_KEY = "state/feed-cache.json"
CONFIG_KEY = "state/config.json"
SCREENS_KEY = "api/screens"
DEFAULT_WEATHER_LATITUDE = 51.4039
DEFAULT_WEATHER_LONGITUDE = -0.256
CHESSINGTON_PARK_ID = 3


def _iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _env_int(env, name, default, minimum=1):
    value = int(env.get(name, str(default)))
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def _env_float(env, name, default, low, high):
    value = float(env.get(name, str(default)))
    if not low <= value <= high:
        raise ValueError(f"{name} must be between {low} and {high}")
    return value


class PublisherConfig:
    def __init__(self, bucket, national_rail_token, station="NEM", max_rows=10, rail_ttl=60,
                 thorpe_park_source="queue_times", thorpe_park_ttl=300,
                 thorpe_park_rides=DEFAULT_THORPE_PARK_RIDES, weather_source="open_meteo",
                 weather_ttl=600, weather_latitude=DEFAULT_WEATHER_LATITUDE,
                 weather_longitude=DEFAULT_WEATHER_LONGITUDE, calendar_source="off",
                 todoist_oauth_secret_arn="", calendar_ttl=300, calendar_max_events=6,
                 calendar_filter_query=DEFAULT_FILTER_QUERY, calendar_timezone=DEFAULT_TIMEZONE,
                 calendar_duration=10, calendar_page_seconds=5):
        self.bucket = bucket
        self.national_rail_token = national_rail_token
        self.station = station
        self.max_rows = max_rows
        self.rail_ttl = rail_ttl
        self.thorpe_park_source = thorpe_park_source
        self.thorpe_park_ttl = thorpe_park_ttl
        self.thorpe_park_rides = tuple(thorpe_park_rides)
        self.weather_source = weather_source
        self.weather_ttl = weather_ttl
        self.weather_latitude = weather_latitude
        self.weather_longitude = weather_longitude
        self.calendar_source = calendar_source
        self.todoist_oauth_secret_arn = todoist_oauth_secret_arn
        self.calendar_ttl = calendar_ttl
        self.calendar_max_events = calendar_max_events
        self.calendar_filter_query = calendar_filter_query
        self.calendar_timezone = calendar_timezone
        self.calendar_duration = calendar_duration
        self.calendar_page_seconds = calendar_page_seconds

    @classmethod
    def from_env(cls, env=None):
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
        todoist_secret = env.get("TODOIST_OAUTH_SECRET_ARN", "").strip()
        if calendar_source == "todoist" and not todoist_secret:
            raise ValueError("TODOIST_OAUTH_SECRET_ARN is required when LED_CALENDAR_SOURCE=todoist")
        rides = tuple(x.strip() for x in env.get("LED_THORPE_PARK_RIDES", ",".join(DEFAULT_THORPE_PARK_RIDES)).split(",") if x.strip())
        calendar_max_events = _env_int(env, "LED_TODOIST_MAX_EVENTS", 6)
        calendar_duration = _env_int(env, "LED_CALENDAR_DURATION_SECONDS", 10)
        calendar_page_seconds = _env_int(env, "LED_CALENDAR_PAGE_SECONDS", 5)
        if calendar_page_seconds >= calendar_duration:
            raise ValueError("LED_CALENDAR_PAGE_SECONDS must be less than LED_CALENDAR_DURATION_SECONDS")
        return cls(bucket, token, station, max_rows, _env_int(env, "LED_CACHE_SECONDS", 60),
                   thorpe_source, _env_int(env, "LED_THORPE_PARK_CACHE_SECONDS", 300), rides,
                   weather_source, _env_int(env, "LED_WEATHER_CACHE_SECONDS", 600),
                   _env_float(env, "LED_WEATHER_LATITUDE", DEFAULT_WEATHER_LATITUDE, -90, 90),
                   _env_float(env, "LED_WEATHER_LONGITUDE", DEFAULT_WEATHER_LONGITUDE, -180, 180),
                   calendar_source, todoist_secret, _env_int(env, "LED_TODOIST_CACHE_SECONDS", 300),
                   calendar_max_events, env.get("LED_TODOIST_FILTER_QUERY", DEFAULT_FILTER_QUERY).strip() or DEFAULT_FILTER_QUERY,
                   env.get("LED_TODOIST_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE,
                   calendar_duration, calendar_page_seconds)


class S3StateStore:
    def __init__(self, bucket, client=None):
        self.bucket = bucket
        if client is None:
            import boto3
            client = boto3.client("s3")
        self.client = client

    def _get_json(self, key, default):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            meta = getattr(error, "response", {}) or {}
            if str((meta.get("Error") or {}).get("Code") or "") in ("NoSuchKey", "404", "NotFound"):
                return copy.deepcopy(default)
            raise
        return json.loads(response["Body"].read().decode("utf-8"))

    def load(self):
        payload = self._get_json(STATE_KEY, {"version": 1, "feeds": {}})
        return payload if isinstance(payload, dict) and isinstance(payload.get("feeds"), dict) else {"version": 1, "feeds": {}}

    def load_config(self):
        try:
            return validate_config(self._get_json(CONFIG_KEY, DEFAULT_DISPLAY_CONFIG))
        except ValueError:
            print(json.dumps({"event": "invalid_display_config", "fallback": "defaults"}))
            return copy.deepcopy(DEFAULT_DISPLAY_CONFIG)

    def save(self, state):
        self.client.put_object(Bucket=self.bucket, Key=STATE_KEY, Body=json.dumps(state, separators=(",", ":")).encode(),
                               ContentType="application/json", CacheControl="no-store", ServerSideEncryption="AES256")

    def publish(self, payload):
        self.client.put_object(Bucket=self.bucket, Key=SCREENS_KEY, Body=json.dumps(payload, separators=(",", ":")).encode(),
                               ContentType="application/json", CacheControl="no-store, max-age=0", ServerSideEncryption="AES256")


class Publisher:
    def __init__(self, config, store, rail_provider=None, queue_provider=None, weather_provider=None, utcnow=None,
                 calendar_provider=None, chessington_provider=None):
        self.config = config
        self.store = store
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.rail_provider = rail_provider or NationalRailProvider(config.national_rail_token, config.station, config.max_rows)
        self.queue_provider = queue_provider
        if self.queue_provider is None and config.thorpe_park_source == "queue_times":
            self.queue_provider = QueueTimesProvider(2)
        self.chessington_provider = chessington_provider
        if self.chessington_provider is None and config.thorpe_park_source == "queue_times":
            self.chessington_provider = QueueTimesProvider(CHESSINGTON_PARK_ID)
        self.weather_provider = weather_provider
        if self.weather_provider is None and config.weather_source == "open_meteo":
            self.weather_provider = OpenMeteoProvider(config.weather_latitude, config.weather_longitude)
        self.calendar_provider = calendar_provider
        if self.calendar_provider is None and config.calendar_source == "todoist":
            oauth = TodoistOAuthSession(SecretsManagerOAuthStore(config.todoist_oauth_secret_arn))
            self.calendar_provider = TodoistProvider(oauth, filter_query=config.calendar_filter_query,
                                                     timezone_name=config.calendar_timezone,
                                                     max_events=config.calendar_max_events, utcnow=self.utcnow)

    def _due(self, previous, ttl, now):
        if not previous or previous.get("data") is None:
            return True
        last = _parse_iso(previous.get("last_attempt_at"))
        return last is None or (now - last).total_seconds() >= ttl

    def _refresh(self, name, previous, ttl, fetcher, now):
        previous = copy.deepcopy(previous or {})
        if not self._due(previous, ttl, now):
            return previous
        attempted = _iso(now)
        try:
            data = fetcher()
        except Exception:
            had_cache = previous.get("data") is not None
            print(json.dumps({"event": "feed_refresh_failed", "feed": name, "had_cache": had_cache}))
            if had_cache:
                previous.update(last_attempt_at=attempted, stale=True)
                return previous
            return {"last_attempt_at": attempted, "last_success_at": None, "stale": True, "data": None}
        return {"last_attempt_at": attempted, "last_success_at": attempted, "stale": False, "data": data}

    def _fetch_rail(self, now):
        return {"station": self.config.station, "source": "national_rail", "fetched_at": _iso(now), "services": self.rail_provider.fetch()}

    def _fetch_queues(self, now, provider, park):
        return {"park": park, "source": "queue_times", "fetched_at": _iso(now), "rides": provider.fetch()}

    def _fetch_calendar(self, now):
        return {"source": "todoist", "fetched_at": _iso(now), "events": self.calendar_provider.fetch()}

    def _fetch_weather(self, now):
        result = {"source": "open_meteo", "fetched_at": _iso(now)}
        result.update(self.weather_provider.fetch())
        return result

    @staticmethod
    def _park_screen(screen_id, title, feed, park_config, selected_names=None):
        data = feed.get("data") if feed else None
        entries = park_config["entriesPerPage"]
        page_seconds = park_config["pageDurationSeconds"]
        iterations = park_config["iterations"]
        if data is None:
            rides = []
            source = "unavailable"
            stale = True
        else:
            all_rides = data.get("rides") or []
            rides = _select_rides(all_rides, selected_names) if selected_names else all_rides
            source = data.get("source", "queue_times")
            stale = bool(feed.get("stale"))
            if rides and not any(bool(ride.get("open")) for ride in rides):
                return None
        page_count = max(1, (len(rides) + entries - 1) // entries)
        return {
            "id": screen_id,
            "kind": "theme_park_queues",
            "duration_seconds": page_count * page_seconds * iterations,
            "title": title + " · Powered by Queue-Times.com",
            "source": source,
            "stale": stale,
            "rides": copy.deepcopy(rides),
            "entries_per_page": entries,
            "page_seconds": page_seconds,
            "iterations": iterations,
            "attribution": "Powered by Queue-Times.com",
        }

    def _screens(self, feeds, now, display_config):
        screens = []
        rail = feeds.get("rail") or {}
        rail_data = rail.get("data")
        screens.append({"id": "departures", "kind": "rail_combined", "duration_seconds": 8,
                        "title": f"{rail_data['station']} departures" if rail_data else "Departures unavailable",
                        "source": rail_data.get("source", "national_rail") if rail_data else "unavailable",
                        "stale": bool(rail.get("stale")) if rail_data else True,
                        "services": copy.deepcopy((rail_data.get("services") or [])[:2]) if rail_data else []})
        parks = display_config["themeParks"]
        if self.config.thorpe_park_source != "off" and parks["thorpePark"]["enabled"]:
            park_screen = self._park_screen("thorpe-park", "THORPE PARK", feeds.get("thorpePark") or {},
                                            parks["thorpePark"], self.config.thorpe_park_rides)
            if park_screen is not None:
                screens.append(park_screen)
        if self.config.thorpe_park_source != "off" and parks["chessington"]["enabled"]:
            park_screen = self._park_screen("chessington", "CHESSINGTON", feeds.get("chessington") or {}, parks["chessington"])
            if park_screen is not None:
                screens.append(park_screen)
        if self.config.calendar_source != "off":
            calendar = feeds.get("calendar") or {}; data = calendar.get("data")
            screens.append({"id": "calendar", "kind": "calendar_agenda", "duration_seconds": self.config.calendar_duration,
                            "title": "UPCOMING" if data is not None else "Calendar unavailable",
                            "source": data.get("source", "todoist") if data is not None else "unavailable",
                            "stale": bool(calendar.get("stale")) if data is not None else True,
                            "viewport_size": 3, "page_seconds": self.config.calendar_page_seconds,
                            "events": copy.deepcopy((data.get("events") or [])[:self.config.calendar_max_events]) if data is not None else []})
        if self.config.weather_source != "off":
            weather = feeds.get("weather") or {}; data = weather.get("data")
            overlay = copy.deepcopy(data) if data is not None else {"source": "unavailable", "temperature_c": None, "weather_code": None, "icon": "unknown"}
            overlay["stale"] = bool(weather.get("stale")) if data is not None else True
            for screen in screens:
                screen["weather"] = copy.deepcopy(overlay)
        return {"fetched_at": _iso(now), "screens": screens}

    def run(self):
        now = self.utcnow()
        state = self.store.load()
        load_config = getattr(self.store, "load_config", None)
        display_config = validate_config(load_config()) if load_config else copy.deepcopy(DEFAULT_DISPLAY_CONFIG)
        feeds = copy.deepcopy(state.get("feeds") or {})
        feeds["rail"] = self._refresh("rail", feeds.get("rail"), self.config.rail_ttl, lambda: self._fetch_rail(now), now)
        parks = display_config["themeParks"]
        if self.config.thorpe_park_source != "off" and parks["thorpePark"]["enabled"]:
            feeds["thorpePark"] = self._refresh("thorpePark", feeds.get("thorpePark") or feeds.get("queues"), self.config.thorpe_park_ttl,
                                                lambda: self._fetch_queues(now, self.queue_provider, "Thorpe Park"), now)
        if self.config.thorpe_park_source != "off" and parks["chessington"]["enabled"]:
            feeds["chessington"] = self._refresh("chessington", feeds.get("chessington"), self.config.thorpe_park_ttl,
                                                  lambda: self._fetch_queues(now, self.chessington_provider, "Chessington World of Adventures"), now)
        feeds.pop("queues", None)
        if self.config.calendar_source != "off":
            feeds["calendar"] = self._refresh("calendar", feeds.get("calendar"), self.config.calendar_ttl, lambda: self._fetch_calendar(now), now)
        else:
            feeds.pop("calendar", None)
        if self.config.weather_source != "off":
            feeds["weather"] = self._refresh("weather", feeds.get("weather"), self.config.weather_ttl, lambda: self._fetch_weather(now), now)
        else:
            feeds.pop("weather", None)
        next_state = {"version": 1, "updated_at": _iso(now), "feeds": feeds}
        payload = self._screens(feeds, now, display_config)
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
