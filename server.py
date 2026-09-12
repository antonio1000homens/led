"""Local departures API and browser simulator server.

This is deliberately CPython-only. It keeps external feed integration on the
backend and exposes a small JSON contract that a browser or a future
CircuitPython client can consume.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from urllib.parse import urlparse

from fixtures import CALENDAR_EVENTS, PAGES
from queue_times import QueueFeedUnavailable, QueueTimesProvider, ThorpeParkFeed
from weather import OpenMeteoProvider, WeatherFeed, WeatherFeedUnavailable


WSDL_URL = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx?ver=2021-11-01"
SECRET_ID_PATTERN = re.compile(r"^[0-9a-fA-F-]{36}$")
PROJECT_ROOT = Path(__file__).resolve().parent
SIMULATOR_ROOT = PROJECT_ROOT / "simulator"
DEFAULT_THORPE_PARK_RIDES = ("Hyperia", "Stealth", "The Swarm")
DEFAULT_WEATHER_LATITUDE = 51.4039
DEFAULT_WEATHER_LONGITUDE = -0.256


class ConfigurationError(RuntimeError):
    """The server cannot start safely with its current configuration."""


class FeedUnavailable(RuntimeError):
    """No departure data is currently available."""


def load_dotenv(path=PROJECT_ROOT / ".env"):
    """Load simple KEY=VALUE settings without overwriting the environment."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


def resolve_bitwarden_secret(secret_id, runner=None):
    """Resolve one Bitwarden secret without propagating sensitive output."""
    if not SECRET_ID_PATTERN.fullmatch(secret_id or ""):
        raise ConfigurationError("BWS_NATIONAL_RAIL_TOKEN_SECRET_ID must be a secret UUID")
    runner = runner or subprocess.run
    try:
        result = runner(
            ["bws", "secret", "get", secret_id, "--output", "json"],
            check=True,
            capture_output=True,
            text=True,
        )
        value = json.loads(result.stdout).get("value", "")
    except (FileNotFoundError, subprocess.SubprocessError, json.JSONDecodeError, AttributeError) as error:
        raise ConfigurationError("Unable to resolve the National Rail token from Bitwarden") from error
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError("The configured Bitwarden secret has no value")
    return value.strip()


def _first_location_name(value):
    if not isinstance(value, dict):
        return "Unknown"
    locations = value.get("location") or []
    if isinstance(locations, dict):
        locations = [locations]
    if locations and isinstance(locations[0], dict):
        return str(locations[0].get("locationName") or "Unknown")
    return "Unknown"


def _reason_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return str(value.get("reason") or value.get("value") or "")
    return ""


def _calling_points(value):
    """Flatten Darwin's destination-grouped calling-point structure."""
    groups = value or []
    if isinstance(groups, dict):
        groups = groups.get("callingPointList") or [groups]
    points = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        raw_points = group.get("callingPoint") or group.get("callingPoints") or []
        if isinstance(raw_points, dict):
            raw_points = [raw_points]
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            scheduled = str(point.get("st") or point.get("sta") or "--:--")
            expected = str(point.get("et") or point.get("at") or scheduled)
            cancelled = bool(point.get("isCancelled")) or expected.lower() == "cancelled"
            if cancelled:
                status = "Cancelled"
            elif expected.lower() == "on time" or expected == scheduled:
                status = "On time"
            else:
                status = expected
            points.append({
                "station": str(point.get("locationName") or "Unknown"),
                "crs": str(point.get("crs") or ""),
                "time": scheduled,
                "status": status,
                "cancelled": cancelled,
            })
    return points


