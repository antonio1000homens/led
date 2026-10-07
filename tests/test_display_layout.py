import sys
import types
import unittest
from unittest import mock


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

    def _text_scaled(self, value, x, y, color, scale=1):
        self._text(value, x, y, color)


class CapturingGroup(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.x = 0
        self.y = 0
        self.hidden = False


class CapturingBitmap:
    def __init__(self, width, height, colors):
        self.width, self.height, self.colors = width, height, colors

    def __setitem__(self, key, value):
        del key, value


class CapturingPalette:
    def __init__(self, count):
        self.values = [None] * count

    def __setitem__(self, key, value):
        self.values[key] = value

    def make_transparent(self, index):
        del index


class CapturingTileGrid:
    def __init__(self, bitmap, pixel_shader, x=0, y=0):
        del bitmap, pixel_shader
        self.x, self.y = x, y


class CapturingLabel:
    def __init__(self, font, **kwargs):
        del font
        self.__dict__.update(kwargs)


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
        }
        for index in range(7)
    ]



def today_blocks():
    icons = ("clear_day", "cloudy", "partly_cloudy_day", "clear_night", "rain", "cloudy")
    return [
        {
            "label": label,
            "temperature_c": 10 + index,
            "weather_code": index,
            "icon": icons[index],
        }
        for index, label in enumerate(("Now", "2pm", "6pm", "10pm", "2am", "6am"))
    ]


