"""Exercise firmware sleep/clock functions without importing hardware code.py."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

from flash_events import FlashState, _iso_epoch


class ReminderClockLoopTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.due = _iso_epoch("2026-10-04T12:00:00Z")
        self.flash = FlashState(enabled=True)
        self.flash.accept({
            "id": "sleep-reminder", "type": "reminder", "event": "scheduled",
            "label": "Test", "due_at": "2026-10-04T12:00:00Z",
            "expires_at": "2026-10-04T12:05:00Z",
            "published_at": "2026-10-04T11:59:00Z",
        }, 0, self.due - 1)
        self.pauses = []
        self.polls = []
        self.scope = {
            "time": SimpleNamespace(monotonic=lambda: self.now, sleep=self.sleep),
            "clock": SimpleNamespace(epoch=lambda now: self.due - 1 + now),
            "flash": self.flash, "flash_resume": None, "last_render_key": "old",
            "rotation": SimpleNamespace(pause=self.pause),
            "mqtt": SimpleNamespace(poll=self.polls.append), "buttons": None,
            "_BUTTON_POLL_SECONDS": 0.05, "_MQTT_SLEEP_POLL_SECONDS": 0.25,
        }
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / "code.py").read_text())
        names = {"_sleep_interruptible", "_reminder_epoch", "_flash_started",
                 "_service_reminder_clock"}
        functions = ast.Module(body=[node for node in tree.body
                                    if isinstance(node, ast.FunctionDef)
                                    and node.name in names], type_ignores=[])
        exec(compile(functions, "code.py", "exec"), self.scope)

    def sleep(self, seconds):
        self.now += seconds

    def pause(self, now):
        self.pauses.append(now)
        return ("departures", 2.5)

    def test_static_sleep_wakes_at_local_due_time(self):
        self.scope["_sleep_interruptible"](30, service_mqtt=True)
        self.assertGreaterEqual(self.now, 1)
        self.assertLess(self.now, 1.06)
        self.assertEqual(len(self.pauses), 1)
        self.assertEqual(self.scope["flash_resume"], ("departures", 2.5))
        self.assertTrue(self.flash.active(self.now))
        self.assertIsNone(self.scope["last_render_key"])

    def test_due_checks_during_frames_do_not_poll_or_pause_twice(self):
        self.assertFalse(self.scope["_service_reminder_clock"](0.9))
        self.assertTrue(self.scope["_service_reminder_clock"](1.0))
        self.assertFalse(self.scope["_service_reminder_clock"](1.1))
        self.assertEqual(self.polls, [])
        self.assertEqual(self.pauses, [1.0])


if __name__ == "__main__":
    unittest.main()
