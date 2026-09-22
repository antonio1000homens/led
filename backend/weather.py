"""Current-weather provider and cache for the LED backend."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import threading
import time
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherFeedUnavailable(RuntimeError):
    """No current weather data is available."""


def weather_icon(weather_code, is_day=True):
    """Map WMO weather interpretation codes to renderer-neutral icon names."""
    try:
        code = int(weather_code)
    except (TypeError, ValueError):
        return "unknown"

    if code == 0:
        return "clear_day" if is_day else "clear_night"
    if code in (1, 2):
        return "partly_cloudy_day" if is_day else "partly_cloudy_night"
    if code == 3:
        return "cloudy"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        return "rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "snow"
    if code in (95, 96, 99):
        return "storm"
    return "unknown"


class OpenMeteoProvider:
    """Fetch current temperature and WMO weather code from Open-Meteo."""

    source = "open_meteo"

    def __init__(self, latitude, longitude, opener=None, timeout=10):
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.opener = opener or urlopen
        self.timeout = timeout

    def fetch(self):
        query = urlencode(
            {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": "temperature_2m,weather_code,is_day",
            }
        )
        response = self.opener(OPEN_METEO_URL + "?" + query, timeout=self.timeout)
        try:
            payload = json.load(response)
        finally:
            response.close()

        current = payload.get("current") if isinstance(payload, dict) else None
        if not isinstance(current, dict):
            raise WeatherFeedUnavailable("Open-Meteo response has no current weather")
        try:
            temperature = float(current["temperature_2m"])
            code = int(current["weather_code"])
            is_day = bool(int(current.get("is_day", 1)))
        except (KeyError, TypeError, ValueError) as error:
            raise WeatherFeedUnavailable("Open-Meteo current weather is invalid") from error

        return {
            "temperature_c": round(temperature, 1),
            "weather_code": code,
            "icon": weather_icon(code, is_day),
            "is_day": is_day,
            "attribution": "Weather data by Open-Meteo.com",
            "attribution_url": "https://open-meteo.com/",
        }


class WeatherFeed:
    """Cache weather independently and retain the last successful value on errors."""

    def __init__(self, provider, cache_seconds=600, monotonic=None, utcnow=None):
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
                weather = self.provider.fetch()
            except Exception as error:
                if self._payload is None:
                    raise WeatherFeedUnavailable("Weather data is unavailable") from error
                self._payload["stale"] = True
                return copy.deepcopy(self._payload)

            self._payload = {
                "source": self.provider.source,
                "fetched_at": self.utcnow().isoformat().replace("+00:00", "Z"),
                "stale": False,
            }
            self._payload.update(weather)
            return copy.deepcopy(self._payload)
