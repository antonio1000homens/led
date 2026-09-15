import sys
import types
import unittest


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display


class CapturingFixture(led_display.FixtureDisplay):
    def __init__(self):
        self.pixels = None
        self.drawn = []

    def _text(self, value, x, y, color):
        self.drawn.append((str(value), int(x), int(y), color))


class DisplayLayoutTests(unittest.TestCase):
    def test_todoist_due_labels_are_right_aligned_for_every_row(self):
        display = CapturingFixture()
        screen = {
            "kind": "calendar_agenda",
            "source": "todoist",
            "title": "TODOIST",
            "events": [
                {"start": "2026-09-15T23:59:00+01:00", "date_text": "15/09", "time_text": "23:59", "title": "Today task"},
                {"start": "2026-09-16T00:01:00+01:00", "date_text": "16/09", "time_text": "00:01", "title": "Tomorrow task"},
                {"start": "2026-09-17", "date_text": "17/09", "all_day": True, "title": "Later task"},
            ],
        }

        display._draw_screen(screen, phase=10, clock_date="2026-09-15")

        due_rows = [item for item in display.drawn if item[0] in ("TODAY", "DUE IN 1 DAY", "DUE IN 2 DAYS")]
        self.assertEqual([item[0] for item in due_rows], ["TODAY", "DUE IN 1 DAY", "DUE IN 2 DAYS"])
        for text, x, _y, _color in due_rows:
            self.assertEqual(x + len(text) * led_display.WEATHER_FONT_WIDTH, led_display.DISPLAY_WIDTH)

    def test_todoist_due_labels_ignore_hours(self):
        display = CapturingFixture()
        screen = {
            "kind": "calendar_agenda",
            "source": "todoist",
            "events": [
                {"start": "2026-09-15T00:01:00+01:00", "date_text": "15/09", "time_text": "00:01", "title": "Early"},
                {"start": "2026-09-15T23:59:00+01:00", "date_text": "15/09", "time_text": "23:59", "title": "Late"},
            ],
        }

        display._draw_screen(screen, phase=10, clock_date="2026-09-15")

        self.assertEqual([item[0] for item in display.drawn].count("TODAY"), 2)

    def test_departure_statuses_share_one_vertical_column(self):
        display = CapturingFixture()
        screen = {
            "kind": "rail_combined",
            "services": [
                {"time": "12:00", "destination": "Waterloo", "platform": "1", "status": "On time"},
                {"time": "12:10", "destination": "Waterloo", "platform": "2", "status": "On time"},
                {"time": "12:20", "destination": "Waterloo", "platform": "3", "status": "On time"},
            ],
        }

        display._draw_screen(screen, phase=10, clock_date="2026-09-15")

        status_x = [x for text, x, _y, _color in display.drawn if text == "On time"]
        self.assertEqual(len(status_x), 3)
        self.assertEqual(len(set(status_x)), 1)


if __name__ == "__main__":
    unittest.main()
