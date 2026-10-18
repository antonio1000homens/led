import unittest
from datetime import datetime

from cron_schedule import schedule_window_active
from runtime_config import RuntimeConfigValidationError, validate_feed_patch


def epoch(value):
    return int(datetime.fromisoformat(value).timestamp())


class ScheduleWindowTests(unittest.TestCase):
    def test_inclusive_start_exclusive_end_and_overnight(self):
        windows = [{"cron": "0 18 * * 3", "duration_minutes": 840}]
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-21T18:00:00+01:00")))
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-22T07:59:00+01:00")))
        self.assertFalse(schedule_window_active(windows, epoch("2026-10-22T08:00:00+01:00")))

    def test_unrestricted_missing_clock_and_multiple_windows(self):
        self.assertTrue(schedule_window_active([], None))
        windows = [{"cron": "0 8 * * 1-5", "duration_minutes": 60},
                   {"cron": "0 20 * * 6,0", "duration_minutes": 120}]
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-19T08:30:00+01:00")))
        self.assertFalse(schedule_window_active(windows, None))
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-24T21:00:00+01:00")))

    def test_spring_gap_skipped_and_both_autumn_occurrences_match(self):
        windows = [{"cron": "30 1 * * *", "duration_minutes": 30}]
        self.assertFalse(schedule_window_active(windows, epoch("2026-03-29T02:00:00+01:00")))
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-25T01:45:00+01:00")))
        self.assertTrue(schedule_window_active(windows, epoch("2026-10-25T01:45:00+00:00")))

    def test_month_and_year_boundary(self):
        windows = [{"cron": "0 23 31 12 *", "duration_minutes": 120}]
        self.assertTrue(schedule_window_active(windows, epoch("2027-01-01T00:59:00+00:00")))
        self.assertFalse(schedule_window_active(windows, epoch("2027-01-01T01:00:00+00:00")))

    def test_validation_and_legacy_migration(self):
        self.assertEqual(validate_feed_patch("today", {"schedule_windows": [
            {"cron": "0 8 * * 1-5", "duration_minutes": 30}
        ]}), {"schedule_windows": [{"cron": "0 8 * * 1-5", "duration_minutes": 30}]})
        for windows in ([{"cron": "bad", "duration_minutes": 10}],
                        [{"cron": "* * * * *", "duration_minutes": 0}],
                        [{"cron": "* * * * *", "duration_minutes": 1}] * 17):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("today", {"schedule_windows": windows})


if __name__ == "__main__":
    unittest.main()
