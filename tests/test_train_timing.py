"""Train-only clock/rotation/deadline integration; not panel acceptance."""

import unittest

from animation_scheduler import next_deadline
from screen_client import ScreenRotation


class TrainTimingTests(unittest.TestCase):
    def test_complete_crossings_keep_one_pixel_steps_at_aged_reload_offsets(self):
        # Include observed hardware uptime and substantially longer uptimes.
        for uptime in (297_805_460, 30 * 86_400_000, 365 * 86_400_000):
            for reload_offset in (0, 1, 31, 156):
                with self.subTest(uptime=uptime, reload_offset=reload_offset):
                    started = uptime + reload_offset
                    rotation = ScreenRotation(ticks_per_second=1000)
                    rotation.update([
                        {"id": "train", "kind": "steam_train_intro",
                         "duration_seconds": 33}
                    ], started)
                    deadline, _, _, _ = next_deadline(
                        None, started, 8, ticks_per_second=1000
                    )
                    # Five complete crossings, including hold/reset boundaries.
                    for tick in range(1, 5 * 264 + 1):
                        now = started + tick * 125
                        self.assertEqual(deadline, now)
                        screen, phase = rotation.current(now)
                        self.assertEqual(screen["id"], "train")
                        self.assertEqual(phase, (tick % 264) / 8)
                        self.assertEqual(
                            max(0, 256 - int(phase * 8)),
                            max(0, 256 - tick % 264),
                        )
                        self.assertIsInstance(rotation.started_at, int)
                        # Variable bounded rendering/bookkeeping must consume
                        # the frame budget rather than accumulate pacing drift.
                        cost_ms = (3, 10, 19)[tick % 3]
                        deadline, remaining, late, rebased = next_deadline(
                            deadline, now + cost_ms, 8, ticks_per_second=1000
                        )
                        self.assertEqual(deadline, now + 125)
                        self.assertEqual(remaining, (125 - cost_ms) / 1000)
                        self.assertFalse(late)
                        self.assertFalse(rebased)

    def test_stall_skips_stale_positions_then_resumes_without_catchup_burst(self):
        started = 30 * 86_400_000 + 31
        rotation = ScreenRotation(ticks_per_second=1000)
        rotation.update([
            {"id": "train", "kind": "steam_train_intro", "duration_seconds": 33}
        ], started)
        deadline, _, _, _ = next_deadline(
            None, started, 8, ticks_per_second=1000
        )
        # A genuine 500 ms interruption must not be hidden by replaying old
        # coordinates. This checks recovery policy, not absence of real stalls.
        now = started + 500
        _, phase = rotation.current(now)
        self.assertEqual(max(0, 256 - int(phase * 8)), 252)
        deadline, remaining, late, rebased = next_deadline(
            deadline, now, 8, ticks_per_second=1000
        )
        self.assertEqual(deadline, now)
        self.assertLessEqual(remaining, 0)
        self.assertTrue(late)
        self.assertTrue(rebased)
        deadline, remaining, late, rebased = next_deadline(
            deadline, now + 10, 8, ticks_per_second=1000
        )
        self.assertEqual(deadline, now + 125)
        self.assertEqual(remaining, 0.115)
        self.assertFalse(late)
        self.assertFalse(rebased)
        _, phase = rotation.current(deadline)
        self.assertEqual(max(0, 256 - int(phase * 8)), 251)


if __name__ == "__main__":
    unittest.main()
