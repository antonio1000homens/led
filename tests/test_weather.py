import io
import json
import unittest

from server import DepartureFeed, FixtureProvider, ScreenFeed
from weather import OpenMeteoProvider, WeatherFeed, WeatherFeedUnavailable, weather_icon


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
    def test_fetches_only_current_fields_and_normalizes_response(self):
        captured = {}

        def opener(url, timeout):
            captured["url"] = url
            captured["timeout"] = timeout
            payload = {
                "current": {
                    "temperature_2m": 17.36,
                    "weather_code": 2,
                    "is_day": 1,
                }
            }
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        result = OpenMeteoProvider(51.4039, -0.256, opener=opener).fetch()

        self.assertIn("latitude=51.4039", captured["url"])
        self.assertIn("longitude=-0.256", captured["url"])
        self.assertIn("temperature_2m", captured["url"])
        self.assertIn("weather_code", captured["url"])
        self.assertIn("is_day", captured["url"])
        self.assertEqual(captured["timeout"], 10)
        self.assertEqual(result["temperature_c"], 17.4)
        self.assertEqual(result["weather_code"], 2)
        self.assertEqual(result["icon"], "partly_cloudy_day")
        self.assertTrue(result["is_day"])
        self.assertEqual(result["source"] if "source" in result else "open_meteo", "open_meteo")

    def test_rejects_response_without_current_weather(self):
        def opener(url, timeout):
            return io.BytesIO(b"{}")

        with self.assertRaises(WeatherFeedUnavailable):
            OpenMeteoProvider(51.4, -0.25, opener=opener).fetch()


class WeatherFeedTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = lambda: self.now

    def test_reuses_fresh_cache(self):
        provider = FakeWeatherProvider([
            {"temperature_c": 17.4, "weather_code": 2, "icon": "partly_cloudy_day", "is_day": True}
        ])
        feed = WeatherFeed(provider, 600, self.clock)
        first = feed.get()
        self.now = 599
        second = feed.get()
        self.assertEqual(first, second)
        self.assertEqual(provider.calls, 1)

    def test_returns_stale_last_good_after_refresh_failure(self):
        provider = FakeWeatherProvider([
            {"temperature_c": 17.4, "weather_code": 2, "icon": "partly_cloudy_day", "is_day": True},
            RuntimeError("upstream down"),
        ])
        feed = WeatherFeed(provider, 600, self.clock)
        feed.get()
        self.now = 601
        result = feed.get()
        self.assertTrue(result["stale"])
        self.assertEqual(result["temperature_c"], 17.4)

    def test_cold_failure_is_unavailable(self):
        feed = WeatherFeed(FakeWeatherProvider([RuntimeError("upstream down")]), 600, self.clock)
        with self.assertRaises(WeatherFeedUnavailable):
            feed.get()

    def test_screen_feed_copies_weather_to_every_screen(self):
        weather_feed = WeatherFeed(
            FakeWeatherProvider([
                {"temperature_c": 17.4, "weather_code": 2, "icon": "partly_cloudy_day", "is_day": True}
            ]),
            600,
            self.clock,
        )
        departures = DepartureFeed(FixtureProvider(10), "NEM", 60)
        payload = ScreenFeed(departures, weather_feed=weather_feed).get()

        self.assertTrue(payload["screens"])
        for screen in payload["screens"]:
            self.assertEqual(screen["weather"]["temperature_c"], 17.4)
            self.assertEqual(screen["weather"]["icon"], "partly_cloudy_day")
            self.assertFalse(screen["weather"]["stale"])


if __name__ == "__main__":
    unittest.main()