def normalize_darwin_board(board, max_rows=10):
    """Convert a serialized Darwin departure board to the stable LED model."""
    container = (board or {}).get("trainServices") or {}
    raw_services = container.get("service") or [] if isinstance(container, dict) else []
    if isinstance(raw_services, dict):
        raw_services = [raw_services]

    services = []
    for item in raw_services[:max_rows]:
        scheduled = str(item.get("std") or item.get("sta") or "--:--")
        expected = str(item.get("etd") or item.get("eta") or scheduled)
        cancelled = bool(item.get("isCancelled")) or expected.lower() == "cancelled"
        if cancelled:
            status = "Cancelled"
        elif expected.lower() == "on time" or expected == scheduled:
            status = "On time"
        else:
            status = expected
        services.append(
            {
                "time": scheduled,
                "destination": _first_location_name(item.get("destination")),
                "platform": str(item.get("platform") or "-"),
                "status": status,
                "cancelled": cancelled,
                "delay_reason": _reason_text(item.get("delayReason") or item.get("cancelReason")),
                "stops": _calling_points(item.get("subsequentCallingPoints")),
            }
        )
    return services


class FixtureProvider:
    source = "fixture"

    def __init__(self, max_rows=10):
        self.max_rows = max_rows

    def fetch(self):
        return [copy.deepcopy(service) for page in PAGES for service in page][: self.max_rows]


class FixtureCalendarProvider:
    """Credential-free stand-in for a future calendar adapter."""

    source = "calendar_fixture"

    def fetch(self):
        return copy.deepcopy(CALENDAR_EVENTS)


class NationalRailProvider:
    source = "national_rail"

    def __init__(self, token, station, max_rows=10):
        self.token = token
        self.station = station
        self.max_rows = max_rows
        self._client = None
        self._header = None

    def _connect(self):
        if self._client is not None:
            return
        try:
            from zeep import Client, Settings, helpers, xsd
            from zeep.transports import Transport
        except ImportError as error:
            raise ConfigurationError(
                "Live mode requires: python -m pip install -r requirements-server.txt"
            ) from error
        self._serialize = helpers.serialize_object
        self._client = Client(
            wsdl=WSDL_URL,
            settings=Settings(strict=False),
            transport=Transport(timeout=10, operation_timeout=15),
        )
        header = xsd.Element(
            "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}AccessToken",
            xsd.ComplexType(
                [
                    xsd.Element(
                        "{http://thalesgroup.com/RTTI/2013-11-28/Token/types}TokenValue",
                        xsd.String(),
                    )
                ]
            ),
        )
        self._header = header(TokenValue=self.token)

    def fetch(self):
        self._connect()
        board = self._client.service.GetDepBoardWithDetails(
            numRows=self.max_rows,
            crs=self.station,
            _soapheaders=[self._header],
        )
        return normalize_darwin_board(self._serialize(board), self.max_rows)


class DepartureFeed:
    def __init__(self, provider, station, cache_seconds=60, monotonic=None, utcnow=None):
        self.provider = provider
        self.station = station
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
                services = self.provider.fetch()
            except Exception as error:
                if self._payload is None:
                    raise FeedUnavailable("Departure data is unavailable") from error
                self._payload["stale"] = True
                return copy.deepcopy(self._payload)

            self._payload = {
                "station": self.station,
                "source": self.provider.source,
                "fetched_at": self.utcnow().isoformat().replace("+00:00", "Z"),
                "stale": False,
                "services": services,
            }
            return copy.deepcopy(self._payload)


def _select_rides(rides, names):
    """Keep a stable configured ride order, ignoring unavailable ride names."""
    by_name = {ride.get("name", "").casefold(): ride for ride in rides}
    selected = []
    for name in names:
        ride = by_name.get(name.casefold())
        if ride is not None:
            selected.append(ride)
    return selected


