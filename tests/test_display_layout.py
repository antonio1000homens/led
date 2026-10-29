import sys
import types
import unittest
from datetime import datetime, timezone
from unittest import mock


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display
import matrix_config as rail_config
from flash_events import assistant_message_page


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
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader
        self.x, self.y = x, y
        self.flip_x = False


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
    def test_combined_sl7_rows_hide_expired_departures_and_keep_upcoming_rows(self):
        now = int(datetime(2026, 10, 13, 15, 0, tzinfo=timezone.utc).timestamp())
        screen = {
            "kind": "bus_departures_combined",
            "directions": {
                "new-malden": {
                    "status": "ok",
                    "departures": [
                        {"planned": "2026-10-13T14:58:00Z", "estimated": "2026-10-13T14:58:00Z",
                         "local_time": "15:58", "destination": "West Croydon"},
                        {"planned": "2026-10-13T15:05:00Z", "estimated": "2026-10-13T15:05:00Z",
                         "local_time": "16:05", "destination": "West Croydon"},
                    ],
                },
                "heathrow": {"status": "empty", "departures": []},
            },
        }

        rows = led_display.split_sl7_rows(screen, now)

        self.assertEqual(rows[0][4], [("5m", "16:05", False, False)])
        self.assertEqual(rows[1][4], [])

    def test_assistant_flash_displays_quote_style_page_and_advances(self):
        fixture = CapturingFixture()
        screen = {
            "kind": "flash",
            "title": "ASSISTANT",
            "label": "Alpha beta gamma delta",
        }
        fixture._draw_screen(screen, phase=0)
        self.assertIn(("ASSISTANT", 0, 1, (255, 170, 0)), fixture.drawn)
        self.assertTrue(any(item[0] == "Alpha beta gamma delta" for item in fixture.drawn))

        fixture.drawn.clear()
        long_text = " ".join("word%02d" % index for index in range(30))
        screen["label"] = long_text
        fixture._draw_screen(screen, phase=2.5)
        self.assertTrue(any(item[0] in assistant_message_page(long_text, 2.5)[1] for item in fixture.drawn))

    def test_assistant_maximum_length_line_is_centered_without_clipping(self):
        fixture = CapturingFixture()
        fixture._draw_screen({
            "kind": "flash",
            "title": "ASSISTANT",
            "label": "a" * 42,
        }, phase=0)

        line = next(item for item in fixture.drawn if item[0] == "a" * 42)
        self.assertEqual(line[1], 0)
        self.assertLessEqual(
            line[1] + 42 * led_display.ASSISTANT_MESSAGE_CHAR_ADVANCE,
            led_display.DISPLAY_WIDTH,
        )

    def test_rail_prebuild_bitmap_and_post_build_gc_defaults(self):
        self.assertFalse(led_display.MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT)
        self.assertTrue(led_display.MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT)
        self.assertFalse(rail_config.MATRIX_RAIL_PREBUILD_EXPERIMENT)
        self.assertEqual(rail_config.MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES, 1024 * 1024)
        self.assertEqual(rail_config.MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES, 512 * 1024)

    def test_rail_gc_waits_for_departure_rows_to_stop(self):
        display = types.SimpleNamespace(
            _rail_summary_seconds=0,
            _rail_calling_seconds=300,
            _rail_scroll_speed=20.0,
            _rail_calling_labels=[{"station_width": 6}],
        )
        screen = {
            "kind": "rail_combined",
            "services": [{}, {}, {}, {}, {}],
            "upcoming_train_pause_seconds": 2,
        }
        # The calling line is in its end pause, while the lower rows are
        # crossing the reset entrance at this phase.
        with mock.patch.object(led_display, "MATRIX_RAIL_ROWS_SCROLL", True):
            self.assertFalse(
                led_display.MatrixDisplay.rail_gc_safe_to_collect(
                    display, screen, 47.4
                )
            )
        with mock.patch.object(led_display, "MATRIX_RAIL_ROWS_SCROLL", False):
            self.assertTrue(
                led_display.MatrixDisplay.rail_gc_safe_to_collect(
                    display, screen, 11.5
                )
            )

    def test_rail_prebuild_obeys_heap_guard_without_touching_visible_root(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        visible_root = object()
        display.display = types.SimpleNamespace(root_group=visible_root)
        display._rail_group = None
        display._rail_scenes = {}
        display._rail_services = None
        display._rail_title = None
        display._rail_stale = None
        display._rail_weather = None
        display._rail_presentation = None
        display._rail_calling_seconds_cached = None
        display._rail_summary_seconds_cached = None
        display._rail_station_speed_cached = None
        display._rail_station_spacing_cached = None
        display._rail_rows_scroll_cached = None
        display._rail_static_rows_bitmap_cached = None
        display._rail_pause_seconds_cached = None
        screen = {"kind": "rail_combined", "services": [{"id": "one"}]}
        with mock.patch.object(display, "_heap_free", return_value=1000), \
                mock.patch.object(display, "_build_rail_scene") as build:
            self.assertFalse(display.prepare_rail_scene(screen, minimum_free_bytes=600,
                                                        maximum_scene_bytes=500))
        build.assert_not_called()
        self.assertIs(display.display.root_group, visible_root)

    def test_rail_scene_discard_releases_only_hidden_cache(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        visible_root = object()
        hidden_rail = object()
        display.display = types.SimpleNamespace(root_group=visible_root)
        display._rail_group = hidden_rail
        display._rail_scenes = {"calling": object()}
        display._rail_services = [{"id": "old"}]
        display._rail_prebuilt_pending = True
        display._rail_calling_labels = []
        display._rail_departure_rows = []
        display._rail_phase = None
        display._rail_clock_group = None
        display._rail_clock_label = None
        display._rail_weather_group = None
        with mock.patch.object(display, "_heap_free", side_effect=[900, 900]):
            self.assertTrue(display.discard_prepared_rail_scene(reason="changed"))
        self.assertIs(display.display.root_group, visible_root)
        self.assertIsNone(display._rail_group)
        self.assertEqual(display._rail_scenes, {})
        self.assertIsNone(display._rail_services)
        self.assertFalse(display._rail_prebuilt_pending)

        display._rail_group = hidden_rail
        display.display.root_group = hidden_rail
        self.assertFalse(display.discard_prepared_rail_scene(reason="active"))
        self.assertIs(display._rail_group, hidden_rail)
        self.assertIs(display.display.root_group, hidden_rail)

    def test_rail_prebuild_keeps_scene_hidden_and_does_not_refresh(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        visible_root = object()
        display.display = types.SimpleNamespace(root_group=visible_root, refresh=mock.Mock())
        display._rail_group = None
        display._rail_scenes = {}
        screen = {"kind": "rail_combined", "services": [{"id": "one"}], "title": "Departures"}

        def build(payload, clock_time, phase):
            del clock_time, phase
            display._rail_group = object()
            display._rail_services = payload["services"]
            display._rail_title = payload.get("title")
            display._rail_stale = False
            display._rail_weather = None
            display._rail_presentation = None
            display._rail_calling_seconds_cached = led_display.RAIL_CALLING_SECONDS
            display._rail_summary_seconds_cached = led_display.RAIL_SUMMARY_SECONDS
            display._rail_station_speed_cached = None
            display._rail_station_spacing_cached = None
            display._rail_rows_scroll_cached = led_display.MATRIX_RAIL_ROWS_SCROLL
            display._rail_static_rows_bitmap_cached = led_display.MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT
            display._rail_pause_seconds_cached = 2

        with mock.patch.object(display, "_heap_free", side_effect=[10000, 9500, 9400, 9000]), \
                mock.patch.object(display, "_build_rail_scene", side_effect=build):
            self.assertTrue(display.prepare_rail_scene(screen, minimum_free_bytes=1000,
                                                       maximum_scene_bytes=1000))
        self.assertTrue(display.rail_scene_prebuilt(screen))
        self.assertIs(display.display.root_group, visible_root)
        display.display.refresh.assert_not_called()

    def test_rail_scene_cache_identity_includes_payload_and_render_settings(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display._rail_group = object()
        display._rail_services = [{"id": "one"}]
        display._rail_title = "Departures"
        display._rail_stale = False
        display._rail_weather = None
        display._rail_presentation = {"calling_seconds": 30}
        display._rail_calling_seconds_cached = 30
        display._rail_summary_seconds_cached = 0
        display._rail_station_speed_cached = 20
        display._rail_station_spacing_cached = 3
        display._rail_rows_scroll_cached = led_display.MATRIX_RAIL_ROWS_SCROLL
        display._rail_static_rows_bitmap_cached = led_display.MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT
        display._rail_pause_seconds_cached = 2
        screen = {
            "kind": "rail_combined", "services": [{"id": "one"},],
            "title": "Departures", "stale": False,
            "rail_presentation": {"calling_seconds": 30},
            "calling_seconds": 30, "summary_seconds": 0,
            "station_scroll_speed": 20, "station_list_spacing": 3,
            "upcoming_train_pause_seconds": 2,
        }
        self.assertTrue(display.rail_scene_ready(screen))
        with mock.patch.object(led_display, "MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT", False):
            self.assertFalse(display.rail_scene_ready(screen))
        screen["services"] = [{"id": "changed"}]
        self.assertFalse(display.rail_scene_ready(screen))
        screen["services"] = [{"id": "one"}]
        screen["station_scroll_speed"] = 24
        self.assertFalse(display.rail_scene_ready(screen))

    def test_rail_prebuild_reuses_equivalent_cached_scene(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.display = types.SimpleNamespace(root_group=object())
        display._rail_group = object()
        display._rail_scenes = {}
        display._rail_services = [{"id": "one"}]
        display._rail_title = "Departures"
        display._rail_stale = False
        display._rail_weather = None
        display._rail_presentation = None
        display._rail_calling_seconds_cached = led_display.RAIL_CALLING_SECONDS
        display._rail_summary_seconds_cached = led_display.RAIL_SUMMARY_SECONDS
        display._rail_station_speed_cached = None
        display._rail_station_spacing_cached = None
        display._rail_rows_scroll_cached = led_display.MATRIX_RAIL_ROWS_SCROLL
        display._rail_static_rows_bitmap_cached = led_display.MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT
        display._rail_pause_seconds_cached = 2
        screen = {"kind": "rail_combined", "services": [{"id": "one"}], "title": "Departures"}
        with mock.patch.object(display, "_build_rail_scene") as build, \
                mock.patch.object(display, "_heap_free") as heap_free:
            self.assertTrue(display.prepare_rail_scene(screen))
        build.assert_not_called()
        heap_free.assert_not_called()

    def test_rail_prebuild_rejects_stale_or_empty_payload(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.discard_prepared_rail_scene = mock.Mock()
        with mock.patch.object(display, "_build_rail_scene") as build:
            self.assertFalse(display.prepare_rail_scene({
                "kind": "rail_combined", "services": [{"id": "one"}], "stale": True,
            }))
            self.assertFalse(display.prepare_rail_scene({
                "kind": "rail_combined", "services": [], "stale": False,
            }))
        self.assertEqual(display.discard_prepared_rail_scene.call_count, 2)
        build.assert_not_called()

    def test_static_rail_row_experiment_uses_one_bitmap_per_service(self):
        import sys

        class GlyphBitmap:
            def __getitem__(self, key):
                return key == (0, 0)

        class Glyph:
            width = 2
            height = 3
            dx = 0
            dy = 0
            shift_x = 3
            bitmap = GlyphBitmap()

        class Font:
            ascent = 7

            def load_glyphs(self, codepoints):
                del codepoints

            def get_glyph(self, codepoint):
                del codepoint
                return Glyph()

        previous = sys.modules.get("displayio")
        sys.modules["displayio"] = types.SimpleNamespace(
            Group=CapturingGroup, Bitmap=CapturingBitmap,
            Palette=CapturingPalette, TileGrid=CapturingTileGrid,
        )
        try:
            display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
            display.font = Font()
            group = CapturingGroup()
            with mock.patch.object(led_display, "MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT", True):
                display._rail_service(
                    group,
                    {"scheduled": "12:34", "destination": "Waterloo", "platform": "2",
                     "cancelled": True, "status": "CANCELLED"},
                    0xFF3300,
                    0,
                    12,
                    250,
                )
            self.assertEqual(len(group), 1)
            self.assertIsInstance(group[0], CapturingTileGrid)
            self.assertEqual(group[0].x, 0)
            self.assertEqual(group[0].pixel_shader.values[1], 0xFF3300)
        finally:
            if previous is None:
                del sys.modules["displayio"]
            else:
                sys.modules["displayio"] = previous

    def test_failed_cold_rail_build_restores_disabled_gc_state(self):
        import sys

        class FakeGC:
            def __init__(self):
                self.disabled = 0

            def disable(self):
                self.disabled += 1

        previous = sys.modules.get("gc")
        fake_gc = FakeGC()
        sys.modules["gc"] = fake_gc
        try:
            display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
            display._rail_cache_matches = mock.Mock(return_value=False)
            display._rail_prebuilt_pending = True
            display._heap_free = mock.Mock(return_value=1000)
            display._build_rail_scene = mock.Mock(side_effect=MemoryError("full"))
            with mock.patch.object(led_display, "MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT", True):
                with self.assertRaises(MemoryError):
                    display._show_rail({"kind": "rail_combined", "services": [{}]}, "12:00", 0)
            self.assertEqual(fake_gc.disabled, 1)
            self.assertFalse(display._rail_prebuilt_pending)
        finally:
            if previous is None:
                del sys.modules["gc"]
            else:
                sys.modules["gc"] = previous

    def test_prebuilt_scene_marker_is_consumed_at_handoff(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        visible_root = object()
        rail_root = object()
        display.display = types.SimpleNamespace(root_group=visible_root)
        display._rail_group = rail_root
        display._rail_prebuilt_pending = True
        display._rail_cache_matches = mock.Mock(return_value=True)
        display._rail_phase = "calling"
        display._rail_first_refresh_pending = False
        display._rail_update_phase = 0
        display._heap_free = mock.Mock(return_value=None)
        display._update_rail_scene = mock.Mock(return_value=False)
        display._attach_brightness_overlay = mock.Mock()
        display._animation_class = mock.Mock(return_value="departures_calling")
        display._record_animation_update = mock.Mock()
        display._refresh = mock.Mock()
        display.telemetry_enabled = False
        screen = {"kind": "rail_combined", "services": [{"id": "one"}]}

        display._show_rail(screen, "12:00", 0)

        self.assertIs(display.display.root_group, rail_root)
        self.assertFalse(display._rail_prebuilt_pending)
        display._refresh.assert_called_once_with("departures_calling")

    def test_novelty_screens_are_shifted_up_two_pixels(self):
        for kind, heading, field in (
            ("dad_joke", "DAD JOKE", "joke"),
            ("random_fact", "DID YOU KNOW?", "fact"),
        ):
            with self.subTest(kind=kind):
                display = CapturingFixture()
                display._draw_screen({"kind": kind, field: "A short test"}, 0)
                self.assertIn((heading, 0, 3, (255, 170, 0)), display.drawn)
                self.assertIn(("A short test", 0, 12, (255, 255, 255)), display.drawn)

    def test_loading_title_matches_upcoming_header_position(self):
        display = CapturingFixture()
        display.pixels = FakePixels()
        display.show_loading()
        self.assertIn(("UPCOMING", 0, 0, (255, 170, 0)), display.drawn)

    def test_bin_collection_one_and_two_collection_layout(self):
        display = CapturingFixture()
        display._draw_screen({
            "kind": "bin_collection", "title": "NEXT COLLECTION",
            "collection_date": "2026-10-13",
            "collections": [{"id": "mixed", "label": "Mixed recycling"}],
            "slide_speed": 20,
        }, 4, clock_date="2026-10-07")
        self.assertIn(("NEXT COLLECTION", 0, 3, (255, 170, 0)), display.drawn)
        self.assertIn(("Mixed recycling", 88, 14, (255, 255, 255)), display.drawn)
        self.assertIn(("DUE IN 6 DAYS", 167, 14, (170, 170, 170)), display.drawn)
        display.drawn = []
        display._draw_screen({
            "kind": "bin_collection", "title": "NEXT COLLECTION",
            "collection_date": "2026-10-13",
            "collections": [{"id": "mixed", "label": "Mixed recycling"}],
            "slide_speed": 20,
        }, 5, clock_date="2026-10-07")
        self.assertIn(("DUE IN 6 DAYS", 167, 14, (170, 170, 170)), display.drawn)

        display.drawn = []
        display._draw_screen({
            "kind": "bin_collection", "title": "NEXT COLLECTION",
            "collection_date": "2026-10-13",
            "collections": [{"id": "mixed", "label": "Mixed recycling"},
                            {"id": "paper", "label": "Paper"}],
            "slide_speed": 20,
        }, 4, clock_date="2026-10-07")
        # The combined collection label shares this row with the due date,
        # so it is clipped to the space available beside the parked lorry.
        self.assertIn(("Mixed recycling / P", 88, 14, (255, 255, 255)), display.drawn)

    def test_bin_collection_long_label_stops_beside_parked_lorry(self):
        display = CapturingFixture()
        screen = {"kind": "bin_collection", "title": "NEXT COLLECTION",
                  "collection_date": "2026-10-13", "slide_speed": 20,
                  "collections": [{"id": "x", "label": "A very long collection label for the MatrixPortal"}]}
        display._draw_screen(screen, 4)
        first = next(item for item in display.drawn if item[0].startswith("A very long"))
        display.drawn = []
        display._draw_screen(screen, 5)
        second = next(item for item in display.drawn if item[0].startswith("A very long"))
        self.assertEqual(first[1], second[1])
        self.assertEqual(first[1], led_display.BIN_LORRY_WIDTH + led_display.HEADER_GAP)
        self.assertNotEqual(first[0], screen["collections"][0]["label"])

    def test_bin_collection_date_follows_lorry_in_from_right(self):
        display = CapturingFixture()
        screen = {"kind": "bin_collection", "title": "NEXT COLLECTION",
                  "collection_date": "2026-10-13", "slide_speed": 20,
                  "collections": [{"id": "x", "label": "Mixed recycling"}]}
        display._draw_screen(screen, 3, clock_date="2026-10-07")
        self.assertNotIn(("DUE IN 6 DAYS", 120, 25, (170, 170, 170)), display.drawn)
        self.assertIn(("Mixed recycling", 152, 14, (255, 255, 255)), display.drawn)
        self.assertIn(("DUE IN 6 DAYS", 231, 14, (170, 170, 170)), display.drawn)
        display._draw_screen(screen, 5, clock_date="2026-10-07")
        self.assertIn(("DUE IN 6 DAYS", 167, 14, (170, 170, 170)), display.drawn)

    def test_bin_collection_stops_animating_after_lorry_enters(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        screen = {"kind": "bin_collection", "slide_speed": 20,
                  "collections": [{"id": "x", "label": "X" * 50}]}
        with mock.patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "baseline"):
            self.assertTrue(display.animation_active(screen, 0))
            parked_phase = led_display.BIN_LORRY_SECONDS
            self.assertFalse(display.animation_active(screen, parked_phase))
            self.assertEqual(display.animation_cadence(screen, parked_phase), 0)
            self.assertEqual(led_display._bin_collection_footer_x(screen, 5), 0)

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
            display._bin_lorry_group = None
            display._bin_lorry_grid = None
            screen = {"kind": "bin_collection", "title": "NEXT COLLECTION",
                      "collection_date": "2026-10-13", "slide_speed": 20,
                      "collections": [{"id": "mixed", "label": "Mixed recycling"}],
                      "weather": None}
            display._show_bin_collection(screen, "21:00", "2026-10-07", 2)
            self.assertFalse(display._bin_content_group.hidden)
            self.assertFalse(display._bin_lorry_group.hidden)
            self.assertEqual(display._bin_lorry_group.x, led_display._bin_lorry_x(2))
            self.assertEqual(display._bin_lorry_grid.x, 0)
            footer_mid_x = display._bin_footer_group.x
            self.assertEqual(footer_mid_x, display._bin_lorry_group.x)
            display._show_bin_collection(screen, "21:00", "2026-10-07", 3)
            self.assertFalse(display._bin_content_group.hidden)
            self.assertFalse(display._bin_lorry_group.hidden)
            self.assertEqual(display._bin_lorry_group.x, led_display._bin_lorry_x(3))
            display._show_bin_collection(screen, "21:00", "2026-10-07", 4)
            self.assertFalse(display._bin_content_group.hidden)
            self.assertFalse(display._bin_lorry_group.hidden)
            self.assertEqual(display._bin_lorry_group.x, 0)
            self.assertEqual(display._bin_date.y, 14)
            self.assertEqual((display._bin_title.text, display._bin_date.text),
                             ("NEXT COLLECTION", "DUE IN 6 DAYS"))
            self.assertEqual(display._bin_label.text, "Mixed recycling")
            self.assertEqual(display._bin_lorry_label.text, "Mixed recycling")
            self.assertEqual(display._bin_footer_group.x, 0)
            self.assertFalse(display._bin_lorry_grid.flip_x)
            self.assertEqual(display._bin_clock_label.text, "21:00")
            self.assertFalse(hasattr(display, "_bin_bins_group"))
            long_screen = dict(screen)
            long_screen["collections"] = [{"id": "custom", "label": "Mixed recycling " * 5}]
            display._show_bin_collection(long_screen, "21:00", "2026-10-07", 4)
            start_x = display._bin_lorry_group.x
            display._show_bin_collection(long_screen, "21:00", "2026-10-07", 5)
            self.assertEqual(start_x, 0)
            self.assertEqual(display._bin_lorry_group.x, 0)
            self.assertLess(len(display._bin_lorry_label.text), len("Mixed recycling " * 5))
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

    def test_stale_weather_icons_use_one_bit_visible_blue(self):
        self.assertEqual(led_display._weather_sprite_color("B", stale=True), 0x0000FF)
        self.assertEqual(
            led_display._weather_sprite_color("B", stale=False),
            led_display.WEATHER_SPRITE_PALETTE["B"],
        )

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
        for phase in range(0, int(led_display.SUN_WEATHER_TOTAL_ANIMATION_SECONDS) + 1):
            sun_y = led_display._sun_weather_icon_y("clear_day", phase)
            moon_y = led_display._sun_weather_icon_y("clear_night", phase)
            self.assertGreaterEqual(sun_y, 0)
            self.assertLessEqual(
                sun_y + 21,
                32,
            )
            self.assertGreaterEqual(moon_y, 0)
            self.assertLessEqual(
                moon_y + 21,
                32,
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

        self.assertEqual(len(led_display._celestial_sprite_rows("clear_day")), 21)
        self.assertEqual(len(led_display._celestial_sprite_rows("clear_night")), 21)
        self.assertEqual(led_display.WEATHER_SPRITE_PALETTE["Y"], 0xFFFF00)
        self.assertEqual(led_display.WEATHER_SPRITE_PALETTE["B"], 0x0000FF)

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

    def test_departure_cancelled_status_fits_after_left_shifted_platform(self):
        display = CapturingFixture()
        display._draw_screen({
            "kind": "rail_combined",
            "services": [{
                "time": "12:00", "destination": "Millwall FC", "platform": "2",
                "cancelled": True, "status": "CANCELLED",
            }],
        }, phase=0, clock_date="2026-09-15")

        platform = next(item for item in display.drawn if item[0] == "P2")
        cancelled = next(item for item in display.drawn if item[0] == "CANCELLED")
        self.assertEqual(platform[1], 154)
        self.assertEqual(platform[2], cancelled[2])
        self.assertGreaterEqual(cancelled[1], platform[1] + 3 * led_display.WEATHER_FONT_WIDTH)


if __name__ == "__main__":
    unittest.main()
