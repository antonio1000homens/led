"""Scheduled AWS publisher for the renderer-neutral LED screen contract."""

from __future__ import annotations

import copy
import gc
import hashlib
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
from dad_jokes import DadJokeProvider
from random_facts import RandomFactProvider
from insults import InsultProvider
from transitous_bus import TransitousBusProvider
from formatting import prepare_rail_presentation, todoist_effective_duration

STATE_KEY = "state/feed-cache.json"
SCREENS_KEY = "api/screens"
DEFAULT_WEATHER_LATITUDE = 51.4039
DEFAULT_WEATHER_LONGITUDE = -0.256
STEAM_TRAIN_DISPLAY_WIDTH = 256
STEAM_TRAIN_EDGE_HOLD_SECONDS = 1.0


def content_version(feed_id, cached):
    data = (cached or {}).get("data") or {}
    text = data.get("joke") if feed_id == "dad_joke" else data.get("fact") if feed_id == "random_fact" else data.get("insult")
    if not text:
        return None
    return hashlib.sha256((str(data.get("fetched_at")) + ":" + text).encode()).hexdigest()


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
            from botocore.config import Config

            client = boto3.client("s3", config=Config(signature_version="s3v4"))
        self.client = client

    def _get_json(self, key, default):
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            meta = getattr(error, "response", {}) or {}
            if str((meta.get("Error") or {}).get("Code") or "") in ("NoSuchKey", "404", "NotFound"):
                return copy.deepcopy(default)
            raise
        with response["Body"] as body:
            return json.loads(body.read().decode("utf-8"))

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

    def displayed(self, feed_id, version):
        if not version:
            return False
        # The capability permits a fixed-size marker, not trusted JSON input.
        # Check existence only: malformed marker bytes must not stop publishing.
        try:
            self.client.head_object(Bucket=self.bucket,
                                    Key="state/displayed/{}/{}.json".format(feed_id, version))
        except Exception as error:
            meta = getattr(error, "response", {}) or {}
            if str((meta.get("Error") or {}).get("Code") or "") in ("NoSuchKey", "404", "NotFound"):
                return False
            raise
        return True

    def acknowledgement(self, feed_id, version):
        # Write-only capability for this exact content version. No board/admin
        # credential or cache mutation permission is exposed. Sign the fixed
        # body length too, so this cannot be used for arbitrary uploads.
        return self.client.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket,
                    "Key": "state/displayed/{}/{}.json".format(feed_id, version),
                    "ContentLength": 2, "ContentType": "application/json"},
            ExpiresIn=3600,
        )


