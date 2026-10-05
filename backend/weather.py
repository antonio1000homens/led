"""Current, seven-day, Today and solar weather provider/cache for the LED backend."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import threading
import time
from urllib.parse import urlencode
from urllib.request import urlopen


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TODAY_BLOCKS = (
    ("00-04", 0, 4, 2),
    ("04-08", 4, 8, 6),
    ("08-12", 8, 12, 10),
    ("12-16", 12, 16, 14),
    ("16-20", 16, 20, 18),
    ("20-24", 20, 24, 22),
)


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


def _local_hhmm(value):
    text = str(value or "")
    if "T" not in text:
        raise ValueError("missing local timestamp")
    return text.split("T", 1)[1][:5]


def _today_blocks(hourly, today_date, sunrise_time=None, sunset_time=None):
    if not isinstance(hourly, dict):
        return []
    times = hourly.get("time")
    temperatures = hourly.get("temperature_2m")
    codes = hourly.get("weather_code")
    if not all(isinstance(values, list) for values in (times, temperatures, codes)):
        return []

    entries = []
    count = min(len(times), len(temperatures), len(codes))
    for index in range(count):
        try:
            stamp = datetime.strptime(str(times[index]), "%Y-%m-%dT%H:%M")
            if stamp.strftime("%Y-%m-%d") != today_date:
                continue
            entries.append(
                {
                    "hour": stamp.hour,
                    "temperature_c": round(float(temperatures[index]), 1),
                    "weather_code": int(codes[index]),
                }
            )
        except (TypeError, ValueError):
            continue

    try:
        rise_parts = str(sunrise_time).split(":", 1)
        set_parts = str(sunset_time).split(":", 1)
        rise_minutes = int(rise_parts[0]) * 60 + int(rise_parts[1])
        set_minutes = int(set_parts[0]) * 60 + int(set_parts[1])
    except (IndexError, TypeError, ValueError):
        rise_minutes, set_minutes = 6 * 60, 18 * 60

    blocks = []
    for label, start, end, midpoint in TODAY_BLOCKS:
        candidates = [entry for entry in entries if start <= entry["hour"] < end]
        if not candidates:
            continue
        selected = min(candidates, key=lambda entry: (abs(entry["hour"] - midpoint), entry["hour"]))
        is_day = rise_minutes <= selected["hour"] * 60 < set_minutes
        blocks.append(
            {
                "label": label,
                "temperature_c": selected["temperature_c"],
                "weather_code": selected["weather_code"],
                "icon": weather_icon(selected["weather_code"], is_day),
            }
        )
    return blocks


class OpenMeteoProvider:
    """Fetch current, weekly, Today and solar weather from Open-Meteo."""

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
                "hourly": "temperature_2m,weather_code",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset",
                "forecast_days": 7,
                "timezone": "auto",
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

        daily = payload.get("daily") if isinstance(payload, dict) else None
        if not isinstance(daily, dict):
            raise WeatherFeedUnavailable("Open-Meteo response has no daily forecast")
        required = ("time", "weather_code", "temperature_2m_max", "temperature_2m_min")
        arrays = [daily.get(name) for name in required]
        if any(not isinstance(values, list) for values in arrays):
            raise WeatherFeedUnavailable("Open-Meteo daily forecast is invalid")

        sunrise_values = daily.get("sunrise") if isinstance(daily.get("sunrise"), list) else []
        sunset_values = daily.get("sunset") if isinstance(daily.get("sunset"), list) else []
        forecast = []
        count = min(7, *(len(values) for values in arrays))
        for index in range(count):
            try:
                date_text = str(arrays[0][index])
                date_value = datetime.strptime(date_text, "%Y-%m-%d")
                daily_code = int(arrays[1][index])
                temperature_max = float(arrays[2][index])
                temperature_min = float(arrays[3][index])
            except (TypeError, ValueError):
                continue
            day = {
                "date": date_text,
                "weekday": date_value.strftime("%a").upper(),
                "temperature_max_c": round(temperature_max, 1),
                "temperature_min_c": round(temperature_min, 1),
                "weather_code": daily_code,
                "icon": weather_icon(daily_code, True),
            }
            try:
                day["sunrise_time"] = _local_hhmm(sunrise_values[index])
            except (IndexError, TypeError, ValueError):
                pass
            try:
                day["sunset_time"] = _local_hhmm(sunset_values[index])
            except (IndexError, TypeError, ValueError):
                pass
            forecast.append(day)
        if not forecast:
            raise WeatherFeedUnavailable("Open-Meteo daily forecast has no usable entries")

        today = forecast[0]
        blocks = _today_blocks(
            payload.get("hourly") if isinstance(payload, dict) else None,
            today["date"],
            today.get("sunrise_time"),
            today.get("sunset_time"),
        )

        return {
            "temperature_c": round(temperature, 1),
            "weather_code": code,
            "icon": weather_icon(code, is_day),
            "is_day": is_day,
            "forecast": forecast,
            "today_blocks": blocks,
            "sunrise_time": today.get("sunrise_time"),
            "sunset_time": today.get("sunset_time"),
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