class ScreenFeed:
    """Compose independent feed payloads into renderer-neutral screens."""

    def __init__(
        self,
        departure_feed,
        calendar_provider=None,
        queue_feed=None,
        queue_ride_names=None,
        weather_feed=None,
        utcnow=None,
    ):
        self.departure_feed = departure_feed
        self.calendar_provider = calendar_provider
        self.queue_feed = queue_feed
        self.queue_ride_names = tuple(queue_ride_names or DEFAULT_THORPE_PARK_RIDES)
        self.weather_feed = weather_feed
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))

    def get(self):
        screens = []
        try:
            departures = self.departure_feed.get()
            screens.append({
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "title": "{} departures".format(departures["station"]),
                "source": departures["source"],
                "stale": departures["stale"],
                "services": departures["services"][:3],
            })
        except FeedUnavailable:
            screens.append({
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "title": "Departures unavailable",
                "source": "unavailable",
                "stale": True,
                "services": [],
            })

        if self.queue_feed is not None:
            try:
                queues = self.queue_feed.get()
                rides = _select_rides(queues["rides"], self.queue_ride_names)
                screens.append({
                    "id": "thorpe-park",
                    "kind": "theme_park_queues",
                    "duration_seconds": 8,
                    "title": "THORPE PARK · Powered by Queue-Times.com",
                    "source": queues["source"],
                    "stale": queues["stale"],
                    "rides": rides[:3],
                    "attribution": "Powered by Queue-Times.com",
                })
            except QueueFeedUnavailable:
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

        if self.calendar_provider is not None:
            try:
                events = self.calendar_provider.fetch()
                screens.append({
                    "id": "calendar",
                    "kind": "calendar_agenda",
                    "duration_seconds": 8,
                    "title": "Upcoming events",
                    "source": self.calendar_provider.source,
                    "stale": False,
                    "events": events,
                })
            except Exception:
                screens.append({
                    "id": "calendar",
                    "kind": "calendar_agenda",
                    "duration_seconds": 8,
                    "title": "Calendar unavailable",
                    "source": "unavailable",
                    "stale": True,
                    "events": [],
                })

        if self.weather_feed is not None:
            try:
                weather = self.weather_feed.get()
            except WeatherFeedUnavailable:
                weather = {
                    "source": "unavailable",
                    "stale": True,
                    "temperature_c": None,
                    "weather_code": None,
                    "icon": "unknown",
                }
            for screen in screens:
                screen["weather"] = copy.deepcopy(weather)

        return {
            "fetched_at": self.utcnow().isoformat().replace("+00:00", "Z"),
            "screens": screens,
        }


class SimulatorHandler(SimpleHTTPRequestHandler):
    feed = None
    screen_feed = None

    def do_GET(self):
        if urlparse(self.path).path == "/api/departures":
            self._serve_departures()
            return
        if urlparse(self.path).path == "/api/screens":
            self._serve_screens()
            return
        super().do_GET()

    def _serve_departures(self):
        try:
            payload = self.feed.get()
            status = 200
        except FeedUnavailable:
            payload = {"error": "departures_unavailable"}
            status = 503
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_screens(self):
        body = json.dumps(self.screen_feed.get(), separators=(",", ":")).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(feed, host="127.0.0.1", port=8000, screen_feed=None):
    handler = type(
        "ConfiguredSimulatorHandler",
        (SimulatorHandler,),
        {"feed": feed, "screen_feed": screen_feed or ScreenFeed(feed)},
    )
    return ThreadingHTTPServer((host, port), partial(handler, directory=str(SIMULATOR_ROOT)))


