import sys
import types
import unittest
from unittest.mock import patch


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display
from matrix_config import (
    DEPARTURES_CALLING_FPS,
    HEADER_SLIDE_FPS,
    MATRIX_PRESENTATION_MODE,
    MATRIX_REFRESH_FPS,
    TODOIST_MARQUEE_FPS,
    TODOIST_PAGE_SLIDE_FPS,
    TODOIST_MARQUEE_SPEED,
)


class FakeGroup(list):
    def __init__(self):
        super().__init__()
        self.x = 0
        self.y = 0


class FakeBitmap:
    def __init__(self, width, height, colors):
        self.width = width
        self.height = height
        self.colors = colors
        self.values = {}

    def __setitem__(self, key, value):
        self.values[key] = value


class FakePalette(list):
    def __init__(self, size):
        super().__init__([0] * size)


class FakeTileGrid:
    def __init__(self, bitmap, pixel_shader=None, x=0, y=0):
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader
        self.x = x
        self.y = y


class FakeLabel:
    def __init__(self, font, text="", color=0, x=0, y=0):
        self.font = font
        self.text = str(text)
        self.color = color
        self.x = int(x)
        self.y = int(y)


class FakeFramebufferDisplay:
    def __init__(self, _matrix, auto_refresh=False):
        self.auto_refresh = auto_refresh
        self._root_group = None
        self.root_assignments = 0
        self.refresh_targets = []

    @property
    def root_group(self):
        return self._root_group

    @root_group.setter
    def root_group(self, value):
        self._root_group = value
        self.root_assignments += 1

    def refresh(self, target_frames_per_second=None):
        self.refresh_targets.append(target_frames_per_second)
        return True


class FakeRGBMatrix:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def fake_modules():
    displayio = types.SimpleNamespace(
        Group=FakeGroup,
        Bitmap=FakeBitmap,
        Palette=FakePalette,
        TileGrid=FakeTileGrid,
        release_displays=lambda: None,
    )
    framebufferio = types.SimpleNamespace(FramebufferDisplay=FakeFramebufferDisplay)
    rgbmatrix = types.SimpleNamespace(RGBMatrix=FakeRGBMatrix)
    bitmap_font = types.SimpleNamespace(load_font=lambda _path: object())
    adafruit_bitmap_font = types.SimpleNamespace(bitmap_font=bitmap_font)
    adafruit_display_text = types.SimpleNamespace(label=types.SimpleNamespace(Label=FakeLabel))
    return {
        "displayio": displayio,
        "framebufferio": framebufferio,
        "rgbmatrix": rgbmatrix,
        "adafruit_bitmap_font": adafruit_bitmap_font,
        "adafruit_display_text": adafruit_display_text,
    }


def todoist_screen(count=6):
    events = []
    for index in range(count):
        events.append(
            {
                "start": "2026-09-20",
                "date_text": "20/09",
                "all_day": True,
                "title": "Task {} with a deliberately long title that must scroll smoothly".format(index + 1),
            }
        )
    return {
        "id": "todoist",
        "kind": "calendar_agenda",
        "source": "todoist",
        "title": "UPCOMING",
        "viewport_size": 3,
        "page_seconds": 5,
        "events": events,
    }


def departures_screen():
    return {
        "id": "departures",
        "kind": "rail_combined",
        "title": "WAT departures",
        "services": [
            {
                "time": "19:40",
                "destination": "Windsor",
                "platform": "2",
                "stops": [{"station": "Clapham", "time": "19:52"}],
            },
            {
                "time": "19:50",
                "destination": "Reading",
                "platform": "4",
                "stops": [{"station": "Richmond", "time": "20:02"}],
            },
        ],
        "weather": {"temperature_c": 17, "icon": "clear_day"},
    }


