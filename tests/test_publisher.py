import copy
from datetime import datetime, timedelta, timezone
import unittest

from publisher import Publisher, PublisherConfig


class MemoryStore:
    def __init__(self):
        self.state = {"version": 1, "feeds": {}}
        self.payload = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def publish(self, payload):
        self.payload = copy.deepcopy(payload)


class FakeProvider:
    source = "fake"

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 13, 7, 0, tzinfo=timezone.utc)
        self.utcnow = lambda: self.now
        self.store = MemoryStore()
        self.config = PublisherConfig(
            bucket="test-bucket",
            national_rail_token="test-token",
            thorpe_park_source="off",
            weather_source="off",
        )

    def test_persists_cache_across_separate_publisher_instances(self):
        rail = FakeProvider([[{"time": "08:01", "destination": "Waterloo"}]])
        Publisher(self.config, self.store, rail_provider=rail, utcnow=self.utcnow).run()
        self.now += timedelta(seconds=30)
        Publisher(self.config, self.store, rail_provider=rail, utcnow=self.utcnow).run()

        self.assertEqual(rail.calls, 1)
        self.assertEqual(self.store.payload["screens"][0]["services"][0]["time"], "08:01")
        self.assertEqual(self.store.state["feeds"]["rail"]["last_success_at"], "2026-09-13T07:00:00Z")

    def test_refreshes_after_ttl_and_keeps_last_good_data_stale_on_failure(self):
        rail = FakeProvider([
            [{"time": "08:01", "destination": "Waterloo"}],
            RuntimeError("upstream failure must not leak"),
        ])
        Publisher(self.config, self.store, rail_provider=rail, utcnow=self.utcnow).run()
        self.now += timedelta(seconds=61)
        payload = Publisher(self.config, self.store, rail_provider=rail, utcnow=self.utcnow).run()

        self.assertEqual(rail.calls, 2)
        self.assertTrue(payload["screens"][0]["stale"])
        self.assertEqual(payload["screens"][0]["services"][0]["destination"], "Waterloo")
        self.assertTrue(self.store.state["feeds"]["rail"]["stale"])

    def test_cold_rail_failure_publishes_safe_unavailable_screen(self):
        rail = FakeProvider([RuntimeError("sensitive response")])
        payload = Publisher(self.config, self.store, rail_provider=rail, utcnow=self.utcnow).run()
        screen = payload["screens"][0]

        self.assertEqual(screen["source"], "unavailable")
        self.assertTrue(screen["stale"])
        self.assertEqual(screen["services"], [])

    def test_queue_and_weather_ttls_are_independent_and_contract_is_preserved(self):
        config = PublisherConfig(
            bucket="test-bucket",
            national_rail_token="test-token",
            rail_ttl=60,
            thorpe_park_ttl=300,
            weather_ttl=600,
            thorpe_park_rides=("Hyperia", "Stealth"),
        )
        rail = FakeProvider([[{"time": "08:01", "destination": "Waterloo"}], [{"time": "08:02"}]])
        queues = FakeProvider([[{
            "name": "Hyperia", "open": True, "wait_minutes": 25, "last_updated": "", "land": ""
        }, {
            "name": "Stealth", "open": True, "wait_minutes": 10, "last_updated": "", "land": ""
        }]])
        weather = FakeProvider([{
            "temperature_c": 17.4,
            "weather_code": 2,
            "icon": "partly_cloudy_day",
            "is_day": True,
            "attribution": "Weather data by Open-Meteo.com",
            "attribution_url": "https://open-meteo.com/",
        }])

        first = Publisher(config, self.store, rail, queues, weather, self.utcnow).run()
        self.now += timedelta(seconds=61)
        second = Publisher(config, self.store, rail, queues, weather, self.utcnow).run()

        self.assertEqual(rail.calls, 2)
        self.assertEqual(queues.calls, 1)
        self.assertEqual(weather.calls, 1)
        self.assertEqual([screen["id"] for screen in first["screens"]], ["departures", "thorpe-park"])
        self.assertEqual(second["screens"][1]["rides"][0]["name"], "Hyperia")
        for screen in second["screens"]:
            self.assertIn("weather", screen)
            self.assertEqual(screen["weather"]["temperature_c"], 17.4)


if __name__ == "__main__":
    unittest.main()
