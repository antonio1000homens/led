import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import jwt

import config_api
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore, _runtime_defaults
from runtime_config import MAX_POLL_SECONDS, MAX_SCREEN_DURATION_SECONDS, default_runtime_config


ROOT = Path(__file__).resolve().parents[1]


class MemoryStore:
    def __init__(self, state=None):
        self.state = copy.deepcopy(state or {"version": 2, "feeds": {}})
        self.payload = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def publish(self, payload):
        self.payload = copy.deepcopy(payload)


class FakeProvider:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        result = self.results[self.calls]
        self.calls += 1
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)


class EmptyStatusStore:
    def feed_state(self):
        return {}

    def screens_state(self):
        return {}


class FakeRuntimeStore:
    def __init__(self):
        self.config = default_runtime_config({})
        self.config.update(config_version=4, updated_at="2026-09-13T17:00:00Z", updated_by="human:old@example.com")

    def ensure(self):
        return copy.deepcopy(self.config)

    def patch_feed(self, feed_id, body, **kwargs):
        updated = copy.deepcopy(self.config)
        updated["feeds"][feed_id].update(body)
        updated["config_version"] = kwargs["expected_version"] + 1
        updated["updated_by"] = kwargs["updated_by"]
        self.config = updated
        return copy.deepcopy(updated), list(body)


class FailingInvoker:
    def __init__(self, function_name):
        self.function_name = function_name

    def invoke(self):
        raise RuntimeError("synthetic invoke failure")


