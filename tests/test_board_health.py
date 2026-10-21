import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hardware/matrixportal/firmware"))
from board_health import BoardHealth, HEARTBEAT_SECONDS


class BoardHealthTests(unittest.TestCase):
    def test_heartbeat_is_due_by_progress_time_and_payload_is_compact(self):
        health = BoardHealth("matrixportal-s3-abc1", "rev_42")
        self.assertTrue(health.due(0))
        health.checkpoint("render", {"id": "departures", "kind": "rail_combined", "source": "api"})
        health.completed_render(
            {"id": "departures", "kind": "rail_combined", "source": "api", "duration_seconds": 90},
            1, 1790000000, 1200000,
        )
        payload = health.payload(1, 1790000000, 1190000)
        parsed = json.loads(payload)
        self.assertLess(len(payload), 2048)
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(parsed["last_screen_id"], "departures")
        self.assertEqual(parsed["expected_duration_seconds"], 90)
        self.assertEqual(parsed["heap_low_water_bytes"], 1190000)
        self.assertEqual(parsed["sequence"], 1)
        self.assertFalse(health.due(1 + HEARTBEAT_SECONDS - 0.01))
        self.assertTrue(health.due(1 + HEARTBEAT_SECONDS))

    def test_unsynchronized_clock_stays_null_and_attempt_is_separate(self):
        health = BoardHealth("boot-a", "unknown")
        health.completed_render({"id": "intro", "kind": "message"}, 3, None, None)
        health.checkpoint("render", {"id": "next", "kind": "christmas_tracker", "source": "api"})
        payload = json.loads(health.payload(4, None, None))
        self.assertIsNone(payload["reported_at_epoch"])
        self.assertFalse(payload["clock_synchronized"])
        self.assertEqual(payload["last_screen_id"], "intro")
        self.assertEqual(payload["attempted_screen_id"], "next")
        self.assertEqual(payload["stage"], "render")

    def test_fetch_results_keep_bounded_provider_state_and_only_error_class(self):
        health = BoardHealth("boot-a")
        health.fetch_result(12.5, 0.25, [
            {"source": "open_meteo", "stale": True},
            {"source": "open_meteo", "stale": False},
            {"source": "national_rail", "stale": False},
        ])
        self.assertTrue(health.state["last_fetch_successful"])
        health.checkpoint("fetch", {"id": "calendar", "kind": "calendar_agenda", "source": "todoist"})
        health.fetch_result(20, 2.1, error="Token leaked in URL")
        payload = json.loads(health.payload(20, None, None))
        self.assertEqual(payload["fetch_failures"], 1)
        self.assertFalse(payload["last_fetch_successful"])
        self.assertEqual(payload["last_fetch_error_class"], "other")
        self.assertEqual(payload["attempted_screen_id"], "calendar")
        self.assertEqual(len(payload["feed_health"]), 2)
        self.assertLess(len(json.dumps(payload)), 2048)

    def test_identifiers_are_bounded_and_strip_personal_content(self):
        health = BoardHealth("boot-a", "rev")
        health.checkpoint("render", {"id": "meeting secret text !", "kind": "private", "source": "api"})
        payload = json.loads(health.payload(1, None, None))
        self.assertEqual(payload["attempted_screen_id"], "meetingsecrettext")
        self.assertEqual(len(payload["attempted_screen_id"]), 17)
        self.assertNotIn("!", payload["attempted_screen_id"])


if __name__ == "__main__":
    unittest.main()
