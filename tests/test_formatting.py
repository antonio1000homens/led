import unittest

from formatting import calling_text, format_row, header, row_slide_phase


class FormattingTests(unittest.TestCase):
    def test_row_is_fixed_width(self):
        self.assertEqual(len(format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "status": "On time"})), 32)

    def test_long_destination_uses_available_row_space(self):
        row = format_row({"time": "12:04", "destination": "London Waterloo", "platform": "1", "status": "On time"})
        self.assertIn("London Waterloo", row)
        self.assertIn("P1", row)

    def test_cancelled_status_is_visible(self):
        self.assertIn("CANCELLED", format_row({"time": "12:04", "destination": "Waterloo", "platform": "1", "cancelled": True}))

    def test_stale_header(self):
        self.assertIn("STALE", header("NEM", stale=True))

    def test_header_is_new_departures(self):
        self.assertEqual(header("NEM"), "NEW DEPARTURES")

    def test_rows_slide_in_one_at_a_time(self):
        self.assertEqual(row_slide_phase(0, 0), 0)
        self.assertEqual(row_slide_phase(0, 1), 0)
        self.assertGreater(row_slide_phase(1.1, 0), row_slide_phase(1.1, 1))
        self.assertEqual(row_slide_phase(4, 2), 1)

    def test_calling_text_includes_station_times(self):
        text = calling_text({"destination": "Waterloo", "stops": [{"station": "Wimbledon", "time": "12:19", "status": "On time"}]})
        self.assertEqual(text, "CALLING AT: Wimbledon 12:19")
