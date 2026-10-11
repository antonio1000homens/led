import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from insults import InsultProvider
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import (default_runtime_config, schema_metadata, validate_feed_patch,
                            validate_runtime_config, RuntimeConfigValidationError)


class MemoryStore:
    def __init__(self):
        self.state = {"version": 2, "feeds": {}}
        self.payload = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def publish(self, payload):
        self.payload = copy.deepcopy(payload)


class FakeInsultProvider:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def fetch(self):
        value = self.values[self.calls]
        self.calls += 1
        if isinstance(value, Exception):
            raise value
        return value


class InsultTests(unittest.TestCase):
    def test_provider_accepts_insult_and_rejects_error_or_malformed_payload(self):
        with patch("insults.urlopen", return_value=BytesIO(b'{"insult":"You\\u2019re tedious.","error":false}')) as opener:
            self.assertEqual(InsultProvider().fetch(), "You're tedious.")
            self.assertEqual(opener.call_args.kwargs["timeout"], 5)
            self.assertEqual(opener.call_args.args[0].full_url, InsultProvider.URL)
        for body in (b"[]", b'{"error":true}', b'{"insult":""}'):
            with self.subTest(body=body), patch("insults.urlopen", return_value=BytesIO(body)):
                with self.assertRaises(ValueError):
                    InsultProvider().fetch()

    def test_hourly_screen_refreshes_and_keeps_last_good_value_on_failure(self):
        runtime = default_runtime_config({"LED_WEATHER_SOURCE": "off", "LED_THORPE_PARK_SOURCE": "off"})
        runtime["feeds"]["departures"]["enabled"] = False
        runtime["feeds"]["insult_of_hour"]["enabled"] = True
        store = MemoryStore()
        now = [datetime(2026, 10, 11, tzinfo=timezone.utc)]
        provider = FakeInsultProvider(["First insult", "Second insult", RuntimeError("offline")])
        kwargs = dict(
            config=PublisherConfig(bucket="test", national_rail_token="unused"),
            store=store,
            utcnow=lambda: now[0],
            runtime_config_store=StaticRuntimeConfigStore(runtime),
            insult_provider=provider,
        )
        first = Publisher(**kwargs).run()
        screen = next(item for item in first["screens"] if item["kind"] == "insult_of_hour")
        self.assertEqual(screen["insult"], "First insult")
        self.assertEqual(screen["items"][0]["insult"], "First insult")
        now[0] += timedelta(seconds=3599)
        Publisher(**kwargs).run()
        self.assertEqual(provider.calls, 1)
        now[0] += timedelta(seconds=2)
        refreshed = Publisher(**kwargs).run()
        refreshed_screen = next(item for item in refreshed["screens"] if item["kind"] == "insult_of_hour")
        self.assertEqual(refreshed_screen["insult"], "Second insult")
        now[0] += timedelta(seconds=3601)
        failed = Publisher(**kwargs).run()
        failed_screen = next(item for item in failed["screens"] if item["kind"] == "insult_of_hour")
        self.assertEqual(failed_screen["insult"], "Second insult")
        self.assertTrue(failed_screen["stale"])

    def test_initial_failure_shows_fallback_without_retrying_before_one_hour(self):
        runtime = default_runtime_config({"LED_WEATHER_SOURCE": "off", "LED_THORPE_PARK_SOURCE": "off"})
        runtime["feeds"]["departures"]["enabled"] = False
        runtime["feeds"]["insult_of_hour"]["enabled"] = True
        store = MemoryStore()
        now = [datetime(2026, 10, 11, tzinfo=timezone.utc)]
        provider = FakeInsultProvider([TimeoutError("unavailable"), "Recovered insult"])
        publisher = Publisher(
            config=PublisherConfig(bucket="test", national_rail_token="unused"),
            store=store, utcnow=lambda: now[0],
            runtime_config_store=StaticRuntimeConfigStore(runtime),
            insult_provider=provider,
        )
        first = publisher.run()
        fallback = next(screen for screen in first["screens"] if screen["kind"] == "insult_of_hour")
        self.assertEqual(fallback["insult"], "Insult temporarily unavailable")
        self.assertTrue(fallback["stale"])
        self.assertEqual(fallback["items"], [])
        now[0] += timedelta(seconds=3599)
        publisher.run()
        self.assertEqual(provider.calls, 1)
        now[0] += timedelta(seconds=2)
        recovered = publisher.run()
        screen = next(screen for screen in recovered["screens"] if screen["kind"] == "insult_of_hour")
        self.assertEqual(screen["insult"], "Recovered insult")
        self.assertFalse(screen["stale"])
        self.assertEqual(provider.calls, 2)

    def test_legacy_config_and_interval_guard(self):
        config = default_runtime_config({})
        config["feeds"].pop("insult_of_hour")
        self.assertFalse(validate_runtime_config(config)["feeds"]["insult_of_hour"]["enabled"])
        config["feeds"]["insult_of_hour"] = {
            "enabled": True, "poll_seconds": 60, "screen_duration_seconds": 15,
        }
        self.assertEqual(validate_runtime_config(config)["feeds"]["insult_of_hour"]["poll_seconds"], 3600)
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("insult_of_hour", {"poll_seconds": 60})
        self.assertEqual(validate_feed_patch("insult_of_hour", {"poll_seconds": 7200})["poll_seconds"], 7200)

    def test_admin_schema_exposes_hourly_controls(self):
        config = default_runtime_config({})
        self.assertFalse(config["feeds"]["insult_of_hour"]["enabled"])
        schema = schema_metadata()["feeds"]["insult_of_hour"]
        self.assertEqual(schema["label"], "Insult of the Hour")
        self.assertEqual(config["feeds"]["insult_of_hour"]["poll_seconds"], 3600)
        self.assertEqual(schema["fields"]["poll_seconds"]["minimum"], 3600)


if __name__ == "__main__":
    unittest.main()
