import io
import json
import unittest
from datetime import datetime, timezone

from queue_times import (
    QueueFeedUnavailable,
    QueueTimesProvider,
    ThorpeParkFeed,
    normalize_queue_times,
)
from server import DepartureFeed, FixtureProvider, ScreenFeed


class FakeQueueProvider:
    source = "queue_times"

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


class NormalizationTests(unittest.TestCase):
    def test_flattens_lands_and_top_level_rides(self):
        payload = {
            "rides": [
                {"name": "Flying Fish", "is_open": True, "wait_time": 5, "last_updated": "2026-09-12T12:00:00Z"}
            ],
            "lands": [
                {
                    "name": "Coasters",
                    "rides": [
                        {"name": "Hyperia", "is_open": True, "wait_time": "45", "last_updated": "2026-09-12T12:00:00Z"},
                        {"name": "Stealth", "is_open": False, "wait_time": 0, "last_updated": "2026-09-12T12:00:00Z"},
                    ],
                }
            ],
        }
        rides = normalize_queue_times(payload)
        self.assertEqual([ride["name"] for ride in rides], ["Flying Fish", "Hyperia", "Stealth"])
        self.assertEqual(rides[1]["wait_minutes"], 45)
        self.assertEqual(rides[1]["land"], "Coasters")
        self.assertFalse(rides[2]["open"])

    def test_deduplicates_rides_case_insensitively(self):
        payload = {
            "rides": [{"name": "Hyperia", "is_open": True, "wait_time": 20}],
            "lands": [{"name": "Coasters", "rides": [{"name": "HYPERIA", "is_open": True, "wait_time": 40}]}],
        }
        rides = normalize_queue_times(payload)
        self.assertEqual(len(rides), 1)
        self.assertEqual(rides[0]["wait_minutes"], 20)


class ProviderTests(unittest.TestCase):
    def test_fetches_thorpe_park_id_2_without_credentials(self):
        requests = []
        payload = {"lands": [{"name": "Coasters", "rides": [{"name": "Hyperia", "is_open": True, "wait_time": 30}]}]}

        def opener(request, timeout):
            requests.append((request, timeout))
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        rides = QueueTimesProvider(opener=opener).fetch()
        self.assertEqual(requests[0][0].full_url, "https://queue-times.com/parks/2/queue_times.json")
        self.assertEqual(requests[0][1], 10)
        self.assertEqual(rides[0]["name"], "Hyperia")


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = lambda: self.now
        self.utcnow = lambda: datetime(2026, 9, 12, 12, 0, tzinfo=timezone.utc)
        self.rides = [{"name": "Hyperia", "open": True, "wait_minutes": 45, "last_updated": "", "land": "Coasters"}]

    def test_reuses_five_minute_cache(self):
        provider = FakeQueueProvider([self.rides])
        feed = ThorpeParkFeed(provider, 300, self.clock, self.utcnow)
        first = feed.get()
        self.now = 299
        second = feed.get()
        self.assertEqual(first, second)
        self.assertEqual(provider.calls, 1)

    def test_returns_stale_last_good_after_refresh_failure(self):
        provider = FakeQueueProvider([self.rides, RuntimeError("upstream down")])
        feed = ThorpeParkFeed(provider, 300, self.clock, self.utcnow)
        feed.get()
        self.now = 301
        result = feed.get()
        self.assertTrue(result["stale"])
        self.assertEqual(result["rides"], self.rides)

    def test_cold_failure_is_unavailable(self):
        feed = ThorpeParkFeed(FakeQueueProvider([RuntimeError("upstream down")]), 300, self.clock, self.utcnow)
        with self.assertRaises(QueueFeedUnavailable):
            feed.get()


class ScreenFeedTests(unittest.TestCase):
    def test_cycles_queue_screen_after_departures_in_configured_order(self):
        queue_rides = [
            {"name": "The Swarm", "open": True, "wait_minutes": 15},
            {"name": "Hyperia", "open": True, "wait_minutes": 45},
            {"name": "Stealth", "open": False, "wait_minutes": 0},
            {"name": "Colossus", "open": True, "wait_minutes": 20},
        ]
        rail = DepartureFeed(FixtureProvider(10), "NEM", 60)
        queues = ThorpeParkFeed(FakeQueueProvider([queue_rides]), 300)
        payload = ScreenFeed(
            rail,
            queue_feed=queues,
            queue_ride_names=("Hyperia", "Stealth", "The Swarm", "Colossus"),
        ).get()

        self.assertEqual([screen["id"] for screen in payload["screens"]], ["departures", "thorpe-park"])
        screen = payload["screens"][1]
        self.assertEqual(screen["kind"], "theme_park_queues")
        self.assertEqual(screen["duration_seconds"], 8)
        self.assertEqual(
            [ride["name"] for ride in screen["rides"]],
            ["Hyperia", "Stealth", "The Swarm", "Colossus"],
        )
        self.assertEqual(screen["attribution"], "Powered by Queue-Times.com")

    def test_queue_screen_duration_grows_for_longer_ride_lists(self):
        names = ("Hyperia", "Stealth", "The Swarm", "Colossus", "Nemesis Inferno", "Rush", "Detonator")
        queue_rides = [
            {"name": name, "open": True, "wait_minutes": index * 5}
            for index, name in enumerate(names, start=1)
        ]
        rail = DepartureFeed(FixtureProvider(10), "NEM", 60)
        queues = ThorpeParkFeed(FakeQueueProvider([queue_rides]), 300)
        screen = ScreenFeed(rail, queue_feed=queues, queue_ride_names=names).get()["screens"][1]

        self.assertEqual(len(screen["rides"]), 7)
        self.assertEqual(screen["duration_seconds"], 9)

    def test_queue_failure_does_not_remove_departures(self):
        rail = DepartureFeed(FixtureProvider(10), "NEM", 60)
        queues = ThorpeParkFeed(FakeQueueProvider([RuntimeError("queue API down")]), 300)
        payload = ScreenFeed(rail, queue_feed=queues).get()

        self.assertEqual(payload["screens"][0]["source"], "fixture")
        self.assertEqual(payload["screens"][1]["source"], "unavailable")
        self.assertTrue(payload["screens"][1]["stale"])


if __name__ == "__main__":
    unittest.main()
