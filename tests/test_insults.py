import copy
import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import config_api
import publisher
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

    def test_gc_endpoint_requires_confirmation_and_handles_dispatch_failures(self):
        event = {
            "rawPath": "/api/control/v1/maintenance/gc",
            "requestContext": {"http": {"method": "POST"}},
            "body": json.dumps({"confirm": False}),
        }
        env = {
            "RUNTIME_CONFIG_TABLE": "test-table",
            "STATE_BUCKET": "test-bucket",
            "PUBLISHER_FUNCTION_NAME": "test-publisher",
        }
        with patch.dict(config_api.os.environ, env, clear=True), \
             patch.object(config_api, "authenticate_access", return_value=("human:admin", {})), \
             patch.object(config_api, "RuntimeConfigStore"), \
             patch.object(config_api, "StatusStore"), \
             patch.object(config_api, "PublisherInvoker") as invoke_class:
            response = config_api.lambda_handler(event, None)
            self.assertEqual(response["statusCode"], 400)
            invoke_class.assert_not_called()

            event["body"] = json.dumps({"confirm": True})
            response = config_api.lambda_handler(event, None)
            self.assertEqual(response["statusCode"], 202)
            self.assertIn("requested", json.loads(response["body"])["message"])
            invoke_class.return_value.invoke.assert_called_once_with(
                b'{"source":"runtime-control-api","action":"garbage_collect"}'
            )

            invoke_class.return_value.invoke.side_effect = RuntimeError("offline")
            response = config_api.lambda_handler(event, None)
            self.assertEqual(response["statusCode"], 503)
            self.assertIn("could not be requested", json.loads(response["body"])["error"])

    def test_gc_command_collects_before_publishing(self):
        execution = []
        backend = Mock()
        backend.run.side_effect = lambda: execution.append("publish") or {"screens": []}
        with patch.object(publisher, "_PUBLISHER", backend), \
             patch.object(publisher.gc, "collect", side_effect=lambda: execution.append("collect") or 0):
            result = publisher.lambda_handler({"action": "garbage_collect"}, None)
        self.assertEqual(execution, ["collect", "publish"])
        self.assertTrue(result["published"])

    def test_admin_links_insult_to_joke_and_fact(self):
        html = (ROOT / "simulator/admin.html").read_text()
        self.assertIn('card(\'insult_of_hour\')', html)
        self.assertIn('href="#insult-of-hour"', html)
        self.assertIn('window.confirm(', html)
        self.assertIn("runGarbageCollection()", html)

    def test_admin_schema_exposes_hourly_controls(self):
        config = default_runtime_config({})
        self.assertFalse(config["feeds"]["insult_of_hour"]["enabled"])
        schema = schema_metadata()["feeds"]["insult_of_hour"]
        self.assertEqual(schema["label"], "Insult of the Hour")
        self.assertEqual(config["feeds"]["insult_of_hour"]["poll_seconds"], 3600)
        self.assertEqual(schema["fields"]["poll_seconds"]["minimum"], 3600)


if __name__ == "__main__":
    unittest.main()
