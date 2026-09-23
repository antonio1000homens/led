"""Scheduled AWS publisher for the renderer-neutral LED screen contract."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from zoneinfo import ZoneInfo

from queue_times import QueueTimesProvider, select_rides
from runtime_config import (
    DEFAULT_CHESSINGTON_RIDES,
    DEFAULT_UPCOMING_TRAIN_COUNT,
    FEED_REGISTRY,
    LEGACY_DEFAULT_CHESSINGTON_RIDES,
    RuntimeConfigStore,
    default_runtime_config,
    validate_runtime_config,
)
from server import DEFAULT_THORPE_PARK_RIDES, NationalRailProvider
from todoist import DEFAULT_FILTER_QUERY, DEFAULT_TIMEZONE, SecretsManagerOAuthStore, TodoistOAuthSession, TodoistProvider
from weather import OpenMeteoProvider
from formatting import todoist_effective_duration

STATE_KEY = "state/feed-cache.json"
SCREENS_KEY = "api/screens"
DEFAULT_WEATHER_LATITUDE = 51.4039
DEFAULT_WEATHER_LONGITUDE = -0.256


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
    """Deployment configuration: provider wiring/secrets and runtime-default seeds."""

    def __init__(self, bucket, national_rail_token, station="NEM", max_rows=10, rail_ttl=60,
                 thorpe_park_source="queue_times", thorpe_park_ttl=300,
                 thorpe_park_rides=DEFAULT_THORPE_PARK_RIDES, weather_source="open_meteo",
                 weather_ttl=600, weather_latitude=DEFAULT_WEATHER_LATITUDE,
                 weather_longitude=DEFAULT_WEATHER_LONGITUDE, calendar_source="off",
                 todoist_oauth_secret_arn="", calendar_ttl=300, calendar_max_events=6,
                 calendar_filter_query=DEFAULT_FILTER_QUERY, calendar_timezone=DEFAULT_TIMEZONE,
                 calendar_duration=10, calendar_page_seconds=5, runtime_config_table="",
                 chessington_ttl=300, chessington_rides=DEFAULT_CHESSINGTON_RIDES):
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
        self.runtime_config_table = runtime_config_table
        self.chessington_ttl = chessington_ttl
        self.chessington_rides = tuple(chessington_rides)

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
        chessington_rides = tuple(x.strip() for x in env.get("LED_CHESSINGTON_RIDES", ",".join(DEFAULT_CHESSINGTON_RIDES)).split(",") if x.strip())
        calendar_max_events = _env_int(env, "LED_TODOIST_MAX_EVENTS", 6)
        calendar_duration = _env_int(env, "LED_CALENDAR_DURATION_SECONDS", 10)
        calendar_page_seconds = _env_int(env, "LED_CALENDAR_PAGE_SECONDS", 5)
        if calendar_page_seconds >= calendar_duration:
            raise ValueError("LED_CALENDAR_PAGE_SECONDS must be less than LED_CALENDAR_DURATION_SECONDS")
        return cls(
            bucket, token, station, max_rows, _env_int(env, "LED_CACHE_SECONDS", 60),
            thorpe_source, _env_int(env, "LED_THORPE_PARK_CACHE_SECONDS", 300), rides,
            weather_source, _env_int(env, "LED_WEATHER_CACHE_SECONDS", 600),
            _env_float(env, "LED_WEATHER_LATITUDE", DEFAULT_WEATHER_LATITUDE, -90, 90),
            _env_float(env, "LED_WEATHER_LONGITUDE", DEFAULT_WEATHER_LONGITUDE, -180, 180),
            calendar_source, todoist_secret, _env_int(env, "LED_TODOIST_CACHE_SECONDS", 300),
            calendar_max_events, env.get("LED_TODOIST_FILTER_QUERY", DEFAULT_FILTER_QUERY).strip() or DEFAULT_FILTER_QUERY,
            env.get("LED_TODOIST_TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE,
            calendar_duration, calendar_page_seconds, env.get("RUNTIME_CONFIG_TABLE", "").strip(),
            _env_int(env, "LED_CHESSINGTON_CACHE_SECONDS", 300), chessington_rides,
        )


def _runtime_defaults(config: PublisherConfig):
    env = {
        "LED_CACHE_SECONDS": str(config.rail_ttl),
        "LED_THORPE_PARK_SOURCE": config.thorpe_park_source,
        "LED_THORPE_PARK_CACHE_SECONDS": str(config.thorpe_park_ttl),
        "LED_THORPE_PARK_RIDES": ",".join(config.thorpe_park_rides),
        "LED_CHESSINGTON_CACHE_SECONDS": str(config.chessington_ttl),
        "LED_CHESSINGTON_RIDES": ",".join(config.chessington_rides),
        "LED_WEATHER_SOURCE": config.weather_source,
        "LED_WEATHER_CACHE_SECONDS": str(config.weather_ttl),
        "LED_CALENDAR_SOURCE": config.calendar_source,
        "LED_TODOIST_CACHE_SECONDS": str(config.calendar_ttl),
        "LED_CALENDAR_DURATION_SECONDS": str(config.calendar_duration),
    }
    return default_runtime_config(env)


class StaticRuntimeConfigStore:
    def __init__(self, config):
        self.config = copy.deepcopy(config)

    def load(self):
        return copy.deepcopy(self.config)


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
        payload = self._get_json(STATE_KEY, {"version": 2, "feeds": {}})
        return payload if isinstance(payload, dict) and isinstance(payload.get("feeds"), dict) else {"version": 2, "feeds": {}}

    def save(self, state):
        self.client.put_object(
            Bucket=self.bucket, Key=STATE_KEY,
            Body=json.dumps(state, separators=(",", ":")).encode(),
            ContentType="application/json", CacheControl="no-store", ServerSideEncryption="AES256",
        )

    def publish(self, payload):
        self.client.put_object(
            Bucket=self.bucket, Key=SCREENS_KEY,
            Body=json.dumps(payload, separators=(",", ":")).encode(),
            ContentType="application/json", CacheControl="no-store, max-age=0", ServerSideEncryption="AES256",
        )


class Publisher:
    def __init__(self, config, store, rail_provider=None, queue_provider=None, weather_provider=None, utcnow=None,
                 calendar_provider=None, chessington_provider=None, runtime_config_store=None):
        self.config = config
        self.store = store
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.runtime_config_store = runtime_config_store or StaticRuntimeConfigStore(_runtime_defaults(config))
        self.rail_provider = rail_provider or NationalRailProvider(config.national_rail_token, config.station, config.max_rows)
        self.queue_providers = {}
        for feed_id, definition in FEED_REGISTRY.items():
            if definition.get("provider") != "queue_times":
                continue
            if feed_id == "thorpe_park" and queue_provider is not None:
                provider = queue_provider
            elif feed_id == "chessington" and chessington_provider is not None:
                provider = chessington_provider
            else:
                provider = QueueTimesProvider(definition["park_id"])
            self.queue_providers[feed_id] = provider
        self.weather_provider = weather_provider or OpenMeteoProvider(config.weather_latitude, config.weather_longitude)
        self.calendar_provider = calendar_provider
        if self.calendar_provider is None and config.todoist_oauth_secret_arn:
            oauth = TodoistOAuthSession(SecretsManagerOAuthStore(config.todoist_oauth_secret_arn))
            self.calendar_provider = TodoistProvider(
                oauth,
                filter_query=config.calendar_filter_query,
                timezone_name=config.calendar_timezone,
                max_events=config.calendar_max_events,
                utcnow=self.utcnow,
            )

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
        if self.calendar_provider is None:
            raise RuntimeError("calendar provider is not configured")
        return {"source": "todoist", "fetched_at": _iso(now), "events": self.calendar_provider.fetch()}

    def _fetch_weather(self, now):
        result = {"source": "open_meteo", "fetched_at": _iso(now)}
        result.update(self.weather_provider.fetch())
        return result

    @staticmethod
    def _park_payload(feed_id, title, feed, runtime_feed):
        selected_names = runtime_feed.get("rides") or []
        if not selected_names:
            return None
        data = feed.get("data") if feed else None
        if data is None:
            rides = []
            source = "unavailable"
            stale = True
            missing = list(selected_names)
        else:
            rides, missing = select_rides(data.get("rides") or [], selected_names)
            source = data.get("source", "queue_times")
            stale = bool(feed.get("stale"))
            if rides and not any(bool(ride.get("open")) for ride in rides):
                return None
        if missing:
            print(json.dumps({"event": "configured_rides_missing", "feed": feed_id, "rides": missing}))
        return {
            "id": feed_id.replace("_", "-"),
            "feed_id": feed_id,
            "title": title,
            "source": source,
            "stale": stale,
            "rides": copy.deepcopy(rides),
            "missing_configured_rides": missing,
            "attribution": "Powered by Queue-Times.com",
        }

    def _screens(self, feeds, now, runtime):
        screens = []
        config_feeds = runtime["feeds"]
        departures_config = config_feeds["departures"]
        if departures_config["enabled"]:
            rail = feeds.get("departures") or {}
            rail_data = rail.get("data")
            services = copy.deepcopy((rail_data.get("services") or [])[:1 + departures_config["upcoming_train_count"]]) if rail_data else []
            for service in services:
                service["station_spacing_px"] = departures_config["station_list_spacing"]
            no_services = rail_data is not None and not services
            screens.append({
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": (
                    departures_config["no_services_duration_seconds"]
                    if no_services
                    else departures_config["screen_duration_seconds"]
                ),
                "station_scroll_speed": departures_config["station_scroll_speed"],
                "upcoming_train_count": departures_config["upcoming_train_count"],
                "upcoming_train_pause_seconds": departures_config["upcoming_train_pause_seconds"],
                "title": f"{rail_data['station']} departures" if rail_data else "Departures unavailable",
                "source": rail_data.get("source", "national_rail") if rail_data else "unavailable",
                "stale": bool(rail.get("stale")) if rail_data else True,
                "empty_state": "No Services" if no_services else None,
                "services": services,
            })

        queue_config = config_feeds["queue_times"]
        parks = []
        if queue_config["enabled"]:
            for feed_id, definition in FEED_REGISTRY.items():
                if definition.get("provider") != "queue_times":
                    continue
                park_config = config_feeds[feed_id]
                if not park_config["enabled"]:
                    continue
                title = "CHESSINGTON" if feed_id == "chessington" else definition["label"].upper()
                park = self._park_payload(feed_id, title, feeds.get(feed_id) or {}, park_config)
                if park is not None:
                    parks.append(park)
        if parks:
            screens.append({
                "id": "queue-times",
                "kind": "theme_park_queues",
                "duration_seconds": queue_config["screen_duration_seconds"],
                "title": "QUEUE TIMES",
                "source": "queue_times",
                "stale": False,
                "parks": parks,
                "queue_scroll_speed": queue_config["queue_scroll_speed"],
                "queue_scroll_pause_seconds": queue_config["queue_scroll_pause_seconds"],
                "splash_enabled": bool(queue_config["splash_enabled"]),
                "entries_per_page": 3,
                "attribution": "Powered by Queue-Times.com",
            })

        if config_feeds["calendar"]["enabled"]:
            calendar = feeds.get("calendar") or {}
            task_count = max(1, int(config_feeds["calendar"].get("visible_task_count", 6)))
            visible_rows = 3
            data = calendar.get("data")
            calendar_events = []
            if data is not None:
                calendar_events = data.get("events") or []
                if data.get("source") == "todoist":
                    calendar_events = copy.deepcopy(calendar_events[:min(self.config.calendar_max_events, task_count)])
                    local_date = now.astimezone(ZoneInfo(self.config.calendar_timezone)).date().isoformat()
                    duration_seconds = todoist_effective_duration(
                        config_feeds["calendar"]["screen_duration_seconds"],
                        calendar_events,
                        page_seconds=self.config.calendar_page_seconds,
                        current_date=local_date,
                        visible_rows=visible_rows,
                        step_rows=1,
                    )
                else:
                    duration_seconds = config_feeds["calendar"]["screen_duration_seconds"]
            else:
                duration_seconds = config_feeds["calendar"]["screen_duration_seconds"]
            screens.append({
                "id": "calendar", "kind": "calendar_agenda",
                "duration_seconds": duration_seconds,
                "title": "UPCOMING" if data is not None else "Calendar unavailable",
                "source": data.get("source", "todoist") if data is not None else "unavailable",
                "stale": bool(calendar.get("stale")) if data is not None else True,
                "viewport_size": visible_rows, "page_step": 1,
                "page_seconds": self.config.calendar_page_seconds,
                "events": copy.deepcopy(calendar_events[:task_count]),
            })
        if config_feeds["weather"]["enabled"]:
            weather = feeds.get("weather") or {}
            data = weather.get("data")
            overlay = copy.deepcopy(data) if data is not None else {
                "source": "unavailable", "temperature_c": None, "weather_code": None, "icon": "unknown"
            }
            overlay["stale"] = bool(weather.get("stale")) if data is not None else True
            for screen in screens:
                screen["weather"] = copy.deepcopy(overlay)
        return {
            "fetched_at": _iso(now),
            "config_version": runtime["config_version"],
            "flash": copy.deepcopy(config_feeds["flash"]),
            "screens": screens,
        }

    def _runtime(self):
        try:
            runtime = validate_runtime_config(self.runtime_config_store.load())
            if (
                runtime.get("updated_by") == "system:defaults"
                and runtime["feeds"]["chessington"].get("rides") == list(LEGACY_DEFAULT_CHESSINGTON_RIDES)
            ):
                runtime["feeds"]["chessington"]["rides"] = list(DEFAULT_CHESSINGTON_RIDES)
            return runtime
        except Exception:
            print(json.dumps({"event": "runtime_config_invalid", "fallback": "deployment_defaults"}))
            return _runtime_defaults(self.config)

    def run(self):
        now = self.utcnow()
        state = self.store.load()
        runtime = self._runtime()
        settings = runtime["feeds"]
        old_feeds = state.get("feeds") or {}
        feeds = copy.deepcopy(old_feeds)

        # Migrate pre-control-plane cache keys in-place when present. Some older
        # deployments used `queues` for Thorpe Park, so preserve that last-good
        # data before removing the legacy aliases.
        aliases = {
            "departures": ("rail",),
            "thorpe_park": ("thorpePark", "queues"),
        }
        for current, legacy_names in aliases.items():
            if current not in feeds:
                for legacy in legacy_names:
                    if legacy in feeds:
                        feeds[current] = copy.deepcopy(feeds[legacy])
                        break
            for legacy in legacy_names:
                feeds.pop(legacy, None)

        if settings["departures"]["enabled"]:
            feeds["departures"] = self._refresh(
                "departures", feeds.get("departures"), settings["departures"]["poll_seconds"],
                lambda: self._fetch_rail(now), now,
            )
        for feed_id, definition in FEED_REGISTRY.items():
            if definition.get("provider") != "queue_times" or not settings[feed_id]["enabled"]:
                continue
            provider = self.queue_providers[feed_id]
            feeds[feed_id] = self._refresh(
                feed_id,
                feeds.get(feed_id),
                settings[feed_id]["poll_seconds"],
                lambda provider=provider, park=definition["label"]: self._fetch_queues(now, provider, park),
                now,
            )
        if settings["calendar"]["enabled"]:
            feeds["calendar"] = self._refresh(
                "calendar", feeds.get("calendar"), settings["calendar"]["poll_seconds"],
                lambda: self._fetch_calendar(now), now,
            )
        if settings["weather"]["enabled"]:
            feeds["weather"] = self._refresh(
                "weather", feeds.get("weather"), settings["weather"]["poll_seconds"],
                lambda: self._fetch_weather(now), now,
            )

        next_state = {
            "version": 2,
            "updated_at": _iso(now),
            "config_version": runtime["config_version"],
            "feeds": feeds,
        }
        payload = self._screens(feeds, now, runtime)
        self.store.save(next_state)
        self.store.publish(payload)
        print(json.dumps({"event": "screens_published", "screens": len(payload["screens"]), "config_version": runtime["config_version"]}))
        return payload


_PUBLISHER = None


def lambda_handler(event, context):
    del event, context
    global _PUBLISHER
    if _PUBLISHER is None:
        config = PublisherConfig.from_env()
        runtime_store = (
            RuntimeConfigStore(config.runtime_config_table, defaults=_runtime_defaults(config))
            if config.runtime_config_table
            else StaticRuntimeConfigStore(_runtime_defaults(config))
        )
        _PUBLISHER = Publisher(config, S3StateStore(config.bucket), runtime_config_store=runtime_store)
    payload = _PUBLISHER.run()
    return {"published": True, "screen_count": len(payload.get("screens") or []), "config_version": payload.get("config_version")}
