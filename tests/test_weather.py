import io
import json
import unittest
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
        },
        {
            "date": "2026-10-05",
            "weekday": "MON",
            "temperature_max_c": 17.0,
            "temperature_min_c": 10.0,
            "weather_code": 2,
            "icon": "partly_cloudy_day",
        },
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
        return {
            "current": {
                "temperature_2m": 17.36,
                "weather_code": 2,
                "is_day": 1,
            },
            "daily": {
                "time": dates,
                "weather_code": [61, 2, 3, 0, 45, 71, 95, 80][:days],
                "temperature_2m_max": [16.2 + index for index in range(days)],
                "temperature_2m_min": [9.4 + index for index in range(days)],
            },
        }

    def test_fetches_current_and_daily_fields_in_one_request_and_normalizes_response(self):
        captured = {}

        def opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            return io.BytesIO(json.dumps(self._payload()).encode("utf-8"))

        result = OpenMeteoProvider(51.4039, -0.256, opener=opener).fetch()
        query = parse_qs(urlparse(captured["url"]).query)

        self.assertEqual(query["latitude"], ["51.4039"])
        self.assertEqual(query["longitude"], ["-0.256"])
        self.assertEqual(query["current"], ["temperature_2m,weather_code,is_day"])
        self.assertEqual(query["daily"], ["weather_code,temperature_2m_max,temperature_2m_min"])
        self.assertEqual(query["forecast_days"], ["7"])
        self.assertEqual(query["timezone"], ["auto"])
        self.assertEqual(captured["timeout"], 10)
        self.assertEqual(result["temperature_c"], 17.4)
        self.assertEqual(result["weather_code"], 2)
        self.assertEqual(result["icon"], "partly_cloudy_day")
        self.assertTrue(result["is_day"])
        self.assertEqual(result["forecast"], sample_forecast())

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

    def test_rejects_missing_or_malformed_daily_forecast(self):
        payloads = [
            {"current": {"temperature_2m": 12, "weather_code": 3, "is_day": 1}},
            {
                "current": {"temperature_2m": 12, "weather_code": 3, "is_day": 1},
                "daily": {
                    "time": "2026-10-04",
                    "weather_code": [3],
                    "temperature_2m_max": [14],
                    "temperature_2m_min": [8],
                },
            },
            {
                "current": {"temperature_2m": 12, "weather_code": 3, "is_day": 1},
                "daily": {
                    "time": ["bad-date"],
                    "weather_code": [3],
                    "temperature_2m_max": [14],
                    "temperature_2m_min": [8],
                },
            },
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                def opener(url, timeout, payload=payload):
                    del url, timeout
                    return io.BytesIO(json.dumps(payload).encode("utf-8"))

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
        }

    def test_reuses_current_and_forecast_as_one_fresh_cache(self):
        provider = FakeWeatherProvider([self.current])
        feed = WeatherFeed(provider, 600, self.clock)
        first = feed.get()
        self.now = 599
        second = feed.get()

        self.assertEqual(first, second)
        self.assertEqual(second["forecast"], sample_forecast())
        self.assertEqual(provider.calls, 1)

    def test_returns_stale_last_good_current_and_forecast_after_refresh_failure(self):
        provider = FakeWeatherProvider([self.current, RuntimeError("upstream down")])
        feed = WeatherFeed(provider, 600, self.clock)
        feed.get()
        self.now = 601
        result = feed.get()

        self.assertTrue(result["stale"])
        self.assertEqual(result["temperature_c"], 17.4)
        self.assertEqual(result["forecast"], sample_forecast())

    def test_cold_failure_is_unavailable(self):
        feed = WeatherFeed(FakeWeatherProvider([RuntimeError("upstream down")]), 600, self.clock)
        with self.assertRaises(WeatherFeedUnavailable):
            feed.get()

    def test_screen_feed_emits_weekly_weather_and_preserves_current_overlay(self):
        weather_feed = WeatherFeed(FakeWeatherProvider([self.current]), 600, self.clock)
        departures = DepartureFeed(FixtureProvider(10), "NEM", 60)
        payload = ScreenFeed(departures, weather_feed=weather_feed).get()

        weekly = payload["screens"][-1]
        self.assertEqual(weekly["kind"], "weather_weekly")
        self.assertEqual(weekly["days"], sample_forecast())
        self.assertEqual(weekly["duration_seconds"], 8)
        for screen in payload["screens"]:
            self.assertEqual(screen["weather"]["temperature_c"], 17.4)
            self.assertEqual(screen["weather"]["icon"], "partly_cloudy_day")
            self.assertFalse(screen["weather"]["stale"])
            self.assertNotIn("forecast", screen["weather"])

    def test_screen_feed_cold_weather_failure_keeps_departures_and_emits_unavailable_weather(self):
        weather_feed = WeatherFeed(FakeWeatherProvider([RuntimeError("upstream down")]), 600, self.clock)
        departures = DepartureFeed(FixtureProvider(10), "NEM", 60)
        payload = ScreenFeed(departures, weather_feed=weather_feed).get()

        self.assertEqual(payload["screens"][0]["kind"], "rail_combined")
        weekly = payload["screens"][-1]
        self.assertEqual(weekly["kind"], "weather_weekly")
        self.assertEqual(weekly["source"], "unavailable")
        self.assertTrue(weekly["stale"])
        self.assertEqual(weekly["days"], [])


if __name__ == "__main__":
    unittest.main()
