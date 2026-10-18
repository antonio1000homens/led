"""Regress recycling admin/firmware policy without changing the MQTT protocol."""
import copy
import unittest
from datetime import datetime, timezone
from pathlib import Path

from config_api import _status_payload
from mqtt_screens import MqttScreenState
from runtime_config import (
    RuntimeConfigValidationError, default_runtime_config, schema_metadata,
    validate_feed_patch, validate_runtime_config,
)
from screen_client import ClockState, ScreenRotation


def timestamp(iso):
    return int(datetime.fromisoformat(iso).timestamp())


def snapshot(collection_date="2026-10-13", expires_at="2026-10-14T00:00:00+01:00"):
    return {
        "schema_version": 1, "event": "upsert",
        "published_at": "2026-10-07T09:00:00+01:00",
        "expires_at": expires_at,
        "source": "homeassistant",
        "screen": {
            "id": "homeassistant-next-bin", "kind": "bin_collection",
            "title": "NEXT COLLECTION", "collection_date": collection_date,
            "duration_seconds": 8, "slide_speed": 20,
            "collections": [{"id": "mixed", "label": "Mixed recycling"}],
        },
    }


class RecyclingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.epoch = timestamp("2026-10-11T10:00:00+01:00")
        self.mqtt = MqttScreenState()
        self.raw = snapshot()
        self.assertTrue(self.mqtt.accept(
            "led/screens/homeassistant-next-bin", self.raw, self.epoch
        ))

    def test_defaults_registry_schema_validation_and_dynamodb_migration(self):
        defaults = default_runtime_config({})
        expected = {
            "enabled": True, "screen_duration_seconds": 20,
            "slide_speed": 15, "schedule_windows": [],
        }
        self.assertEqual(defaults["feeds"]["recycling"], expected)
        schema = schema_metadata()["feeds"]["recycling"]
        self.assertTrue(schema["virtual"])
        self.assertEqual(schema["provider"], "Home Assistant · local MQTT")
        self.assertEqual(set(schema["mutable_fields"]), set(expected))
        self.assertIn("schedule_windows", schema["mutable_fields"])
        old = copy.deepcopy(defaults)
        old["feeds"].pop("recycling")
        self.assertEqual(validate_runtime_config(old)["feeds"]["recycling"], expected)
        updated = validate_runtime_config(defaults)
        self.assertEqual(updated["feeds"]["recycling"], expected)
        self.assertEqual(validate_feed_patch("recycling", expected), expected)

    def test_rejects_invalid_admin_values_and_unknown_fields(self):
        cases = [
            {"enabled": "true"}, {"screen_duration_seconds": 1},
            {"screen_duration_seconds": 301}, {"slide_speed": 0},
            {"slide_speed": 121}, {"slide_speed": True},
            {"days_before_collection": False}, {"poll_seconds": 60},
        ]
        for invalid in cases:
            with self.subTest(invalid=invalid):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_feed_patch("recycling", invalid)

    def test_window_duration_speed_and_source_snapshot_immutability(self):
        effective = self.mqtt.effective_screens(self.epoch, "2026-10-11")
        self.assertEqual(len(effective), 1)
        self.assertEqual(effective[0]["duration_seconds"], 20)
        self.assertEqual(effective[0]["slide_speed"], 15)
        self.assertEqual(self.mqtt.screens(self.epoch)[0], self.raw["screen"])
        self.assertIsNot(effective[0], self.mqtt.screens(self.epoch)[0])
        self.mqtt.configure_recycling({
            "enabled": True,
            "screen_duration_seconds": 40, "slide_speed": 60,
        })
        changed = self.mqtt.effective_screens(self.epoch, "2026-10-07")
        self.assertEqual((changed[0]["duration_seconds"], changed[0]["slide_speed"]), (40, 60))
        self.assertEqual(self.mqtt.screens(self.epoch)[0]["duration_seconds"], 8)
        self.mqtt.configure_recycling({"enabled": False})
        self.assertEqual(self.mqtt.effective_screens(self.epoch, "2026-10-13"), [])
        self.assertEqual(len(self.mqtt.screens(self.epoch)), 1)

    def test_midnight_and_zero_day_window_and_clock_not_synchronized(self):
        self.mqtt.configure_recycling({"schedule_windows": []})
        self.assertEqual(len(self.mqtt.effective_screens(self.epoch, "2026-10-12")), 1)
        self.assertEqual(len(self.mqtt.effective_screens(self.epoch, "2026-10-13")), 1)
        self.assertEqual(len(self.mqtt.effective_screens(self.epoch, "")), 1)
        clock = ClockState()
        clock.sync("2026-10-12T22:59:59Z", 100)
        self.assertEqual(clock.date_text(100), "2026-10-12")
        self.assertEqual(clock.date_text(101), "2026-10-13")
        self.assertEqual(len(self.mqtt.effective_screens(self.epoch, clock.date_text(101))), 1)

    def test_year_rollover_and_bst_gmt_date_arithmetic(self):
        mqtt = MqttScreenState()
        value = snapshot("2027-01-02", "2027-01-03T00:00:00+00:00")
        epoch = timestamp("2026-12-31T10:00:00+00:00")
        self.assertTrue(mqtt.accept("led/screens/homeassistant-next-bin", value, epoch))
        self.assertEqual(len(mqtt.effective_screens(epoch, "2026-12-31")), 1)
        self.assertEqual(len(mqtt.effective_screens(epoch, "2026-12-30")), 1)
        # Calendar-day window must not be implemented as 2*86400 UTC seconds.
        clock = ClockState()
        clock.sync("2026-10-25T00:59:59Z", 100)
        self.assertEqual(clock.date_text(100), "2026-10-25")
        self.assertEqual(clock.date_text(101), "2026-10-25")
        self.assertEqual(len(self.mqtt.effective_screens(self.epoch, "2026-10-13")), 1)

    def test_expiry_clear_and_phase_preservation(self):
        http = [{"id": "http", "kind": "message", "duration_seconds": 40}]
        rotation = ScreenRotation()
        rotation.update_sources(http, self.mqtt.effective_screens(self.epoch, "2026-10-11"), 0)
        rotation.index = 0
        rotation.started_at = -3
        self.mqtt.configure_recycling({"slide_speed": 55})
        rotation.update_sources(http, self.mqtt.effective_screens(self.epoch, "2026-10-11"), 4)
        active, phase = rotation.current(4)
        self.assertEqual((active["id"], phase), ("http", 7))
        self.mqtt.configure_recycling({"enabled": False})
        rotation.update_sources(http, self.mqtt.effective_screens(self.epoch, "2026-10-11"), 5)
        self.assertEqual(rotation.current(5)[0]["id"], "http")
        self.mqtt.configure_recycling({"enabled": True})
        self.assertEqual(self.mqtt.expire(timestamp("2026-10-13T23:00:00+00:00")), ["homeassistant-next-bin"])
        self.assertEqual(self.mqtt.effective_screens(timestamp("2026-10-13T23:00:00+00:00"), "2026-10-13"), [])

    def test_enabled_recycling_health_is_unobservable_not_ok(self):
        class Status:
            def feed_state(self):
                return {}
            def screens_state(self):
                return {}
        config = default_runtime_config({})
        feeds = _status_payload(config, Status())["feeds"]
        self.assertEqual(feeds["recycling"]["health"], "unavailable")
        config["feeds"]["recycling"]["enabled"] = False
        self.assertEqual(_status_payload(config, Status())["feeds"]["recycling"]["health"], "disabled")

    def test_admin_and_simulator_display_distinguish_preview_from_mqtt(self):
        root = Path(__file__).resolve().parents[1]
        admin = (root / "simulator" / "admin.html").read_text()
        simulator = (root / "simulator" / "index.html").read_text()
        self.assertIn("Not available from LED control plane", admin)
        self.assertNotIn("days_before_collection", admin)
        self.assertIn("schedule_windows", admin)
        self.assertIn("recyclingPolicy.screen_duration_seconds", simulator)
        self.assertIn("ignores admin enable and schedule windows", simulator)


if __name__ == "__main__":
    unittest.main()
