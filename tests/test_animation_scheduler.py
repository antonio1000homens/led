import unittest

from animation_scheduler import next_deadline


class AnimationSchedulerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