class DisplayLayoutTests(unittest.TestCase):
    def test_bin_collection_one_and_two_collection_layout(self):
        display = CapturingFixture()
        display._draw_screen({
            "kind": "bin_collection", "title": "NEXT COLLECTION",
            "collection_date": "2026-10-13",
            "collections": [{"id": "mixed", "label": "Mixed recycling"}],
            "slide_speed": 20,
        }, 4)
        self.assertIn(("NEXT COLLECTION", 0, 3, (255, 170, 0)), display.drawn)
        self.assertIn(("Mixed recycling", 85, 14, (255, 255, 255)), display.drawn)
        self.assertIn(("2026-10-13", 0, 25, (170, 170, 170)), display.drawn)

        display.drawn = []
        display._draw_screen({
            "kind": "bin_collection", "title": "NEXT COLLECTION",
            "collection_date": "2026-10-13",
            "collections": [{"id": "mixed", "label": "Mixed recycling"},
                            {"id": "paper", "label": "Paper"}],
            "slide_speed": 20,
        }, 4)
        self.assertIn(("Mixed recycling / Paper", 61, 14, (255, 255, 255)), display.drawn)

    def test_bin_collection_long_label_moves_at_supplied_speed(self):
        display = CapturingFixture()
        screen = {"kind": "bin_collection", "title": "NEXT COLLECTION",
                  "collection_date": "2026-10-13", "slide_speed": 20,
                  "collections": [{"id": "x", "label": "A very long collection label for the MatrixPortal"}]}
        display._draw_screen(screen, 4)
        first = next(item for item in display.drawn if item[0].startswith("A very long"))
        display.drawn = []
        display._draw_screen(screen, 5)
        second = next(item for item in display.drawn if item[0].startswith("A very long"))
        self.assertEqual(first[1] - second[1], 20)

    def test_bin_collection_blank_scroll_gap_allows_transport_reconnect(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        screen = {"kind": "bin_collection", "slide_speed": 20,
                  "collections": [{"id": "x", "label": "X" * 50}]}
        with mock.patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "baseline"):
            self.assertTrue(display.animation_active(screen, 0))
            self.assertFalse(display.animation_active(screen, 20))
            self.assertEqual(display.animation_cadence(screen, 20), 0)
            self.assertAlmostEqual(display.animation_sleep_seconds(screen, 20), 0.2)

    def test_bin_collection_hardware_layout_keeps_normal_clock_header(self):
        import sys
        import types

        previous = sys.modules.get("displayio")
        sys.modules["displayio"] = types.SimpleNamespace(
            Group=CapturingGroup, Bitmap=CapturingBitmap,
            Palette=CapturingPalette, TileGrid=CapturingTileGrid,
        )
        try:
            display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
            display.label_type = CapturingLabel
            display.font = object()
            display.display = types.SimpleNamespace(root_group=None)
            display._mask = lambda *args: None
            display._present = lambda group: setattr(display, "shown", group)
            display._refresh = lambda animation_class=None: None
            display._attach_brightness_overlay = lambda group: None
            display._record_animation_update = lambda *args: None
            display._bin_group = None
            display._bin_key = None
            display._bin_weather = None
            display._bin_header_kind = None
            display._bin_content_group = None
            display._bin_bins_group = None
            display._bin_lorry_group = None
            display._bin_lorry_grid = None
            display._bin_types = ()
            screen = {"kind": "bin_collection", "title": "NEXT COLLECTION",
                      "collection_date": "2026-10-13", "slide_speed": 20,
                      "collections": [{"id": "mixed", "label": "Mixed recycling"}],
                      "weather": None}
            display._show_bin_collection(screen, "21:00", 4)
            self.assertEqual((display._bin_title.text, display._bin_label.text, display._bin_date.text),
                             ("NEXT COLLECTION", "Mixed recycling", "2026-10-13"))
            self.assertEqual(display._bin_clock_label.text, "21:00")
            long_screen = dict(screen)
            long_screen["collections"] = [{"id": "custom", "label": "Mixed recycling " * 5}]
            display._show_bin_collection(long_screen, "21:00", 4)
            start_x = display._bin_motion_group.x
            display._show_bin_collection(long_screen, "21:00", 5)
            self.assertEqual(start_x - display._bin_motion_group.x, 20)
        finally:
            if previous is None:
                del sys.modules["displayio"]
            else:
                sys.modules["displayio"] = previous
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
            self.assertNotIn("min_text", item)
            self.assertGreaterEqual(item["weekday_x"], item["left"])
            self.assertLessEqual(
                item["weekday_x"] + len(item["weekday"]) * led_display.WEATHER_FONT_WIDTH,
                item["right"],
            )
            compact_width = len(item["max_text"]) * (led_display.WEEKLY_WEATHER_GLYPH_WIDTH + 1)
            self.assertGreaterEqual(item["max_x"], item["left"])
            self.assertLessEqual(item["max_x"] + compact_width, item["right"])
            self.assertGreaterEqual(item["icon_x"], item["left"])
            self.assertLessEqual(item["icon_x"] + item["icon_width"], item["right"])
            previous_right = item["right"]

    def test_weekly_weather_fixture_keeps_max_only_contract_and_empty_fallback(self):
        layout = led_display._weekly_weather_layout(weekly_days())
        self.assertEqual([item["max_text"] for item in layout],
                         ["16C", "15C", "14C", "13C", "12C", "11C", "10C"])

        display = CapturingFixture()
        display._draw_screen({"kind": "weather_weekly", "days": weekly_days()}, phase=0)
        text = [item[0] for item in display.drawn]
        self.assertEqual([value for value in text if value in ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")],
                         ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"])
        self.assertFalse(any(value.startswith("MAX") or value.startswith("MIN") for value in text))

        empty = CapturingFixture()
        empty._draw_screen({"kind": "weather_weekly", "days": []}, phase=0)
        self.assertIn("Weather unavailable", [item[0] for item in empty.drawn])

    def test_today_weather_layout_has_six_ordered_full_width_blocks(self):
        layout = led_display._today_weather_layout(today_blocks())
        self.assertEqual(len(layout), 6)
        self.assertEqual(layout[0]["left"], 0)
        self.assertEqual(layout[-1]["right"], led_display.DISPLAY_WIDTH)
        self.assertEqual([item["label"] for item in layout],
                         ["Now", "2pm", "6pm", "10pm", "2am", "6am"])
        self.assertEqual([item["temp_text"] for item in layout],
                         ["10C", "11C", "12C", "13C", "14C", "15C"])
        for item in layout:
            self.assertGreaterEqual(item["icon_x"], item["left"])
            self.assertLessEqual(item["icon_x"] + item["icon_width"], item["right"])

        self.assertEqual(led_display.TODAY_WEATHER_ICON_Y, 11)
        self.assertEqual(led_display.TODAY_WEATHER_TEMPERATURE_Y, 27)

    def test_fullscreen_weather_screens_suppress_shared_header_chrome(self):
        for screen in (
            {
                "kind": "weather_weekly",
                "title": "7 DAY WEATHER",
                "days": weekly_days(),
            },
            {
                "kind": "weather_today",
                "title": "TODAY",
                "blocks": today_blocks(),
            },
            {
                "kind": "weather_sun",
                "title": "SUNRISE / SUNSET",
                "sunrise_time": "07:08",
                "sunset_time": "18:29",
            },
        ):
            with self.subTest(kind=screen["kind"]):
                display = CapturingFixture()
                display.pixels = FakePixels()
                screen.update({
                    "stale": True,
                    "weather": {"temperature_c": 17, "icon": "clear_day", "stale": True},
                })
                display.show(screen, clock_time="12:34", phase=2)
                text = [item[0] for item in display.drawn]
                self.assertNotIn("12:34", text)
                self.assertNotIn("17C", text)
                self.assertNotIn("STALE", text)
                self.assertEqual(display.pixels.shown, 1)

    def test_sun_weather_draws_today_sunrise_and_sunset_times(self):
        display = CapturingFixture()
        display._draw_screen({
            "kind": "weather_sun",
            "sunrise_time": "07:08",
            "sunset_time": "18:29",
        }, phase=0)
        text = [item[0] for item in display.drawn]
        self.assertIn("SUNRISE", "".join(text))
        self.assertIn("07:08", text)
        self.assertIn("SUNSET", "".join(text))
        self.assertIn("18:29", text)

    def test_sun_weather_animation_runs_sunrise_then_sunset(self):
        self.assertEqual(
            led_display._sun_weather_icon_y("clear_day", 0),
            led_display.SUN_WEATHER_RISE_START_Y,
        )
        self.assertEqual(
            led_display._sun_weather_icon_y("clear_night", 0),
            led_display.SUN_WEATHER_SET_START_Y,
        )

        midpoint = led_display.SUN_WEATHER_ANIMATION_SECONDS / 2
        sun_mid = led_display._sun_weather_icon_y("clear_day", midpoint)
        moon_mid = led_display._sun_weather_icon_y("clear_night", midpoint)
        self.assertLess(sun_mid, led_display.SUN_WEATHER_RISE_START_Y)
        self.assertGreater(sun_mid, led_display.SUN_WEATHER_ICON_Y)
        self.assertEqual(moon_mid, led_display.SUN_WEATHER_SET_START_Y)

        sunset_mid = led_display.SUN_WEATHER_ANIMATION_SECONDS + midpoint
        self.assertEqual(
            led_display._sun_weather_icon_y("clear_day", sunset_mid),
            led_display.SUN_WEATHER_ICON_Y,
        )
        moon_mid = led_display._sun_weather_icon_y("clear_night", sunset_mid)
        self.assertGreater(moon_mid, led_display.SUN_WEATHER_SET_START_Y)
        self.assertLess(moon_mid, led_display.SUN_WEATHER_ICON_Y)

        self.assertEqual(led_display._sun_weather_rgb("clear_day", False, 0), 0x0000FF)
        self.assertEqual(led_display._sun_weather_rgb("clear_day", False, 4), 0xFFFF00)
        self.assertEqual(led_display._sun_weather_rgb("clear_night", False, 4), 0xFFFF00)
        self.assertEqual(led_display._sun_weather_rgb("clear_night", False, 8), 0x0000FF)

        for phase in (
            led_display.SUN_WEATHER_TOTAL_ANIMATION_SECONDS,
            led_display.SUN_WEATHER_TOTAL_ANIMATION_SECONDS + 5,
        ):
            self.assertEqual(
                led_display._sun_weather_icon_y("clear_day", phase),
                led_display.SUN_WEATHER_ICON_Y,
            )
            self.assertEqual(
                led_display._sun_weather_icon_y("clear_night", phase),
                led_display.SUN_WEATHER_ICON_Y,
            )
            self.assertFalse(led_display._sun_weather_animation_active(phase))
        self.assertTrue(led_display._sun_weather_animation_active(led_display.SUN_WEATHER_ANIMATION_SECONDS))

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