def build_feed(source, station, max_rows, cache_seconds):
    if source == "fixture":
        provider = FixtureProvider(max_rows)
    elif source == "national_rail":
        secret_id = os.environ.get("BWS_NATIONAL_RAIL_TOKEN_SECRET_ID", "")
        provider = NationalRailProvider(resolve_bitwarden_secret(secret_id), station, max_rows)
    else:
        raise ConfigurationError("LED_DATA_SOURCE must be fixture or national_rail")
    return DepartureFeed(provider, station, cache_seconds)


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Serve the LED departures simulator")
    parser.add_argument("--source", choices=("fixture", "national_rail"), default=os.getenv("LED_DATA_SOURCE", "fixture"))
    parser.add_argument("--station", default=os.getenv("LED_STATION_CRS", "NEM"))
    parser.add_argument("--max-rows", type=int, default=int(os.getenv("LED_MAX_ROWS", "10")))
    parser.add_argument("--cache-seconds", type=int, default=int(os.getenv("LED_CACHE_SECONDS", "60")))
    parser.add_argument("--calendar-source", choices=("off", "fixture"), default=os.getenv("LED_CALENDAR_SOURCE", "off"))
    parser.add_argument("--thorpe-park-source", choices=("off", "queue_times"), default=os.getenv("LED_THORPE_PARK_SOURCE", "off"))
    parser.add_argument("--thorpe-park-cache-seconds", type=int, default=int(os.getenv("LED_THORPE_PARK_CACHE_SECONDS", "300")))
    parser.add_argument("--thorpe-park-rides", default=os.getenv("LED_THORPE_PARK_RIDES", ",".join(DEFAULT_THORPE_PARK_RIDES)))
    parser.add_argument("--weather-source", choices=("off", "open_meteo"), default=os.getenv("LED_WEATHER_SOURCE", "open_meteo"))
    parser.add_argument("--weather-cache-seconds", type=int, default=int(os.getenv("LED_WEATHER_CACHE_SECONDS", "600")))
    parser.add_argument("--weather-latitude", type=float, default=float(os.getenv("LED_WEATHER_LATITUDE", str(DEFAULT_WEATHER_LATITUDE))))
    parser.add_argument("--weather-longitude", type=float, default=float(os.getenv("LED_WEATHER_LONGITUDE", str(DEFAULT_WEATHER_LONGITUDE))))
    parser.add_argument("--host", default=os.getenv("LED_SERVER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("LED_SERVER_PORT", "8000")))
    args = parser.parse_args()

    station = args.station.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", station):
        raise ConfigurationError("Station CRS must contain exactly three letters")
    if args.max_rows < 1 or args.max_rows > 50:
        raise ConfigurationError("max-rows must be between 1 and 50")
    if args.cache_seconds < 1:
        raise ConfigurationError("cache-seconds must be positive")
    if args.thorpe_park_cache_seconds < 1:
        raise ConfigurationError("thorpe-park-cache-seconds must be positive")
    if args.weather_cache_seconds < 1:
        raise ConfigurationError("weather-cache-seconds must be positive")
    if not -90 <= args.weather_latitude <= 90:
        raise ConfigurationError("weather-latitude must be between -90 and 90")
    if not -180 <= args.weather_longitude <= 180:
        raise ConfigurationError("weather-longitude must be between -180 and 180")

    ride_names = tuple(name.strip() for name in args.thorpe_park_rides.split(",") if name.strip())
    if args.thorpe_park_source != "off" and not ride_names:
        raise ConfigurationError("thorpe-park-rides must contain at least one ride")

    feed = build_feed(args.source, station, args.max_rows, args.cache_seconds)
    calendar_provider = FixtureCalendarProvider() if args.calendar_source == "fixture" else None
    queue_feed = None
    if args.thorpe_park_source == "queue_times":
        queue_feed = ThorpeParkFeed(QueueTimesProvider(), args.thorpe_park_cache_seconds)

    weather_feed = None
    if args.weather_source == "open_meteo":
        weather_feed = WeatherFeed(
            OpenMeteoProvider(args.weather_latitude, args.weather_longitude),
            args.weather_cache_seconds,
        )

    screen_feed = ScreenFeed(feed, calendar_provider, queue_feed, ride_names, weather_feed)
    server = create_server(feed, args.host, args.port, screen_feed)
    print(
        "LED simulator: http://{}:{} (source={}, station={}, thorpe_park={}, weather={})".format(
            args.host,
            args.port,
            args.source,
            station,
            args.thorpe_park_source,
            args.weather_source,
        )
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
