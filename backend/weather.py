"""Current, seven-day, rolling 24-hour and solar weather provider/cache for the LED backend."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
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


def _local_hhmm(value):
    text = str(value or "")
    if "T" not in text:
        raise ValueError("missing local timestamp")
    return text.split("T", 1)[1][:5]


def _hour_label(stamp):
    hour = stamp.hour
    return "{}{}".format(hour % 12 or 12, "am" if hour < 12 else "pm")


def _next_24h_blocks(hourly, current):
    """Build six rolling four-hour snapshots beginning with current conditions."""
    if not isinstance(hourly, dict) or not isinstance(current, dict):
        return []
    times = hourly.get("time")
    temperatures = hourly.get("temperature_2m")
    codes = hourly.get("weather_code")
    is_day_values = hourly.get("is_day")
    if not all(isinstance(values, list) for values in (times, temperatures, codes)):
        return []

    try:
        current_stamp = datetime.fromisoformat(str(current["time"])).replace(tzinfo=None)
        current_temperature = round(float(current["temperature_2m"]), 1)
        current_code = int(current["weather_code"])
        current_is_day = bool(int(current.get("is_day", 1)))
    except (KeyError, TypeError, ValueError):
        return []

    entries = []
    count = min(len(times), len(temperatures), len(codes))
    for index in range(count):
        try:
            stamp = datetime.fromisoformat(str(times[index])).replace(tzinfo=None)
            code = int(codes[index])
            is_day = (
                bool(int(is_day_values[index]))
                if isinstance(is_day_values, list) and index < len(is_day_values)
                else True
            )
            entries.append(
                {
                    "stamp": stamp,
                    "temperature_c": round(float(temperatures[index]), 1),
                    "weather_code": code,
                    "is_day": is_day,
                }
            )
        except (TypeError, ValueError):
            continue

    blocks = [
        {
            "label": "Now",
            "temperature_c": current_temperature,
            "weather_code": current_code,
            "icon": weather_icon(current_code, current_is_day),
        }
    ]
    anchor = current_stamp.replace(minute=0, second=0, microsecond=0)
    for offset_hours in range(4, 24, 4):
        target = anchor + timedelta(hours=offset_hours)
        if not entries:
            break
        selected = min(
            entries,
            key=lambda entry: (
                abs((entry["stamp"] - target).total_seconds()),
                entry["stamp"],
            ),
        )
        if abs((selected["stamp"] - target).total_seconds()) > 2 * 60 * 60:
            continue
        blocks.append(
            {
                "label": _hour_label(target),
                "temperature_c": selected["temperature_c"],
                "weather_code": selected["weather_code"],
                "icon": weather_icon(selected["weather_code"], selected["is_day"]),
            }
        )
    return blocks


class OpenMeteoProvider:
    """Fetch current, weekly, rolling 24-hour and solar weather from Open-Meteo."""

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
                "hourly": "temperature_2m,weather_code,is_day",
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
        blocks = _next_24h_blocks(
            payload.get("hourly") if isinstance(payload, dict) else None,
            current,
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
