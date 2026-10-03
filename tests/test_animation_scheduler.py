import unittest

from animation_scheduler import earliest_wake_seconds, next_deadline, screen_fetch_decision


class AnimationSchedulerTests(unittest.TestCase):
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