class MatrixTodoistPerformanceTests(unittest.TestCase):
    def setUp(self):
        led_display.board.MTX_ADDRESS = (0, 1, 2, 3)
        led_display.board.MTX_COMMON = {}
        self._animation_profile = led_display.MATRIX_ANIMATION_PROFILE
        led_display.MATRIX_ANIMATION_PROFILE = "adaptive"

    def tearDown(self):
        led_display.MATRIX_ANIMATION_PROFILE = self._animation_profile

    def test_marquee_speed_does_not_exceed_update_cadence(self):
        self.assertLessEqual(TODOIST_MARQUEE_SPEED, float(MATRIX_REFRESH_FPS))

    def test_consecutive_todoist_frames_reuse_root_and_move_title_group(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            root = display.display.root_group
            assignments = display.display.root_assignments
            title_group = display._todoist_rows[0][1]
            first_x = title_group.x

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=1.0 / MATRIX_REFRESH_FPS,
            )

            self.assertIs(display.display.root_group, root)
            self.assertEqual(display.display.root_assignments, assignments)
            self.assertIs(display._todoist_rows[0][1], title_group)
            expected_offset = int(TODOIST_MARQUEE_SPEED / MATRIX_REFRESH_FPS + 1e-9)
            self.assertEqual(title_group.x, first_x - expected_offset)
            expected_target = (
                MATRIX_REFRESH_FPS
                if MATRIX_PRESENTATION_MODE == "target_fps"
                else None
            )
            self.assertEqual(display.display.refresh_targets[-1], expected_target)

    def test_page_slide_reuses_row_groups_and_changes_only_positions(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            row_groups = [row[0] for row in display._todoist_rows]
            assignments = display.display.root_assignments
            transition_at = display._todoist_page_transition_at(3)
            self.assertEqual([row.y for row in row_groups[:4]], [8, 16, 24, 64])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + 0.2,
            )
            self.assertEqual(display.display.root_assignments, assignments)
            self.assertEqual([row[0] for row in display._todoist_rows], row_groups)
            self.assertEqual([row.y for row in row_groups[:4]], [-4, 4, 12, 20])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + led_display.AGENDA_SLIDE_SECONDS,
            )
            self.assertEqual([row.y for row in row_groups[3:6]], [8, 16, 24])


    def test_page_waits_for_longest_marquee_and_settled_pause_before_slide(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(3)

            self.assertGreater(transition_at, screen["page_seconds"])
            row_groups = [row[0] for row in display._todoist_rows]
            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at - 0.1,
            )
            self.assertEqual([row.y for row in row_groups[:4]], [8, 16, 24, 64])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + 0.2,
            )
            self.assertEqual([row.y for row in row_groups[:4]], [-4, 4, 12, 20])

    def test_cadence_uses_8hz_for_marquee_and_12hz_only_for_page_slide(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(3)

            self.assertEqual(display.animation_cadence(screen, 1.0), TODOIST_MARQUEE_FPS)
            self.assertEqual(
                display.animation_cadence(screen, transition_at + 0.2),
                TODOIST_PAGE_SLIDE_FPS,
            )
            self.assertEqual(
                display.animation_cadence(screen, transition_at + led_display.AGENDA_SLIDE_SECONDS + 1.0),
                TODOIST_MARQUEE_FPS,
            )

    def test_header_cadence_and_position_use_the_same_phase(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)
            screen["weather"] = {"temperature_c": 17, "icon": "clear_day"}
            phase = 4.2
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=phase)

            expected_item, expected_offset = led_display._header_item_state(phase, screen["weather"])
            self.assertEqual(display.animation_cadence(screen, phase), HEADER_SLIDE_FPS)
            self.assertEqual(
                display._todoist_clock_group.x if expected_item == "clock" else display._todoist_weather_group.x,
                expected_offset,
            )

    def test_baseline_gate_keeps_fixed_b8_schedule(self):
        with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "baseline"):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                screen = todoist_screen(6)
                display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
                transition_at = display._todoist_page_transition_at(3)
                self.assertEqual(display.animation_cadence(screen, transition_at + 0.2), MATRIX_REFRESH_FPS)

    def test_settled_todoist_page_can_sleep_until_boundary(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=100)

            self.assertEqual(display.animation_cadence(screen, 100), 0)
            self.assertGreater(display.animation_sleep_seconds(screen, 100), 0)

    def test_departures_calling_and_header_slides_select_temporary_cadence(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            display.show(screen, clock_time="19:40", phase=0)

            self.assertEqual(display.animation_cadence(screen, 8.1), DEPARTURES_CALLING_FPS)
            self.assertEqual(display.animation_cadence(screen, 4.2), HEADER_SLIDE_FPS)
            self.assertEqual(display.animation_cadence(screen, 0.5), 0)
            self.assertGreater(display.animation_sleep_seconds(screen, 0.5), 0)

    def test_unchanged_partial_scene_does_not_present_duplicate_frame(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            refreshes = len(display.display.refresh_targets)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0.01)

            self.assertEqual(len(display.display.refresh_targets), refreshes)
            self.assertEqual(display._stats_todoist_ticks, 2)
            self.assertEqual(display._stats_todoist_changed, 1)

    def test_partial_scene_updates_keep_root_and_report_attribution(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            display.show(screen, clock_time="19:40", phase=8.1)
            root = display.display.root_group
            display.show(screen, clock_time="19:40", phase=8.2)

            self.assertIs(display.display.root_group, root)
            self.assertEqual(display._stats_rail_ticks, 2)
            self.assertGreaterEqual(display._stats_rail_changed, 1)
            self.assertGreaterEqual(display._stats_update_max, 0.0)

    def test_telemetry_counters_account_for_updates_refreshes_and_boundaries(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            display._record_animation_update("rail", True, 0.25)
            display._record_animation_update("rail", False, 0.50)
            display.note_fetch_overlap()
            display.note_cadence_switch()

            with patch.object(display.display, "refresh", return_value=True):
                with patch.object(led_display.time, "monotonic", side_effect=[10.0, 10.25, 10.25]):
                    self.assertTrue(display._refresh())

            self.assertEqual(display._stats_animation_ticks, 2)
            self.assertEqual(display._stats_rail_ticks, 2)
            self.assertEqual(display._stats_rail_changed, 1)
            self.assertAlmostEqual(display._stats_update_total, 0.75)
            self.assertAlmostEqual(display._stats_update_max, 0.50)
            self.assertEqual(display._stats_refresh_attempts, 1)
            self.assertEqual(display._stats_refresh_successes, 1)
            self.assertAlmostEqual(display._stats_refresh_total, 0.25)
            self.assertAlmostEqual(display._stats_refresh_max, 0.25)
            self.assertEqual(display._stats_fetch_overlap, 1)
            self.assertEqual(display._stats_cadence_switches, 1)

    def test_todoist_title_stays_at_end_until_page_transition(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            _, title_group, title, visible_chars = display._todoist_rows[0]
            scroll_seconds = display._todoist_title_scroll_seconds(title, visible_chars)
            final_x = display._todoist_title_x(title, scroll_seconds, visible_chars)
            transition_at = display._todoist_page_transition_at(3)

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=scroll_seconds + 0.5,
            )
            self.assertEqual(title_group.x, final_x)

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at - 0.05,
            )
            self.assertEqual(title_group.x, final_x)

    def test_second_page_marquee_restarts_from_initial_position(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(3)
            second_title_group = display._todoist_rows[3][1]

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + led_display.AGENDA_SLIDE_SECONDS,
            )
            self.assertEqual(second_title_group.x, led_display.AGENDA_TITLE_X)

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + led_display.AGENDA_SLIDE_SECONDS + 1.0 / MATRIX_REFRESH_FPS,
            )
            expected_offset = int(TODOIST_MARQUEE_SPEED / MATRIX_REFRESH_FPS + 1e-9)
            self.assertEqual(second_title_group.x, led_display.AGENDA_TITLE_X - expected_offset)


    def test_immediate_mode_uses_manual_immediate_refresh(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "immediate"):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                screen = todoist_screen(3)

                display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)

                self.assertFalse(display.display.auto_refresh)
                self.assertEqual(display.presentation_mode, "immediate")
                self.assertTrue(display.display.refresh_targets)
                self.assertIsNone(display.display.refresh_targets[-1])

    def test_auto_refresh_mode_does_not_call_manual_refresh(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "auto_refresh"):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                screen = todoist_screen(3)

                display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
                first_x = display._todoist_rows[0][1].x
                display.show(
                    screen,
                    clock_time="19:40",
                    clock_date="2026-09-20",
                    phase=1.0 / MATRIX_REFRESH_FPS,
                )

                self.assertTrue(display.display.auto_refresh)
                self.assertEqual(display.presentation_mode, "auto_refresh")
                self.assertEqual(display.display.refresh_targets, [])
                expected_offset = int(TODOIST_MARQUEE_SPEED / MATRIX_REFRESH_FPS + 1e-9)
                self.assertEqual(display._todoist_rows[0][1].x, first_x - expected_offset)

    def test_invalid_presentation_mode_is_rejected(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "unknown"):
            with patch.dict(sys.modules, fake_modules()):
                with self.assertRaises(ValueError):
                    led_display.MatrixDisplay()


if __name__ == "__main__":
    unittest.main()
