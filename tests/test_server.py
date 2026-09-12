import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from server import (
    ConfigurationError,
    DepartureFeed,
    FeedUnavailable,
    FixtureProvider,
    create_server,
    normalize_darwin_board,
    resolve_bitwarden_secret,
)


class FakeProvider:
    source = "test"

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return result


class SecretTests(unittest.TestCase):
    def test_resolves_value_without_returning_metadata(self):
        token = "private-test-token"

        def runner(*args, **kwargs):
            class Result:
                stdout = json.dumps({"id": "ignored", "value": token})
            return Result()

        result = resolve_bitwarden_secret("8a5912b2-73d9-4b64-a072-b4c3011910fd", runner)
        self.assertEqual(result, token)

    def test_resolution_error_does_not_expose_command_output(self):
        token = "must-not-leak"

        def runner(*args, **kwargs):
            class Result:
                stdout = token
            return Result()

        with self.assertRaises(ConfigurationError) as raised:
            resolve_bitwarden_secret("8a5912b2-73d9-4b64-a072-b4c3011910fd", runner)
        self.assertNotIn(token, str(raised.exception))


class NormalizationTests(unittest.TestCase):
    def test_normalizes_statuses_platforms_destinations_and_reasons(self):
        board = {
            "trainServices": {
                "service": [
                    {"std": "12:04", "etd": "On time", "platform": "1", "destination": {"location": [{"locationName": "Waterloo"}]}},
                    {"std": "12:16", "etd": "12:18", "platform": None, "destination": {"location": [{"locationName": "Shepperton"}]}},
                    {"std": "12:27", "etd": "Delayed", "platform": "2", "destination": {"location": [{"locationName": "Guildford"}]}},
                    {"std": "12:39", "etd": "Cancelled", "isCancelled": True, "cancelReason": "Signal failure", "destination": {"location": [{"locationName": "Woking"}]}},
                ]
            }
        }
        services = normalize_darwin_board(board)
        self.assertEqual(services[0]["status"], "On time")
        self.assertEqual(services[1]["status"], "12:18")
        self.assertEqual(services[1]["platform"], "-")
        self.assertEqual(services[2]["status"], "Delayed")
        self.assertTrue(services[3]["cancelled"])
        self.assertEqual(services[3]["delay_reason"], "Signal failure")
        self.assertEqual(services[3]["destination"], "Woking")

    def test_empty_board(self):
        self.assertEqual(normalize_darwin_board({"trainServices": None}), [])


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.clock = lambda: self.now
        self.utcnow = lambda: __import__("datetime").datetime(2026, 9, 12, 12, 0, tzinfo=__import__("datetime").timezone.utc)

    def test_reuses_fresh_cache(self):
        provider = FakeProvider([[{"time": "12:04"}]])
        feed = DepartureFeed(provider, "NEM", 60, self.clock, self.utcnow)
        first = feed.get()
        self.now = 59
        second = feed.get()
        self.assertEqual(first, second)
        self.assertEqual(provider.calls, 1)

    def test_returns_stale_last_good_after_refresh_failure(self):
        provider = FakeProvider([[{"time": "12:04"}], RuntimeError("upstream details")])
        feed = DepartureFeed(provider, "NEM", 60, self.clock, self.utcnow)
        feed.get()
        self.now = 61
        result = feed.get()
        self.assertTrue(result["stale"])
        self.assertEqual(result["services"], [{"time": "12:04"}])

    def test_cold_failure_is_unavailable(self):
        provider = FakeProvider([RuntimeError("upstream details")])
        feed = DepartureFeed(provider, "NEM", 60, self.clock, self.utcnow)
        with self.assertRaises(FeedUnavailable):
            feed.get()


class HttpTests(unittest.TestCase):
    def _run_server(self, provider):
        feed = DepartureFeed(provider, "NEM", 60)
        server = create_server(feed, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return "http://127.0.0.1:{}".format(server.server_address[1])

    def test_departures_endpoint_contract(self):
        base = self._run_server(FixtureProvider(10))
        with urlopen(base + "/api/departures") as response:
            payload = json.load(response)
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/json")
        self.assertEqual(payload["station"], "NEM")
        self.assertEqual(payload["source"], "fixture")
        self.assertFalse(payload["stale"])
        self.assertLessEqual(len(payload["services"]), 10)

    def test_cold_failure_is_safe_503(self):
        base = self._run_server(FakeProvider([RuntimeError("sensitive upstream response")]))
        with self.assertRaises(HTTPError) as raised:
            urlopen(base + "/api/departures")
        error = raised.exception
        self.addCleanup(error.close)
        self.assertEqual(error.code, 503)
        body = error.read().decode("utf-8")
        self.assertEqual(json.loads(body), {"error": "departures_unavailable"})
        self.assertNotIn("sensitive", body)


if __name__ == "__main__":
    unittest.main()
