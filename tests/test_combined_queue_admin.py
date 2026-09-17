from pathlib import Path
import copy
import unittest

from runtime_config import (
    FEED_REGISTRY,
    default_runtime_config,
    schema_metadata,
    validate_runtime_config,
)


ROOT = Path(__file__).resolve().parents[1]


class CombinedQueueRuntimeTests(unittest.TestCase):
    def test_shared_queue_settings_are_exposed_in_schema(self):
        config = default_runtime_config({})
        queue = config["feeds"]["queue_times"]
        schema = schema_metadata()["feeds"]["queue_times"]
        self.assertEqual(queue["screen_duration_seconds"], 16)
        self.assertEqual(queue["queue_scroll_speed"], 27)
        self.assertEqual(queue["queue_scroll_pause_seconds"], 1)
        self.assertFalse(queue["splash_enabled"])
        self.assertTrue(schema["virtual"])
        self.assertEqual(
            schema["advanced_fields"],
            ["queue_scroll_speed", "queue_scroll_pause_seconds", "splash_enabled"],
        )

    def test_legacy_persisted_config_is_upgraded_with_queue_times_defaults(self):
        legacy = default_runtime_config({})
        del legacy["feeds"]["queue_times"]
        validated = validate_runtime_config(copy.deepcopy(legacy))
        self.assertIn("queue_times", validated["feeds"])
        self.assertEqual(validated["feeds"]["queue_times"]["screen_duration_seconds"], 16)

    def test_queue_members_are_discoverable_by_provider_not_hard_coded_list(self):
        members = [
            feed_id for feed_id, definition in FEED_REGISTRY.items()
            if definition.get("provider") == "queue_times"
        ]
        self.assertEqual(members, ["thorpe_park", "chessington"])


class CombinedQueueAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")

    def test_admin_renders_single_dynamic_queue_times_group(self):
        self.assertIn('data-queue-group="true"', self.source)
        self.assertIn("schema.provider==='queue_times'", self.source)
        self.assertIn("queueMemberIds().map(queueParkHtml)", self.source)
        self.assertIn("future Queue-Times parks automatically join this section", self.source)

    def test_queue_advanced_block_is_collapsed_and_contains_shared_controls(self):
        self.assertIn('<details class="feed-advanced"><summary>Advanced</summary>', self.source)
        self.assertIn("queue_scroll_speed", self.source)
        self.assertIn("queue_scroll_pause_seconds", self.source)
        self.assertIn("splash_enabled", self.source)
        self.assertIn("Screen duration", self.source)

    def test_individual_park_screen_duration_is_not_rendered_in_queue_subsections(self):
        self.assertIn("const fields=['enabled','poll_seconds']", self.source)
        self.assertNotIn("const fields=['enabled','poll_seconds','screen_duration_seconds']", self.source)


if __name__ == "__main__":
    unittest.main()
