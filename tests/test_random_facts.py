"""Contracts for the optional random-fact feed and its durable novelty safeguard."""

import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from random_facts import RandomFactProvider
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import (
    default_runtime_config, schema_metadata, validate_feed_patch,
    validate_runtime_config,
)


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


class FakeFactProvider:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    def fetch(self):
        value = self.values[self.calls]
        self.calls += 1
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def screen_by_id(payload, screen_id):
    return next(screen for screen in payload["screens"] if screen["id"] == screen_id)


class RandomFactTests(unittest.TestCase):
    def test_defaults_schema_validation_and_migration(self):
        config = default_runtime_config({})
        self.assertFalse(config["feeds"]["random_fact"]["enabled"])
        self.assertEqual(config["feeds"]["random_fact"]["display_every_cycles"], 1)
        self.assertEqual(config["feeds"]["random_fact"]["poll_seconds"], 3600)
        self.assertEqual(config["feeds"]["random_fact"]["screen_duration_seconds"], 15)
        schema = schema_metadata()["feeds"]["random_fact"]
        self.assertIn("enabled", schema["mutable_fields"])
        self.assertIn("display_every_cycles", schema["mutable_fields"])
        self.assertIn("poll_seconds", schema["mutable_fields"])
        self.assertIn("screen_duration_seconds", schema["mutable_fields"])
        self.assertEqual(validate_feed_patch("random_fact", {"display_every_cycles": 3}), {"display_every_cycles": 3})
        with self.assertRaises(ValueError):
            validate_feed_patch("random_fact", {"display_every_cycles": 7})
        config["feeds"]["dad_joke"]["display_every_cycles"] = 4
        del config["feeds"]["random_fact"]
        migrated = validate_runtime_config(config)
        self.assertFalse(migrated["feeds"]["random_fact"]["enabled"])
        self.assertEqual(migrated["feeds"]["dad_joke"]["display_every_cycles"], 4)

    def test_provider_fetch_and_normalize(self):
        body = b'{"id":"one","text":"The world\\u2019s first fact!","source":"example.net","language":"en"}'
        with patch("random_facts.urlopen", return_value=BytesIO(body)) as opener:
            result = RandomFactProvider().fetch()
        self.assertEqual(result, {"id": "one", "text": "The world's first fact!", "source": "example.net"})
        self.assertEqual(opener.call_args.kwargs["timeout"], 5)
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("api/v2/facts/random?language=en", request.full_url)

    def test_provider_rejects_bad_responses(self):
        for body in (
            b"[]",
            b'{"id":"one","text":"","language":"en"}',
            b'{"id":"","text":"text","language":"en"}',
            b'{"id":"one","text":"Hallo","language":"de"}',
        ):
            with self.subTest(body=body), patch("random_facts.urlopen", return_value=BytesIO(body)):
                with self.assertRaises(ValueError):
                    RandomFactProvider().fetch()

    def test_fact_refresh_is_independent_and_reuses_cache(self):
        runtime = default_runtime_config({
            "LED_THORPE_PARK_SOURCE": "off",
            "LED_WEATHER_SOURCE": "off",
            "LED_CALENDAR_SOURCE": "off",
        })
        runtime["feeds"]["departures"]["enabled"] = False
        runtime["feeds"]["random_fact"]["enabled"] = True
        runtime["feeds"]["random_fact"]["display_every_cycles"] = 3
        runtime["feeds"]["random_fact"]["screen_duration_seconds"] = 20
        store = MemoryStore()
        provider = FakeFactProvider([
            {"id": "1", "text": "The first fact", "source": "example.net"},
            {"id": "2", "text": "The first fact", "source": "example.net"},
            {"id": "3", "text": "Another fact", "source": "example.net"},
            {"id": "4", "text": "Another fact", "source": "example.net"},
            {"id": "5", "text": "Another fact", "source": "example.net"},
            {"id": "6", "text": "Another fact", "source": "example.net"},
        ])
        clock = [datetime(2026, 10, 8, tzinfo=timezone.utc)]
        kwargs = dict(
            config=PublisherConfig(bucket="test-bucket", national_rail_token="not-needed"),
            store=store,
            utcnow=lambda: clock[0],
            runtime_config_store=StaticRuntimeConfigStore(runtime),
            fact_provider=provider,
        )
        first = Publisher(**kwargs).run()
        screen = screen_by_id(first, "random-fact")
        self.assertEqual(screen["kind"], "random_fact")
        self.assertEqual(screen["fact"], "The first fact")
        self.assertEqual(screen["display_every_cycles"], 3)
        self.assertEqual(screen["duration_seconds"], 20)
        self.assertEqual(provider.calls, 1)
        clock[0] += timedelta(minutes=15)
        second = Publisher(**kwargs).run()
        self.assertEqual(provider.calls, 1)
        self.assertEqual(screen_by_id(second, "random-fact")["fact"], "The first fact")
        clock[0] += timedelta(hours=1)
        third = Publisher(**kwargs).run()
        self.assertEqual(provider.calls, 3)
        self.assertEqual(screen_by_id(third, "random-fact")["fact"], "Another fact")
        self.assertEqual(store.state["feeds"]["random_fact"]["data"]["history"], ["The first fact", "Another fact"])
        clock[0] += timedelta(hours=1)
        fourth = Publisher(**kwargs).run()
        self.assertEqual(provider.calls, 6)
        self.assertTrue(screen_by_id(fourth, "random-fact")["stale"])
        self.assertEqual(screen_by_id(fourth, "random-fact")["fact"], "Another fact")

    def test_lambda_packaging_includes_both_novelty_providers(self):
        package_script = (ROOT / "scripts" / "package-lambda.sh").read_text()
        self.assertIn('backend/dad_jokes.py', package_script)
        self.assertIn('backend/random_facts.py', package_script)

    def test_disabled_fact_does_not_fetch(self):
        runtime = default_runtime_config({
            "LED_THORPE_PARK_SOURCE": "off",
            "LED_WEATHER_SOURCE": "off",
            "LED_CALENDAR_SOURCE": "off",
        })
        runtime["feeds"]["departures"]["enabled"] = False
        store = MemoryStore()
        provider = FakeFactProvider([])
        result = Publisher(
            PublisherConfig(bucket="test-bucket", national_rail_token="not-needed"), store,
            runtime_config_store=StaticRuntimeConfigStore(runtime),
            fact_provider=provider,
        ).run()
        self.assertEqual(result["screens"], [])
        self.assertEqual(provider.calls, 0)


if __name__ == "__main__":
    unittest.main()
