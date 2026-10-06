import io
import json
import unittest
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from server import DepartureFeed, FixtureProvider, ScreenFeed
from weather import OpenMeteoProvider, WeatherFeed, WeatherFeedUnavailable, weather_icon


def sample_forecast():
    return [
        {
            "date": "2026-10-04",
            "weekday": "SUN",
            "temperature_max_c": 16.2,
            "temperature_min_c": 9.4,
            "weather_code": 61,
            "icon": "rain",
            "sunrise_time": "07:08",
            "sunset_time": "18:29",
        },
        {
            "date": "2026-10-05",
            "weekday": "MON",
            "temperature_max_c": 17.2,
            "temperature_min_c": 10.4,
            "weather_code": 2,
            "icon": "partly_cloudy_day",
            "sunrise_time": "07:10",
            "sunset_time": "18:27",
        },
    ]


def sample_blocks():
    return [
        {"label": "Now", "temperature_c": 10.0, "weather_code": 0, "icon": "clear_day"},
        {"label": "2pm", "temperature_c": 11.0, "weather_code": 1, "icon": "partly_cloudy_day"},
        {"label": "6pm", "temperature_c": 12.0, "weather_code": 2, "icon": "partly_cloudy_day"},
        {"label": "10pm", "temperature_c": 13.0, "weather_code": 3, "icon": "cloudy"},
        {"label": "2am", "temperature_c": 14.0, "weather_code": 61, "icon": "rain"},
        {"label": "6am", "temperature_c": 15.0, "weather_code": 45, "icon": "fog"},
    ]


class FakeWeatherProvider:
    source = "test_weather"

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


class IconTests(unittest.TestCase):
    def test_maps_wmo_codes_to_compact_icon_names(self):
        self.assertEqual(weather_icon(0, True), "clear_day")
        self.assertEqual(weather_icon(0, False), "clear_night")
        self.assertEqual(weather_icon(2, True), "partly_cloudy_day")
        self.assertEqual(weather_icon(3, True), "cloudy")
        self.assertEqual(weather_icon(45, True), "fog")
        self.assertEqual(weather_icon(61, True), "rain")
        self.assertEqual(weather_icon(75, True), "snow")
        self.assertEqual(weather_icon(95, True), "storm")
        self.assertEqual(weather_icon(999, True), "unknown")


class OpenMeteoProviderTests(unittest.TestCase):
    def _payload(self, days=2):
        dates = ["2026-10-{:02d}".format(4 + index) for index in range(days)]
        start = datetime(2026, 10, 4)
        stamps = [start + timedelta(hours=hour) for hour in range(48)]
        hours = [stamp.strftime("%Y-%m-%dT%H:%M") for stamp in stamps]
        return {
            "current": {
                "time": "2026-10-04T10:45",
                "temperature_2m": 17.36,
                "weather_code": 2,
                "is_day": 1,
            },
            "hourly": {
                "time": hours,
                "temperature_2m": [8 + hour / 2 for hour in range(48)],
                "weather_code": [0 for _ in range(48)],
                "is_day": [1 if 7 <= stamp.hour < 19 else 0 for stamp in stamps],
            },
            "daily": {
                "time": dates,
                "weather_code": [61, 2, 3, 0, 45, 71, 95, 80][:days],
                "temperature_2m_max": [16.2 + index for index in range(days)],
                "temperature_2m_min": [9.4 + index for index in range(days)],
                "sunrise": ["2026-10-{:02d}T07:{:02d}".format(4 + index, 8 + index * 2) for index in range(days)],
                "sunset": ["2026-10-{:02d}T18:{:02d}".format(4 + index, 29 - index * 2) for index in range(days)],
            },
        }

    def test_fetches_all_weather_fields_in_one_request_and_normalizes_response(self):
        captured = {}

        def opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return io.BytesIO(json.dumps(self._payload()).encode("utf-8"))

        result = OpenMeteoProvider(51.4039, -0.256, opener=opener).fetch()
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(query["current"], ["temperature_2m,weather_code,is_day"])
        self.assertEqual(query["hourly"], ["temperature_2m,weather_code,is_day"])
        self.assertEqual(
            query["daily"],
            ["weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset"],
        )
        self.assertEqual(query["forecast_days"], ["7"])
        self.assertEqual(query["timezone"], ["auto"])
        self.assertEqual(captured["timeout"], 10)
        self.assertEqual(result["temperature_c"], 17.4)
        self.assertEqual(result["forecast"], sample_forecast())
        self.assertEqual(result["sunrise_time"], "07:08")
        self.assertEqual(result["sunset_time"], "18:29")
        self.assertEqual([block["label"] for block in result["today_blocks"]],
                         ["Now", "2pm", "6pm", "10pm", "2am", "6am"])
        self.assertEqual([block["temperature_c"] for block in result["today_blocks"]],
                         [17.4, 15.0, 17.0, 19.0, 21.0, 23.0])
        self.assertEqual(result["today_blocks"][4]["icon"], "clear_night")

    def test_rolling_weather_uses_nearest_hour_when_a_target_is_missing(self):
        payload = self._payload()
        target = payload["hourly"]["time"].index("2026-10-04T14:00")
        for key in ("time", "temperature_2m", "weather_code", "is_day"):
            payload["hourly"][key].pop(target)

        def opener(url, timeout):
            del url, timeout
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        blocks = OpenMeteoProvider(51.4, -0.25, opener=opener).fetch()["today_blocks"]
        self.assertEqual(blocks[1]["label"], "2pm")
        self.assertEqual(blocks[1]["temperature_c"], 14.5)

    def test_malformed_solar_values_do_not_break_current_weekly_or_next_24h(self):
        payload = self._payload()
        payload["daily"]["sunrise"][0] = "bad"

        def opener(url, timeout):
            del url, timeout
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        result = OpenMeteoProvider(51.4, -0.25, opener=opener).fetch()
        self.assertEqual(result["temperature_c"], 17.4)
        self.assertEqual(len(result["forecast"]), 2)
        self.assertEqual(len(result["today_blocks"]), 6)
        self.assertIsNone(result["sunrise_time"])
        self.assertEqual(result["sunset_time"], "18:29")

    def test_forecast_is_capped_at_seven_and_weekdays_are_backend_generated(self):
        def opener(url, timeout):
            del url, timeout
            return io.BytesIO(json.dumps(self._payload(days=8)).encode("utf-8"))

        forecast = OpenMeteoProvider(51.4, -0.25, opener=opener).fetch()["forecast"]
        self.assertEqual(len(forecast), 7)
        self.assertEqual(forecast[0]["weekday"], "SUN")
        self.assertEqual(forecast[1]["weekday"], "MON")
        self.assertEqual(forecast[-1]["date"], "2026-10-10")

    def test_rejects_response_without_current_weather(self):
        def opener(url, timeout):
            del url, timeout
            return io.BytesIO(b"{}")

        with self.assertRaises(WeatherFeedUnavailable):
            OpenMeteoProvider(51.4, -0.25, opener=opener).fetch()


class WeatherFeedTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = lambda: self.now
        self.current = {
            "temperature_c": 17.4,
            "weather_code": 2,
            "icon": "partly_cloudy_day",
            "is_day": True,
            "forecast": sample_forecast(),
            "today_blocks": sample_blocks(),
            "sunrise_time": "07:08",
            "sunset_time": "18:29",
        }

    def test_reuses_complete_weather_payload_as_one_fresh_cache(self):
        provider = FakeWeatherProvider([self.current])
        feed = WeatherFeed(provider, 600, self.clock)
        first = feed.get()
        self.now = 599
        second = feed.get()

        self.assertEqual(first, second)
        self.assertEqual(second["today_blocks"], sample_blocks())
        self.assertEqual(provider.calls, 1)

    def test_returns_stale_last_good_complete_payload_after_refresh_failure(self):
        provider = FakeWeatherProvider([self.current, RuntimeError("upstream down")])
        feed = WeatherFeed(provider, 600, self.clock)
        feed.get()
        self.now = 601
        result = feed.get()

        self.assertTrue(result["stale"])
        self.assertEqual(result["forecast"], sample_forecast())
        self.assertEqual(result["today_blocks"], sample_blocks())
        self.assertEqual(result["sunrise_time"], "07:08")

    def test_cold_failure_is_unavailable(self):
        feed = WeatherFeed(FakeWeatherProvider([RuntimeError("upstream down")]), 600, self.clock)
        with self.assertRaises(WeatherFeedUnavailable):
            feed.get()

    def test_screen_feed_emits_default_three_screen_sequence_and_preserves_overlay(self):
        weather_feed = WeatherFeed(FakeWeatherProvider([self.current]), 600, self.clock)
        departures = DepartureFeed(FixtureProvider(10), "NEM", 60)
        payload = ScreenFeed(departures, weather_feed=weather_feed).get()

        weather_screens = payload["screens"][-3:]
        self.assertEqual([screen["kind"] for screen in weather_screens],
                         ["weather_weekly", "weather_today", "weather_sun"])
        self.assertEqual(weather_screens[0]["days"], sample_forecast())
        self.assertEqual(weather_screens[1]["blocks"], sample_blocks())
        self.assertEqual(weather_screens[2]["sunrise_time"], "07:08")
        self.assertEqual(weather_screens[2]["sunset_time"], "18:29")
        for screen in payload["screens"]:
            self.assertEqual(screen["weather"]["temperature_c"], 17.4)
            self.assertNotIn("forecast", screen["weather"])
            self.assertNotIn("today_blocks", screen["weather"])
            self.assertNotIn("sunrise_time", screen["weather"])

    def test_screen_feed_cold_weather_failure_only_adds_unavailable_weekly_screen(self):
        weather_feed = WeatherFeed(FakeWeatherProvider([RuntimeError("upstream down")]), 600, self.clock)
        departures = DepartureFeed(FixtureProvider(10), "NEM", 60)
        payload = ScreenFeed(departures, weather_feed=weather_feed).get()

        self.assertEqual([screen["kind"] for screen in payload["screens"]],
                         ["rail_combined", "weather_weekly"])
        weekly = payload["screens"][-1]
        self.assertEqual(weekly["source"], "unavailable")
        self.assertTrue(weekly["stale"])
        self.assertEqual(weekly["days"], [])


if __name__ == "__main__":
    unittest.main()