class Pr37ReviewRegressionTests(unittest.TestCase):
    def test_deployment_defaults_are_bounded_before_they_can_be_seeded(self):
        config = default_runtime_config(
            {
                "LED_CACHE_SECONDS": str(MAX_POLL_SECONDS + 1000),
                "LED_CHESSINGTON_CACHE_SECONDS": str(MAX_POLL_SECONDS + 2000),
                "LED_CALENDAR_DURATION_SECONDS": str(MAX_SCREEN_DURATION_SECONDS + 100),
            }
        )
        self.assertEqual(config["feeds"]["departures"]["poll_seconds"], MAX_POLL_SECONDS)
        self.assertEqual(config["feeds"]["chessington"]["poll_seconds"], MAX_POLL_SECONDS)
        self.assertEqual(config["feeds"]["calendar"]["screen_duration_seconds"], MAX_SCREEN_DURATION_SECONDS)

    def test_publisher_fallback_carries_chessington_deployment_defaults(self):
        config = PublisherConfig(
            bucket="test-bucket",
            national_rail_token="token",
            chessington_ttl=777,
            chessington_rides=("Vampire", "Croc Drop"),
        )
        runtime = _runtime_defaults(config)
        self.assertEqual(runtime["feeds"]["chessington"]["poll_seconds"], 777)
        self.assertEqual(runtime["feeds"]["chessington"]["rides"], ["Vampire", "Croc Drop"])

    def test_legacy_queues_cache_is_migrated_before_a_provider_failure(self):
        cached_ride = {"name": "Hyperia", "open": True, "wait_minutes": 20}
        store = MemoryStore(
            {
                "version": 2,
                "feeds": {
                    "queues": {
                        "last_attempt_at": "2026-09-13T06:00:00Z",
                        "last_success_at": "2026-09-13T06:00:00Z",
                        "stale": False,
                        "data": {"park": "Thorpe Park", "source": "queue_times", "rides": [cached_ride]},
                    }
                },
            }
        )
        runtime = default_runtime_config({"LED_WEATHER_SOURCE": "off", "LED_CALENDAR_SOURCE": "off"})
        runtime["feeds"]["departures"]["enabled"] = False
        runtime["feeds"]["chessington"]["enabled"] = False
        runtime["feeds"]["thorpe_park"]["rides"] = ["Hyperia"]
        queues = FakeProvider([RuntimeError("Queue-Times unavailable")])
        publisher = Publisher(
            PublisherConfig(bucket="test-bucket", national_rail_token="token", weather_source="off"),
            store,
            queue_provider=queues,
            utcnow=lambda: datetime(2026, 9, 13, 7, 0, tzinfo=timezone.utc),
            runtime_config_store=StaticRuntimeConfigStore(runtime),
        )

        payload = publisher.run()

        self.assertEqual(queues.calls, 1)
        self.assertNotIn("queues", store.state["feeds"])
        self.assertIn("thorpe_park", store.state["feeds"])
        self.assertTrue(store.state["feeds"]["thorpe_park"]["stale"])
        queue_screen = next(screen for screen in payload["screens"] if screen["id"] == "queue-times")
        park = next(park for park in queue_screen["parks"] if park["feed_id"] == "thorpe_park")
        self.assertEqual([ride["name"] for ride in park["rides"]], ["Hyperia"])
        self.assertTrue(park["stale"])

    def test_config_payload_does_not_make_live_queue_times_calls(self):
        config = default_runtime_config({})
        payload = config_api._config_payload(config, EmptyStatusStore())
        self.assertEqual(
            payload["schema"]["feeds"]["thorpe_park"]["available_rides"],
            config["feeds"]["thorpe_park"]["rides"],
        )
        self.assertEqual(
            payload["schema"]["feeds"]["chessington"]["available_rides"],
            config["feeds"]["chessington"]["rides"],
        )

    def test_missing_configured_ride_remains_an_allowed_option(self):
        config = default_runtime_config({})
        config["feeds"]["thorpe_park"]["rides"] = ["Hyperia", "Renamed Ride"]

        class Status:
            def feed_state(self):
                return {"thorpe_park": {"data": {"rides": [{"name": "Hyperia"}]}}}

        options = config_api.ride_options("thorpe_park", config, Status(), allow_live_lookup=False)
        self.assertEqual(options, ["Hyperia", "Renamed Ride"])

    def test_jwk_fetch_timeout_is_bounded_below_lambda_timeout(self):
        config_api._JWK_CLIENTS.clear()
        with patch.object(jwt, "PyJWKClient") as constructor:
            config_api._jwt_client("https://example.cloudflareaccess.com")
        constructor.assert_called_once_with(
            "https://example.cloudflareaccess.com/cdn-cgi/access/certs",
            cache_keys=True,
            lifespan=3600,
            timeout=config_api.JWK_FETCH_TIMEOUT_SECONDS,
        )
        self.assertLess(config_api.JWK_FETCH_TIMEOUT_SECONDS, 15)

    def test_committed_patch_is_success_even_if_immediate_rebuild_trigger_fails(self):
        runtime = FakeRuntimeStore()
        event = {
            "rawPath": "/api/control/v1/feeds/departures",
            "requestContext": {"http": {"method": "PATCH"}, "requestId": "req-trigger-failure"},
            "headers": {"If-Match": '"4"'},
            "body": json.dumps({"enabled": False}),
        }
        env = {
            "RUNTIME_CONFIG_TABLE": "table",
            "STATE_BUCKET": "bucket",
            "PUBLISHER_FUNCTION_NAME": "publisher",
        }
        with patch.dict(config_api.os.environ, env, clear=True), \
             patch.object(config_api, "authenticate_access", return_value=("human:admin@example.com", {})), \
             patch.object(config_api, "RuntimeConfigStore", return_value=runtime), \
             patch.object(config_api, "StatusStore", return_value=EmptyStatusStore()), \
             patch.object(config_api, "PublisherInvoker", FailingInvoker):
            response = config_api.lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertEqual(payload["config_version"], 5)
        self.assertFalse(payload["feeds"]["departures"]["enabled"])
        self.assertFalse(payload["rebuild_triggered"])

    def test_admin_preserves_other_dirty_cards_and_reports_delayed_rebuild(self):
        source = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")
        self.assertIn("function captureDirtyDrafts", source)
        self.assertIn("function restoreDirtyDrafts", source)
        self.assertIn("drafts=captureDirtyDrafts(feedId)", source)
        self.assertIn("restoreDirtyDrafts(drafts)", source)
        self.assertIn("data.rebuild_triggered===false", source)
        self.assertIn("scheduled publisher will apply it on its next run", source)


if __name__ == "__main__":
    unittest.main()
