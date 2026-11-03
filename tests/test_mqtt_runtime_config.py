"""Runtime display controls for MatrixPortal MQTT polling."""

import copy
import unittest

from runtime_config import (
    RuntimeConfigValidationError, default_runtime_config,
    schema_metadata, validate_display_patch, validate_runtime_config,
    _dynamodb_compatible,
)
from decimal import Decimal


class MqttConfigTests(unittest.TestCase):
    def test_defaults_legacy_backfill_and_no_brightness_regression(self):
        original = default_runtime_config({})
        self.assertEqual(original["display"]["mqtt_idle_poll_seconds"], 5)
        self.assertEqual(original["display"]["mqtt_live_poll_seconds"], 1.5)
        self.assertTrue(original["display"]["mqtt_adaptive_enabled"])
        legacy = copy.deepcopy(original)
        legacy["display"] = {"brightness_percent": 75}
        migrated = validate_runtime_config(legacy)
        self.assertEqual(migrated["display"]["brightness_percent"], 75)
        self.assertEqual(migrated["display"]["mqtt_idle_poll_seconds"], 5)
        self.assertEqual(migrated["display"]["mqtt_live_poll_seconds"], 1.5)

    def test_partial_patch_and_validation(self):
        self.assertEqual(validate_display_patch({"mqtt_idle_poll_seconds": 10}),
                         {"mqtt_idle_poll_seconds": 10})
        self.assertIn("mqtt_live_poll_seconds", schema_metadata()["display"]["mutable_fields"])
        for field, value in (
            ("mqtt_adaptive_enabled", 1),
            ("mqtt_live_poll_seconds", 0),
            ("mqtt_idle_poll_seconds", 31),
            ("mqtt_idle_poll_seconds", True),
            ("mqtt_live_poll_seconds", "1.5"),
        ):
            with self.subTest(field=field, value=value):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_display_patch({field: value})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_display_patch({"broker_password": "do-not-persist"})

    def test_dynamodb_encodes_fractional_seconds_as_decimal(self):
        payload = _dynamodb_compatible(default_runtime_config({}))
        self.assertEqual(payload["display"]["mqtt_live_poll_seconds"], Decimal("1.5"))
        self.assertNotIsInstance(payload["display"]["mqtt_live_poll_seconds"], float)


if __name__ == "__main__":
    unittest.main()
