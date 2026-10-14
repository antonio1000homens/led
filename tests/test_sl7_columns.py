"""Regression coverage for the time-first SL7 two-column timetable."""

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
import display as led_display


def combined_screen():
    return {
        "kind": "bus_departures_combined",
        "directions": {
            "new-malden": {
                "status": "ok", "stale": False, "enabled": True,
                "departures": [
                    {"local_time": "21:05", "due_text": "15m"},
                    {"local_time": "21:35", "due_text": "Due"},
                    {"local_time": "21:40", "due_text": "50m", "cancelled": True},
                ],
            },
            "heathrow": {
                "status": "ok", "stale": False, "enabled": True,
                "departures": [{"local_time": "20:54", "due_text": "4m"}],
            },
        },
    }


class Sl7ColumnTests(unittest.TestCase):
    def test_countdown_is_labelled_without_losing_due_or_cancellation(self):
        self.assertEqual(led_display.split_sl7_due_text("15m"), "Due in 15m")
        self.assertEqual(led_display.split_sl7_due_text("Due"), "Due in 0m")
        self.assertEqual(led_display.split_sl7_due_text("CXL"), "CXL")
        self.assertLessEqual(
            led_display.SL7_DUE_COLUMN_X + len("Due in 999m") * (
                led_display.WEATHER_FONT_WIDTH + led_display.WEATHER_GAP
            ), 128,
        )

    def test_matrix_first_column_is_time_second_is_due_in(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display._label = mock.Mock()
        group = []
        display._bus_departures_split(group, combined_screen())
        calls = display._label.call_args_list
        self.assertIn(mock.call(group, "21:05", 0xFFFFFF, 2, 11), calls)
        self.assertIn(mock.call(group, "Due in 15m", 0xFFFFFF, 42, 11), calls)
        self.assertIn(mock.call(group, "21:35", 0xFFFFFF, 2, 19), calls)
        self.assertIn(mock.call(group, "Due in 0m", 0xFFFFFF, 42, 19), calls)
        self.assertIn(mock.call(group, "21:40", 0xFF3300, 2, 27), calls)
        self.assertIn(mock.call(group, "CXL", 0xFF3300, 42, 27), calls)
        self.assertIn(mock.call(group, "20:54", 0xFFFFFF, 130, 11), calls)
        self.assertIn(mock.call(group, "Due in 4m", 0xFFFFFF, 170, 11), calls)

    def test_fixture_matches_time_first_and_countdown_order(self):
        display = led_display.FixtureDisplay.__new__(led_display.FixtureDisplay)
        display._text = mock.Mock()
        display._draw_screen(combined_screen(), 0)
        calls = display._text.call_args_list
        self.assertIn(mock.call("21:05", 2, 8, (255, 255, 255)), calls)
        self.assertIn(mock.call("Due in 15m", 42, 8, (255, 255, 255)), calls)
        self.assertIn(mock.call("Due in 0m", 42, 16, (255, 255, 255)), calls)
        self.assertIn(mock.call("CXL", 42, 24, (255, 51, 0)), calls)
        self.assertIn(mock.call("20:54", 130, 8, (255, 255, 255)), calls)
        self.assertIn(mock.call("Due in 4m", 170, 8, (255, 255, 255)), calls)

    def test_browser_simulator_has_matching_time_first_columns(self):
        simulator = (Path(__file__).parents[1] / "simulator/index.html").read_text()
        split = simulator.split("function drawSplitSl7(screen)", 1)[1].split(
            "function drawBusDepartures", 1
        )[0]
        self.assertIn("drawLedText(String(item.local_time || '--:--').slice(0,5), x + 2 * FONT_PIXEL_SCALE, y)", split)
        self.assertIn("drawLedText(countdown, x + 42 * FONT_PIXEL_SCALE, y)", split)
        self.assertIn("'Due in '", split)
        self.assertIn("due === 'Due' ? '0m'", split)


if __name__ == "__main__":
    unittest.main()