class Publisher:
    def __init__(self, config, store, rail_provider=None, queue_provider=None, weather_provider=None, utcnow=None,
                 calendar_provider=None, chessington_provider=None, runtime_config_store=None, joke_provider=None,
                 fact_provider=None, insult_provider=None, bus_provider=None):
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
        self.joke_provider = joke_provider or DadJokeProvider()
        self.fact_provider = fact_provider or RandomFactProvider()
        self.insult_provider = insult_provider or InsultProvider()
        self.bus_provider = bus_provider or TransitousBusProvider()
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

    def _refresh(self, name, previous, ttl, fetcher, now, force=False):
        previous = copy.deepcopy(previous or {})
        if not force and not self._due(previous, ttl, now):
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

    def _refresh_static_pool(self, feed_id, previous, ttl, now):
        """Replenish a bounded pool; selection belongs to the board.

        At most two new items per scheduled run bounds provider/network work.
        Failed replenishment keeps the entire last-good pool available.
        """
        previous = copy.deepcopy(previous or {})
        items = list(previous.get("items") or [])
        if not items and previous.get("data"):
            items = [copy.deepcopy(previous["data"])]
        consumed = [item for item in items if hasattr(self.store, "displayed")
                    and self.store.displayed(feed_id, content_version(feed_id, {"data": item}))]
        due = self._due(previous, ttl, now)
        if not (due or consumed or len(items) < 5) or not self._due(previous, 60, now):
            return previous
        count = min(2, max(5 - len(items), len(consumed), 1 if due else 0))
        working = previous
        added = []
        for _ in range(count):
            fetcher = {"dad_joke": self._fetch_joke, "random_fact": self._fetch_fact,
                       "insult_of_hour": self._fetch_insult}[feed_id]
            refreshed = self._refresh(feed_id, working, ttl,
                                      lambda: fetcher(now, working), now, force=True)
            if refreshed.get("stale"):
                working = {**working, "last_attempt_at": _iso(now), "stale": True}
                break
            working = refreshed
            added.append(copy.deepcopy(working["data"]))
        if added:
            # Remove consumed items first, only when replacement is available.
            for item in consumed[:len(added)]:
                items.remove(item)
            items = (items + added)[-5:]
        working["items"] = items
        return working

    def _fetch_queues(self, now, provider, park):
        return {"park": park, "source": "queue_times", "fetched_at": _iso(now), "rides": provider.fetch()}

    def _fetch_calendar(self, now):
        if self.calendar_provider is None:
            raise RuntimeError("calendar provider is not configured")
        return {"source": "todoist", "fetched_at": _iso(now), "events": self.calendar_provider.fetch()}

    def _fetch_joke(self, now, previous=None):
        # Persist a bounded history in the existing S3 feed cache, so API
        # duplicates are rejected even across Lambda invocations and restarts.
        old = (previous or {}).get("data") or {}
        history = list(old.get("history") or [])[-99:]
        if old.get("joke") and old["joke"] not in history:
            history.append(old["joke"])
        for _ in range(3):
            joke = self.joke_provider.fetch()
            if joke not in history:
                return {"source": "icanhazdadjoke", "fetched_at": _iso(now),
                        "joke": joke, "history": (history + [joke])[-100:]}
        raise ValueError("Dad joke API returned only previously cached jokes")

    def _fetch_fact(self, now, previous=None):
        # Store recent displayed fact text in the same durable S3 feed cache as jokes.
        old = (previous or {}).get("data") or {}
        history = list(old.get("history") or [])[-99:]
        if old.get("fact") and old["fact"] not in history:
            history.append(old["fact"])
        for _ in range(3):
            fact = self.fact_provider.fetch()
            if fact["text"] not in history:
                return {
                    "source": "uselessfacts.jsph.pl", "fetched_at": _iso(now),
                    "fact": fact["text"], "fact_id": fact["id"],
                    "fact_source": fact.get("source"),
                    "history": (history + [fact["text"]])[-100:],
                }
        raise ValueError("Facts API returned only previously cached facts")

    def _fetch_insult(self, now, previous=None):
        old = (previous or {}).get("data") or {}
        history = list(old.get("history") or [])[-99:]
        if old.get("insult") and old["insult"] not in history:
            history.append(old["insult"])
        for _ in range(3):
            insult = self.insult_provider.fetch()
            if insult not in history:
                return {
                    "source": "insult.mattbas.org", "fetched_at": _iso(now),
                    "insult": insult, "history": (history + [insult])[-100:],
                }
        raise ValueError("Insult API returned only previously cached insults")

    def _fetch_weather(self, now):
        result = {"source": "open_meteo", "fetched_at": _iso(now)}
        result.update(self.weather_provider.fetch())
        return result

    def _fetch_buses(self, now):
        return self.bus_provider.fetch(now=now)

    @staticmethod
    def _bus_screen(stop_key, data, config, feed_stale=False, now=None):
        data = data or {}
        departures = copy.deepcopy((data.get("departures") or [])[:config["upcoming_bus_count"]])
        status = "ok" if departures else ("empty" if data else "unavailable")
        observed_at = data.get("observed_at") or _iso(now or datetime.now(timezone.utc))
        observed = _parse_iso(observed_at)
        stale = bool(feed_stale or not data)
        if observed is not None and now is not None:
            stale = stale or (now - observed).total_seconds() > config["stale_after_seconds"]
        return {
            "id": f"sl7-{stop_key}", "kind": "bus_departures", "route": "SL7",
            "stop_key": stop_key, "stop_name": data.get("stop_name", stop_key.title()),
            "title": f"SL7 {data.get('stop_name', stop_key).upper()}",
            "source": "transitous", "stale": stale, "status": status,
            "duration_seconds": config["screen_duration_seconds"] if departures else config["no_services_duration_seconds"],
            "observed_at": observed_at, "departures": departures,
            "destination_scroll_speed": config["destination_scroll_speed"],
        }

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
            steam_config = config_feeds["steam_train"]
            if steam_config["enabled"]:
                words = steam_config.get("words") or ""
                speed = max(1, int(steam_config["animation_speed"]))
                # The train enters from the right and stops with its front at
                # the left edge. Hold there briefly before departures replaces it.
                duration_seconds = max(
                    2.0,
                    STEAM_TRAIN_DISPLAY_WIDTH / speed + STEAM_TRAIN_EDGE_HOLD_SECONDS,
                )
                screens.append({
                    "id": "steam-train",
                    "kind": "steam_train_intro",
                    "duration_seconds": duration_seconds,
                    "title": "Steam train",
                    "source": "local_animation",
                    "stale": False,
                    "animation_speed": speed,
                    "words": words,
                })
            rail = feeds.get("departures") or {}
            rail_data = rail.get("data")
            services = copy.deepcopy((rail_data.get("services") or [])[:1 + departures_config["upcoming_train_count"]]) if rail_data else []
            for service in services:
                service["station_spacing_px"] = departures_config["station_list_spacing"]
            duration_seconds = (
                departures_config["no_services_duration_seconds"]
                if rail_data is not None and not services
                else departures_config["screen_duration_seconds"]
            )
            presentation = prepare_rail_presentation(
                services,
                departures_config["station_scroll_speed"],
                departures_config["upcoming_train_pause_seconds"],
                duration_seconds,
            )
            no_services = rail_data is not None and not services
            screen = {
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": duration_seconds,
                "station_scroll_speed": departures_config["station_scroll_speed"],
                "upcoming_train_count": departures_config["upcoming_train_count"],
                "upcoming_train_pause_seconds": departures_config["upcoming_train_pause_seconds"],
                "title": f"{rail_data['station']} departures" if rail_data else "Departures unavailable",
                "source": rail_data.get("source", "national_rail") if rail_data else "unavailable",
                "stale": bool(rail.get("stale")) if rail_data else True,
                "empty_state": "No Services" if no_services else None,
                "services": services,
            }
            if presentation is not None:
                screen["rail_presentation"] = presentation
                screen["effective_duration_seconds"] = presentation["effective_duration_seconds"]
                screen["calling_seconds"] = presentation["calling_seconds"]
                screen["summary_seconds"] = presentation["summary_seconds"]
            screens.append(screen)

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
        joke_cfg = config_feeds["dad_joke"]
        if joke_cfg["enabled"]:
            cached_joke = feeds.get("dad_joke") or {}
            joke_data = cached_joke.get("data") or {}
            if joke_data.get("joke"):
                screens.append({
                    "id": "dad-joke", "kind": "dad_joke",
                    "title": "DAD JOKE", "source": "icanhazdadjoke",
                    "duration_seconds": joke_cfg["screen_duration_seconds"],
                    "stale": bool(cached_joke.get("stale")),
                    "joke": joke_data["joke"],
                })
        fact_cfg = config_feeds["random_fact"]
        if fact_cfg["enabled"]:
            cached_fact = feeds.get("random_fact") or {}
            fact_data = cached_fact.get("data") or {}
            if fact_data.get("fact"):
                screens.append({
                    "id": "random-fact", "kind": "random_fact",
                    "title": "DID YOU KNOW?", "source": "uselessfacts.jsph.pl",
                    "duration_seconds": fact_cfg["screen_duration_seconds"],
                    "stale": bool(cached_fact.get("stale")),
                    "fact": fact_data["fact"],
                    "fact_id": fact_data.get("fact_id"),
                    "fact_source": fact_data.get("fact_source"),
                })
        insult_cfg = config_feeds["insult_of_hour"]
        if insult_cfg["enabled"]:
            cached_insult = feeds.get("insult_of_hour") or {}
            insult_data = cached_insult.get("data") or {}
            if insult_data.get("insult"):
                screens.append({
                    "id": "insult-of-hour", "kind": "insult_of_hour",
                    "title": "INSULT OF THE HOUR", "source": "insult.mattbas.org",
                    "duration_seconds": insult_cfg["screen_duration_seconds"],
                    "stale": bool(cached_insult.get("stale")),
                    "insult": insult_data["insult"],
                })
        if config_feeds["today"]["enabled"]:
            current_weather = feeds.get("weather") or {}
            screens.append({
                "id": "today", "kind": "today", "title": "TODAY",
                "duration_seconds": config_feeds["today"]["screen_duration_seconds"],
                "source": "open_meteo", "stale": bool(current_weather.get("stale", True)),
                "weather": {key: value for key, value in (current_weather.get("data") or {}).items()
                            if key in ("temperature_c", "weather_code", "icon", "is_day", "fetched_at")},
            })
        weather_config = config_feeds["weather"]
        if weather_config["enabled"]:
            weather = feeds.get("weather") or {}
            data = weather.get("data")
            if data is not None:
                overlay = copy.deepcopy(data)
                forecast = copy.deepcopy(overlay.pop("forecast", [])[:7])
                today_blocks = copy.deepcopy(overlay.pop("today_blocks", []))
                sunrise_time = overlay.pop("sunrise_time", None)
                sunset_time = overlay.pop("sunset_time", None)
                source = data.get("source", "open_meteo")
                stale = bool(weather.get("stale"))
            else:
                overlay = {
                    "source": "unavailable",
                    "temperature_c": None,
                    "weather_code": None,
                    "icon": "unknown",
                }
                forecast = []
                today_blocks = []
                sunrise_time = None
                sunset_time = None
                source = "unavailable"
                stale = True
            overlay["stale"] = stale

            if weather_config["overview_enabled"]:
                screens.append({
                    "id": "weather-weekly",
                    "kind": "weather_weekly",
                    "duration_seconds": weather_config["screen_duration_seconds"],
                    "title": "7 DAY WEATHER",
                    "source": source,
                    "stale": stale,
                    "days": forecast,
                })
            if weather_config["today_enabled"] and today_blocks:
                screens.append({
                    "id": "weather-today",
                    "kind": "weather_today",
                    "duration_seconds": weather_config["today_duration_seconds"],
                    "title": "NEXT 24H",
                    "source": source,
                    "stale": stale,
                    "blocks": today_blocks,
                })
            if weather_config["sun_enabled"] and sunrise_time and sunset_time:
                screens.append({
                    "id": "weather-sun",
                    "kind": "weather_sun",
                    "duration_seconds": weather_config["sun_duration_seconds"],
                    "title": "SUNRISE / SUNSET",
                    "source": source,
                    "stale": stale,
                    "sunrise_time": sunrise_time,
                    "sunset_time": sunset_time,
                })
            for screen in screens:
                screen["weather"] = copy.deepcopy(overlay)
        for screen in screens:
            feed_id = screen.get("kind")
            if FEED_REGISTRY.get(feed_id, {}).get("display_group"):
                screen["display_group"] = "static_feeds"
            if feed_id in ("dad_joke", "random_fact", "insult_of_hour"):
                cached = feeds.get(feed_id) or {}
                screen["items"] = []
                for data in cached.get("items") or [cached.get("data") or {}]:
                    item = {key: value for key, value in data.items() if key != "history"}
                    version = content_version(feed_id, {"data": data})
                    item["content_version"] = version
                    if hasattr(self.store, "acknowledgement"):
                        item["refresh_ack_url"] = self.store.acknowledgement(feed_id, version)
                    screen["items"].append(item)
        bus_config = config_feeds["sl7_bus"]
        if bus_config["enabled"]:
            bus_feed = feeds.get("sl7_bus") or {}
            bus_data = bus_feed.get("data") or {}
            if bus_config.get("heathrow_enabled"):
                screens.append(self._bus_screen("heathrow", bus_data.get("heathrow"), bus_config, bus_feed.get("stale", False), now))
            if bus_config.get("new_malden_enabled"):
                screens.append(self._bus_screen("new-malden", bus_data.get("new-malden"), bus_config, bus_feed.get("stale", False), now))
        return {
            "fetched_at": _iso(now),
            "config_version": runtime["config_version"],
            "display": copy.deepcopy(runtime["display"]),
            "flash": copy.deepcopy(config_feeds["flash"]),
            # Non-secret MQTT screen policy is consumed by the board. The
            # publisher cannot report broker health; this is configuration only.
            "sl7_bus": copy.deepcopy(config_feeds["sl7_bus"]),
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
        if settings["dad_joke"]["enabled"]:
            feeds["dad_joke"] = self._refresh_static_pool(
                "dad_joke", feeds.get("dad_joke"), settings["dad_joke"]["poll_seconds"], now,
            )
        if settings["random_fact"]["enabled"]:
            feeds["random_fact"] = self._refresh_static_pool(
                "random_fact", feeds.get("random_fact"), settings["random_fact"]["poll_seconds"], now,
            )
        if settings["insult_of_hour"]["enabled"]:
            previous_insult = feeds.get("insult_of_hour")
            feeds["insult_of_hour"] = self._refresh(
                "insult_of_hour", previous_insult, settings["insult_of_hour"]["poll_seconds"],
                lambda: self._fetch_insult(now, (previous_insult or {})), now,
            )
        if settings["weather"]["enabled"] or settings["today"]["enabled"]:
            weather_previous = feeds.get("weather")
            weather_data = (weather_previous or {}).get("data")
            # Refresh older cache schemas immediately so all three dedicated
            # Weather screens can be populated without waiting for the normal TTL.
            needs_weather_contract_upgrade = (
                isinstance(weather_data, dict)
                and (
                    "forecast" not in weather_data
                    or "today_blocks" not in weather_data
                    or "sunrise_time" not in weather_data
                    or "sunset_time" not in weather_data
                )
            )
            feeds["weather"] = self._refresh(
                "weather", weather_previous, settings["weather"]["poll_seconds"],
                lambda: self._fetch_weather(now), now,
                force=needs_weather_contract_upgrade,
            )
        if settings["sl7_bus"]["enabled"]:
            feeds["sl7_bus"] = self._refresh(
                "sl7_bus", feeds.get("sl7_bus"), settings["sl7_bus"].get("poll_seconds", 60),
                lambda: self._fetch_buses(now), now,
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
    del context
    event = event or {}
    if event.get("action") == "garbage_collect":
        reclaimed = gc.collect()
        print(json.dumps({"event": "garbage_collection_requested", "reclaimed": reclaimed}))
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
