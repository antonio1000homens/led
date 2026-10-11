import unittest
from unittest.mock import patch

from monotonic_clock import elapsed_seconds, ticks_ms


class MonotonicClockTests(unittest.TestCase):
    def test_integer_uptime_is_subtracted_before_float_conversion(self):
        # More than a week uptime; absolute floating seconds cannot represent
        # millisecond increments on CircuitPython's small floats.
        uptime_ns = 700_000_000_000_000
        with patch("monotonic_clock.time.monotonic_ns", return_value=uptime_ns):
            started = ticks_ms()
        with patch("monotonic_clock.time.monotonic_ns", return_value=uptime_ns + 3_000_000):
            self.assertIsInstance(ticks_ms(), int)
            self.assertEqual(elapsed_seconds(started), 0.003)


if __name__ == "__main__":
    unittest.main()
