import unittest

from formatting import format_row, header


class FormattingTests(unittest.TestCase):
    def test_row_is_fixed_width(self):
        self.assertEqual(len(format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time"})), 32)

    def test_cancelled_status_is_visible(self):
        self.assertIn("CANCELLED", format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "cancelled": True}))

    def test_stale_header(self):
        self.assertIn("STALE", header("NEM", stale=True))
