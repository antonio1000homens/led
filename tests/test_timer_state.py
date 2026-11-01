import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

FIRMWARE = Path(__file__).resolve().parents[1] / "hardware" / "matrixportal" / "firmware"
sys.path.insert(0, str(FIRMWARE))

from timer_state import (TimerState, caterpillar_position, timer_apples_eaten,
                         timer_apple_center, format_countdown, iso_epoch, validate_snapshot)


class AlexaTimerStateTests(unittest.TestCase):
    def snapshot(self, published, timers):
        return {"schema_version": 1, "event": "upsert", "source": "homeassistant",
                "device": "living-room-alexa", "published_at": published, "timers": timers}

    def test_offset_and_fractional_timestamps_normalize(self):
        self.assertEqual(iso_epoch("2026-10-31T16:00:00+01:00"),
                         iso_epoch("2026-10-31T15:00:00Z"))

    def test_timer_ids_use_circuitpython_compatible_ascii_validation(self):
        class CharacterWithoutIsalnum(str):
            def isalnum(self):
                raise AttributeError("CircuitPython str has no isalnum")

        class TimerIdWithoutIsalnum(str):
            def __iter__(self):
                return (CharacterWithoutIsalnum(character) for character in str(self))

        running = {
            "timer_id": TimerIdWithoutIsalnum("A9._:-z"),
            "state": "running",
            "ends_at": "2026-10-31T15:05:00Z",
        }
        validate_snapshot(self.snapshot("2026-10-31T15:00:01Z", [running]),
                          "living-room-alexa")
        for invalid_id in ("timer/id", "timer café", "timer id"):
            invalid = dict(running, timer_id=invalid_id)
            with self.subTest(timer_id=invalid_id):
                self.assertRaises(
                    ValueError,
                    validate_snapshot,
                    self.snapshot("2026-10-31T15:00:01Z", [invalid]),
                    "living-room-alexa",
                )

    def test_countdown_format_and_finish_position(self):
        self.assertEqual(format_countdown(3599), "59:59")
        self.assertEqual(format_countdown(3600), "1:00:00")
        self.assertEqual(format_countdown(0.1), "00:01")
        self.assertEqual(format_countdown(0), "00:00")
        self.assertEqual(format_countdown(-1), "00:00")
        self.assertEqual(caterpillar_position(164, 0), 12)
        self.assertEqual(caterpillar_position(164, 1), 142)
        self.assertEqual(caterpillar_position(164, 0.5), 77)
        self.assertEqual(caterpillar_position(164, 0.999), 141)
        self.assertEqual(timer_apples_eaten(0), 0)
        self.assertEqual(timer_apples_eaten(0.1), 1)
        self.assertEqual(timer_apples_eaten(0.5), 5)
        self.assertEqual(timer_apples_eaten(0.999999), 9)
        self.assertEqual(timer_apples_eaten(1), 10)
        self.assertEqual(timer_apple_center(164, 9), 142)
        self.assertRaises(ValueError, timer_apple_center, 164, 10)
        self.assertEqual(iso_epoch("2026-10-31T15:00:00.125Z"),
                         iso_epoch("2026-10-31T15:00:00Z"))

    def test_selects_nearest_running_timer_and_tracks_progress(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        accepted, _ = state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "long", "state": "running", "ends_at": "2026-10-31T15:10:00Z", "duration_seconds": 600},
            {"timer_id": "short", "state": "running", "ends_at": "2026-10-31T15:05:00Z", "duration_seconds": 300},
        ]), now)
        self.assertTrue(accepted)
        selected = state.selected(now)
        self.assertEqual(selected["timer_id"], "short")
        self.assertEqual(selected["progress"], 0)
        self.assertEqual(state.selected(now + 150)["progress"], 0.5)
        self.assertIs(state.selected(now + 150), selected)
        self.assertIs(state.selected(now + 150), selected)

    def test_running_caterpillar_holds_last_apple_until_expiry(self):
        state = TimerState()
        start = iso_epoch("2026-10-31T15:00:00Z")
        end = "2026-11-07T15:00:00Z"
        accepted, _ = state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "week", "state": "running", "ends_at": end,
             "duration_seconds": 604800},
        ]), start + 604800 - 0.01)
        self.assertTrue(accepted)
        progress = state.selected(start + 604800 - 0.01)["progress"]
        self.assertLess(progress, 1.0)
        self.assertEqual(timer_apples_eaten(progress), 9)
        self.assertLess(caterpillar_position(164, progress),
                        caterpillar_position(164, 1))
        self.assertEqual(state.selected(start + 604800)["state"], "complete")
        self.assertEqual(timer_apples_eaten(state.selected(start + 604800)["progress"]), 10)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for simulator parity")
    def test_browser_simulator_keeps_last_apple_until_zero(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        functions = html[html.index("function alexaTimerRemaining"):
                         html.index("function drawCalendarDue")]
        harness = functions + """
process.stdout.write(JSON.stringify([
  alexaTimerRemaining(300, 299.9),
  alexaTimerRemaining(300, 300),
  alexaTimerCaterpillarPosition(164, 1, 300),
  alexaTimerCaterpillarPosition(164, 0, 300),
  alexaTimerApplesEaten(1, 300),
  alexaTimerApplesEaten(0, 300),
  alexaTimerAppleCenter(164, 9)
]));
"""
        result = subprocess.run(["node", "-e", harness], check=True,
                                capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), [1, 0, 141, 142, 9, 10, 142])

    def test_paused_timer_uses_fixed_remaining_and_resume_keeps_identity(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        accepted, _ = state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "same", "state": "paused", "remaining_seconds": 60,
             "duration_seconds": 120},
        ]), now)
        self.assertTrue(accepted)
        paused = state.selected(now + 60)
        self.assertEqual(paused["remaining_seconds"], 60)
        self.assertEqual(paused["progress"], 0.5)
        accepted, _ = state.accept(self.snapshot("2026-10-31T15:01:01Z", [
            {"timer_id": "same", "state": "running", "ends_at": "2026-10-31T15:02:01Z",
             "duration_seconds": 120},
        ]), now + 61)
        self.assertTrue(accepted)
        resumed = state.selected(now + 61)
        self.assertEqual(resumed["timer_id"], "same")
        self.assertEqual(resumed["state"], "running")
        self.assertEqual(resumed["remaining_seconds"], 60)
        self.assertEqual(resumed["progress"], 0.5)
        advancing = state.selected(now + 91)
        self.assertEqual(advancing["timer_id"], "same")
        self.assertEqual(advancing["remaining_seconds"], 30)
        self.assertEqual(advancing["progress"], 0.75)

    def test_duration_edit_recalculates_caterpillar_progress_without_changing_identity(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "same", "state": "running", "ends_at": "2026-10-31T15:05:00Z",
             "duration_seconds": 300},
        ]), now)[0])
        self.assertEqual(state.selected(now + 150)["progress"], 0.5)
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:02:31Z", [
            {"timer_id": "same", "state": "running", "ends_at": "2026-10-31T15:07:30Z",
             "duration_seconds": 450},
        ]), now + 150)[0])
        self.assertEqual(state.selected(now + 150)["timer_id"], "same")
        self.assertAlmostEqual(state.selected(now + 150)["progress"], 1 / 3)

    def test_rejects_expired_out_of_order_malformed_and_wrong_device_snapshots(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        expired = self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "old", "state": "running", "ends_at": "2026-10-31T14:59:59Z"},
        ])
        self.assertFalse(state.accept(expired, now)[0])
        current = {"schema_version": 1, "event": "clear", "source": "homeassistant",
                   "device": "living-room-alexa", "published_at": "2026-10-31T15:00:02Z"}
        self.assertTrue(state.accept(current, now)[0])
        self.assertEqual(state.accept(current, now)[1], "out_of_order")
        wrong = dict(current, device="bathroom-alexa", published_at="2026-10-31T15:00:03Z")
        self.assertFalse(state.accept(wrong, now)[0])
        extra = dict(current, token="private")
        self.assertRaises(ValueError, validate_snapshot, extra, "living-room-alexa")
        invalid_version = dict(current, schema_version=True,
                               published_at="2026-10-31T15:00:03Z")
        self.assertRaises(ValueError, validate_snapshot, invalid_version,
                           "living-room-alexa")
        self.assertRaises(ValueError, validate_snapshot,
                          self.snapshot("2026-10-31T15:00:04Z", []),
                          "living-room-alexa")
        too_far = self.snapshot("2026-10-31T15:00:04Z", [
            {"timer_id": "far", "state": "running", "ends_at": "2026-11-09T15:00:00Z"},
        ])
        self.assertEqual(state.accept(too_far, now)[1], "timer_end_outside_bounds")
        self.assertEqual(state.accept(" " * 4097, now)[1], "payload_too_large")
    def test_clear_cancels_completion_hold_immediately(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "done", "state": "running", "ends_at": "2026-10-31T15:00:02Z"},
        ]), now)[0])
        self.assertEqual(state.selected(now + 2)["state"], "complete")
        clear = {"schema_version": 1, "event": "clear", "source": "homeassistant",
                 "device": "living-room-alexa", "published_at": "2026-10-31T15:00:03Z"}
        self.assertTrue(state.accept(clear, now + 2)[0])
        self.assertIsNone(state.selected(now + 2))

    def test_running_timer_continues_on_monotonic_clock_without_epoch(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "offline", "state": "running", "ends_at": "2026-10-31T15:01:00Z",
             "duration_seconds": 60},
        ]), now, 100.0)[0])
        self.assertEqual(state.selected(None, 130.0)["remaining_seconds"], 30.0)
        self.assertEqual(state.selected(None, 160.0)["state"], "complete")
        self.assertEqual(state.selected(None, 162.0)["state"], "complete")
        self.assertIsNone(state.selected(None, 163.0))

    def test_marks_upstream_stale_after_bounded_refresh_window(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "stale", "state": "running", "ends_at": "2026-10-31T16:00:00Z"},
        ]), now, 100.0)[0])
        self.assertFalse(state.selected(now, 699.0)["stale"])
        self.assertTrue(state.selected(now, 700.0)["stale"])

    def test_unsynchronized_clock_accepts_paused_but_not_unanchored_running_timers(self):
        state = TimerState()
        paused = self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "paused", "state": "paused", "remaining_seconds": 45},
        ])
        self.assertTrue(state.accept(paused, None, 1.0)[0])
        self.assertEqual(state.selected(None, 1.0)["remaining_seconds"], 45)
        running_state = TimerState()
        running = self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "running", "state": "running", "ends_at": "2026-10-31T15:01:00Z"},
        ])
        self.assertEqual(running_state.accept(running, None, 1.0)[1], "clock_not_synchronized")

    def test_completes_once_then_selects_next_timer(self):
        state = TimerState()
        now = iso_epoch("2026-10-31T15:00:00Z")
        self.assertTrue(state.accept(self.snapshot("2026-10-31T15:00:01Z", [
            {"timer_id": "first", "state": "running", "ends_at": "2026-10-31T15:00:05Z", "duration_seconds": 5},
            {"timer_id": "next", "state": "running", "ends_at": "2026-10-31T15:00:10Z", "duration_seconds": 10},
        ]), now)[0])
        self.assertEqual(state.selected(now + 5)["state"], "complete")
        self.assertEqual(state.selected(now + 6)["state"], "complete")
        self.assertEqual(state.selected(now + 9)["timer_id"], "next")


if __name__ == "__main__":
    unittest.main()
