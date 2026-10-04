import sys
import types
import unittest


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display


class FakePixels:
    def __init__(self):
        self.shown = 0

    def fill(self, color):
        del color

    def show(self):
        self.shown += 1

    def __setitem__(self, key, value):
        del key, value


class CapturingFixture(led_display.FixtureDisplay):
    def __init__(self):
        self.pixels = None
        self.drawn = []

    def _text(self, value, x, y, color):
        self.drawn.append((str(value), int(x), int(y), color))


def weekly_days():
    icons = ("clear_day", "partly_cloudy_day", "cloudy", "rain", "fog", "snow", "storm")
    weekdays = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")
    return [
        {
            "date": "2026-10-{:02d}".format(4 + index),
            "weekday": weekdays[index],
            "temperature_max_c": 16 - index,
            "temperature_min_c": 9 - index,
            "weather_code": index,
            "icon": icons[index],
            "sunrise_time": "07:{:02d}".format(8 + index * 2),
            "sunset_time": "18:{:02d}".format(29 - index * 2),
        }
        for index in range(7)
    ]


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

        due_rows = [item for item in display.drawn if item[0] in ("TODAY", "DUE 1 DAY", "DUE 2 DAYS")]
        self.assertEqual([item[0] for item in due_rows], ["TODAY", "DUE 1 DAY", "DUE 2 DAYS"])
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

    def test_overdue_todoist_label_is_red_and_right_aligned(self):
        display = CapturingFixture()
        screen = {
            "kind": "calendar_agenda",
            "source": "todoist",
            "events": [{"start": "2026-09-12", "date_text": "12/09", "all_day": True, "title": "Late task"}],
        }
        display._draw_screen(screen, phase=10, clock_date="2026-09-13")
        overdue = [item for item in display.drawn if item[0] == "OVERDUE"]
        self.assertEqual(len(overdue), 1)
        _text, x, _y, color = overdue[0]
        self.assertEqual(x + len("OVERDUE") * led_display.WEATHER_FONT_WIDTH, led_display.DISPLAY_WIDTH)
        self.assertEqual(color, (255, 51, 0))

    def test_weekly_weather_columns_use_full_width_and_keep_content_inside_each_column(self):
        layout = led_display._weekly_weather_layout(weekly_days())
        self.assertEqual(len(layout), 7)
        self.assertEqual(layout[0]["left"], 0)
        self.assertEqual(layout[-1]["right"], led_display.DISPLAY_WIDTH)
        self.assertEqual([item["icon_name"] for item in layout], [day["icon"] for day in weekly_days()])

        previous_right = 0
        for item in layout:
            self.assertEqual(item["left"], previous_right)
            self.assertLess(item["left"], item["right"])
            for text_key, x_key in (("weekday", "weekday_x"), ("max_text", "max_x"), ("min_text", "min_x")):
                text = item[text_key]
                x = item[x_key]
                self.assertGreaterEqual(x, item["left"])
                self.assertLessEqual(x + len(text) * led_display.WEATHER_FONT_WIDTH, item["right"])
            self.assertGreaterEqual(item["icon_x"], item["left"])
            self.assertLessEqual(item["icon_x"] + led_display.WEATHER_ICON_WIDTH, item["right"])
            previous_right = item["right"]

    def test_weekly_weather_fixture_draws_all_rows_and_empty_fallback(self):
        display = CapturingFixture()
        display._draw_screen({"kind": "weather_weekly", "days": weekly_days()}, phase=0)

        text = [item[0] for item in display.drawn]
        self.assertEqual([value for value in text if value in ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")],
                         ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"])
        self.assertEqual(len([value for value in text if value.startswith("MAX")]), 7)
        self.assertEqual(len([value for value in text if value.startswith("MIN")]), 7)

        empty = CapturingFixture()
        empty._draw_screen({"kind": "weather_weekly", "days": []}, phase=0)
        self.assertIn("Weather unavailable", [item[0] for item in empty.drawn])

    def test_weekly_weather_show_suppresses_clock_current_weather_and_stale_header(self):
        display = CapturingFixture()
        display.pixels = FakePixels()
        display.show(
            {
                "kind": "weather_weekly",
                "title": "7 DAY WEATHER",
                "stale": True,
                "days": weekly_days(),
                "weather": {"temperature_c": 17, "icon": "clear_day", "stale": True},
            },
            clock_time="12:34",
            phase=2,
        )

        text = [item[0] for item in display.drawn]
        self.assertNotIn("12:34", text)
        self.assertNotIn("17C", text)
        self.assertNotIn("STALE", text)
        self.assertEqual(display.pixels.shown, 1)

    def test_weather_day_layout_uses_full_height_regions_and_all_metrics(self):
        day = weekly_days()[0]
        layout = led_display._weather_day_layout(day)

        self.assertEqual(layout["weekday"], "SUN")
        self.assertEqual(layout["weekday_rows"], (0, 10, 20))
        self.assertEqual(layout["icon_scale"], 4)
        self.assertEqual(layout["icon_y"], 2)
        self.assertLessEqual(
            layout["icon_y"] + led_display.WEATHER_ICON_WIDTH * layout["icon_scale"],
            32,
        )
        self.assertEqual(layout["rise_text"], "RISE 07:08")
        self.assertEqual(layout["set_text"], "SET 18:29")
        self.assertEqual(layout["max_text"], "MAX 16C")
        self.assertEqual(layout["min_text"], "MIN 9C")
        self.assertGreater(layout["metrics_x"], layout["icon_x"])

    def test_weather_day_fixture_draws_weekday_and_four_metric_rows(self):
        display = CapturingFixture()
        display._draw_screen(
            {"kind": "weather_day", "day": weekly_days()[0], "stale": False},
            phase=0,
        )

        drawn = [item[0] for item in display.drawn]
        self.assertEqual([value for value in drawn if value in ("S", "U", "N")], ["S", "U", "N"])
        self.assertIn("RISE 07:08", drawn)
        self.assertIn("SET 18:29", drawn)
        self.assertIn("MAX 16C", drawn)
        self.assertIn("MIN 9C", drawn)

    def test_weather_day_show_suppresses_shared_header_and_stale_label(self):
        display = CapturingFixture()
        display.pixels = FakePixels()
        display.show(
            {
                "kind": "weather_day",
                "title": "SUN",
                "stale": True,
                "day": weekly_days()[0],
                "weather": {"temperature_c": 17, "icon": "clear_day", "stale": True},
            },
            clock_time="12:34",
            phase=2,
        )

        drawn = [item[0] for item in display.drawn]
        self.assertNotIn("12:34", drawn)
        self.assertNotIn("17C", drawn)
        self.assertNotIn("STALE", drawn)
        self.assertIn("RISE 07:08", drawn)
        self.assertEqual(display.pixels.shown, 1)

    def test_departure_statuses_share_one_vertical_column(self):
        display = CapturingFixture()
        screen = {
            "kind": "rail_combined",
            "services": [
                {"time": "12:00", "destination": "Waterloo", "platform": "1", "status": "On time"},
                {"time": "12:10", "destination": "Waterloo", "platform": "2", "status": "On time"},
                {"time": "12:20", "destination": "Waterloo", "platform": "3", "status": "On time"},
                {"time": "12:30", "destination": "Waterloo", "platform": "4", "status": "On time"},
            ],
        }

        display._draw_screen(screen, phase=0, clock_date="2026-09-15")

        status_x = [x for text, x, _y, _color in display.drawn if text == "On time"]
        self.assertEqual(len(status_x), 4)
        self.assertEqual(len(set(status_x)), 1)
        ordinals = [text for text, _x, _y, _color in display.drawn if text in ("1st", "2nd", "3rd", "4th")]
        self.assertEqual(ordinals[:4], ["1st", "2nd", "3rd", "4th"])


if __name__ == "__main__":
    unittest.main()
