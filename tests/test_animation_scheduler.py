import unittest

from animation_scheduler import (
    earliest_wake_seconds,
    frame_gap_exceeded,
    frame_sleep_remaining,
    next_deadline,
    screen_fetch_decision,
    train_gc_collection_due,
)


class AnimationSchedulerTests(unittest.TestCase):
    def test_frame_gap_diagnostic_ignores_normal_and_threshold_intervals(self):
        self.assertFalse(frame_gap_exceeded(None, 125))
        self.assertFalse(frame_gap_exceeded(1000, 1125))
        self.assertFalse(frame_gap_exceeded(1000, 1200))
        self.assertTrue(frame_gap_exceeded(1000, 1201))

    def test_train_gc_waits_until_due_and_for_a_long_static_window(self):
        self.assertFalse(train_gc_collection_due(59, 60, "rail_combined", False, 2))
        self.assertFalse(train_gc_collection_due(60, 60, "rail_combined", False, 1.49))
        self.assertTrue(train_gc_collection_due(60, 60, "rail_combined", False, 1.5))

    def test_train_gc_accepts_a_window_longer_than_the_collection_budget(self):
        self.assertFalse(
            train_gc_collection_due(
                8, 8, "rail_combined", False, 0.59, minimum_idle_seconds=0.6
            )
        )
        self.assertTrue(
            train_gc_collection_due(
                8, 8, "rail_combined", False, 0.6, minimum_idle_seconds=0.6
            )
        )

    def test_train_gc_never_runs_during_motion_or_on_other_screens(self):
        self.assertFalse(train_gc_collection_due(60, 60, "rail_combined", True, 3))
        self.assertFalse(train_gc_collection_due(60, 60, "calendar_agenda", False, 3))
        self.assertFalse(train_gc_collection_due(60, 60, "rail_combined", False, None))

    def test_due_fetch_waits_while_animation_is_active(self):
        should_fetch, retry_at = screen_fetch_decision(10.0, 9.0, True, 4.0)
        self.assertFalse(should_fetch)
        self.assertEqual(retry_at, 10.5)

    def test_due_fetch_waits_for_a_long_enough_static_window(self):
        should_fetch, retry_at = screen_fetch_decision(10.0, 9.0, False, 2.9)
        self.assertFalse(should_fetch)
        self.assertEqual(retry_at, 10.5)

    def test_due_fetch_runs_when_static_window_is_safe(self):
        should_fetch, next_fetch = screen_fetch_decision(10.0, 9.0, False, 3.0)
        self.assertTrue(should_fetch)
        self.assertEqual(next_fetch, 9.0)

    def test_not_due_fetch_keeps_its_scheduled_time(self):
        should_fetch, next_fetch = screen_fetch_decision(8.0, 9.0, True, 0.0)
        self.assertFalse(should_fetch)
        self.assertEqual(next_fetch, 9.0)

    def test_wake_arbitration_uses_earliest_boundary(self):
        self.assertEqual(earliest_wake_seconds(7.5, 20, 3.5), 3.5)
        self.assertEqual(earliest_wake_seconds(7.5, 20, None), 7.5)

    def test_frame_sleep_remaining_prevents_catchup_after_a_late_frame(self):
        self.assertAlmostEqual(frame_sleep_remaining(5.0, 5.005, 12), 1 / 12 - 0.005)
        self.assertLess(frame_sleep_remaining(5.0, 5.1, 12), 0)

    def test_integer_frame_timing_retains_milliseconds_after_days_of_uptime(self):
        started = 297_805_460
        self.assertAlmostEqual(
            frame_sleep_remaining(started, started + 3, 8, 1000), 0.122
        )
        self.assertLess(frame_sleep_remaining(started, started + 130, 8, 1000), 0)

    def test_integer_deadlines_include_bookkeeping_without_cumulative_drift(self):
        started = 297_805_460
        deadline, _, _, _ = next_deadline(None, started, 8, ticks_per_second=1000)
        for frame in range(1, 200):
            # Render and bookkeeping take 10 ms after the planned frame start.
            deadline, remaining, late, rebased = next_deadline(
                deadline, started + frame * 125 + 10, 8, ticks_per_second=1000
            )
            self.assertEqual(deadline, started + (frame + 1) * 125)
            self.assertEqual(remaining, 0.115)
            self.assertFalse(late)
            self.assertFalse(rebased)

    def test_slightly_late_integer_deadline_rebases_without_catchup(self):
        now = 297_805_460
        deadline, remaining, late, rebased = next_deadline(
            now - 130, now, 8, ticks_per_second=1000
        )
        self.assertEqual(deadline, now)
        self.assertLessEqual(remaining, 0)
        self.assertTrue(late)
        self.assertTrue(rebased)

    def test_cadence_switch_rebases_before_scheduling_new_frame(self):
        deadline, remaining, late, rebased = next_deadline(
            previous_deadline=100.0,
            now=101.0,
            cadence=12,
            cadence_changed=True,
        )

        self.assertAlmostEqual(deadline, 101.0 + 1.0 / 12.0)
        self.assertGreater(remaining, 0)
        self.assertFalse(late)
        self.assertTrue(rebased)

    def test_long_blocking_fetch_rebases_instead_of_catching_up(self):
        deadline, remaining, late, rebased = next_deadline(
            previous_deadline=10.0,
            now=11.0,
            cadence=8,
        )

        self.assertEqual(deadline, 11.0)
        self.assertLessEqual(remaining, 0)
        self.assertTrue(late)
        self.assertTrue(rebased)

        next_frame, next_remaining, next_late, next_rebased = next_deadline(
            previous_deadline=deadline,
            now=11.01,
            cadence=8,
        )
        self.assertAlmostEqual(next_frame, 11.0 + 1.0 / 8.0)
        self.assertGreater(next_remaining, 0)
        self.assertFalse(next_late)
        self.assertFalse(next_rebased)

if __name__ == "__main__":
    unittest.main()
