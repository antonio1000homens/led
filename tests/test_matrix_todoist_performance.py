import copy
import sys
import types
import unittest
from unittest.mock import patch


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display
from formatting import prepare_rail_presentation
from matrix_config import (
    DEPARTURES_CALLING_FPS,
    MATRIX_PRESENTATION_MODE,
    MATRIX_ANIMATION_PROFILES,
    MATRIX_ANIMATION_PROFILE as DEFAULT_MATRIX_ANIMATION_PROFILE,
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

    def fill(self, value):
        self.values = {}
        self.fill_value = value


class FakePalette(list):
    def __init__(self, size):
        super().__init__([0] * size)
        self.transparent = set()

    def make_transparent(self, index):
        self.transparent.add(index)


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


def departures_screen(long_calling=False):
    first_stops = [{"station": "Clapham", "time": "19:52"}]
    second_stops = [{"station": "Richmond", "time": "20:02"}]
    if long_calling:
        first_stops = [
            {"station": "Clapham Junction", "time": "19:52"},
            {"station": "East Croydon", "time": "20:04"},
            {"station": "Redhill", "time": "20:18"},
            {"station": "Gatwick Airport", "time": "20:31"},
        ]
    return {
        "id": "departures",
        "kind": "rail_combined",
        "title": "WAT departures",
        "services": [
            {
                "time": "19:40",
                "destination": "Windsor",
                "platform": "2",
                "stops": first_stops,
            },
            {
                "time": "19:50",
                "destination": "Reading",
                "platform": "4",
                "stops": second_stops,
            },
            {
                "time": "20:00",
                "destination": "Waterloo",
                "platform": "1",
                "stops": [{"station": "Wimbledon", "time": "20:08"}],
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

    def test_static_weekly_weather_reuses_icon_scene_between_render_ticks(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = {
                "kind": "weather_weekly",
                "stale": False,
                "days": [{
                    "weekday": "MON", "weather_code": 0, "icon": "clear_day",
                    "temperature_max_c": 18,
                }],
            }

            display.show(screen, phase=0)
            group = display.display.root_group
            tile_grid = next(item for item in group if isinstance(item, FakeTileGrid))
            root_assignments = display.display.root_assignments
            display.show(screen, phase=1)

            self.assertIs(display.display.root_group, group)
            self.assertIs(next(item for item in group if isinstance(item, FakeTileGrid)), tile_grid)
            self.assertEqual(display.display.root_assignments, root_assignments)

            screen["days"][0]["temperature_max_c"] = 19
            display.show(screen, phase=2)
            self.assertIsNot(display.display.root_group, group)

    def test_marquee_speed_does_not_exceed_update_cadence(self):
        self.assertLessEqual(TODOIST_MARQUEE_SPEED, float(MATRIX_REFRESH_FPS))

    def test_default_profile_is_the_8_hz_control(self):
        self.assertEqual(DEFAULT_MATRIX_ANIMATION_PROFILE, "baseline")
        self.assertEqual(
            MATRIX_ANIMATION_PROFILES[DEFAULT_MATRIX_ANIMATION_PROFILE]["departures_calling"],
            MATRIX_REFRESH_FPS,
        )

    def test_transition_profiles_only_raise_short_transition_cadence(self):
        self.assertEqual(MATRIX_ANIMATION_PROFILES["baseline"]["todoist_page_slide"], MATRIX_REFRESH_FPS)
        self.assertEqual(MATRIX_ANIMATION_PROFILES["adaptive"]["todoist_page_slide"], 12)
        self.assertEqual(MATRIX_ANIMATION_PROFILES["adaptive"]["steam_train"], 12)
        self.assertEqual(MATRIX_ANIMATION_PROFILES["transition_15"]["todoist_page_slide"], 15)
        self.assertEqual(MATRIX_ANIMATION_PROFILES["transition_20"]["todoist_page_slide"], 20)
        for profile in ("baseline", "adaptive", "transition_15", "transition_20"):
            self.assertEqual(MATRIX_ANIMATION_PROFILES[profile]["todoist_marquee"], 8)
        self.assertEqual(MATRIX_ANIMATION_PROFILES["baseline"]["departures_calling"], 8)
        for profile in ("adaptive", "transition_15", "transition_20"):
            self.assertEqual(MATRIX_ANIMATION_PROFILES[profile]["departures_calling"], 12)

    def test_transition_profiles_select_only_page_and_header_cadence(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(0)

            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_15"):
                self.assertEqual(display.animation_cadence(screen, transition_at + 0.2), 15)
                self.assertEqual(display.animation_cadence(screen, 1.0), 8)
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_20"):
                self.assertEqual(display.animation_cadence(screen, transition_at + 0.2), 20)
                self.assertEqual(display.animation_cadence(screen, 1.0), 8)

    def test_transition_profiles_keep_boundary_driven_wakeups(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(3)

            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "adaptive"):
                adaptive_sleep = display.animation_sleep_seconds(screen, 0.5)
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_15"):
                transition_15_sleep = display.animation_sleep_seconds(screen, 0.5)
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_20"):
                transition_20_sleep = display.animation_sleep_seconds(screen, 0.5)
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "baseline"):
                baseline_sleep = display.animation_sleep_seconds(screen, 0.5)

            self.assertEqual(adaptive_sleep, transition_15_sleep)
            self.assertEqual(adaptive_sleep, transition_20_sleep)
            self.assertGreater(adaptive_sleep, 0)
            self.assertLessEqual(adaptive_sleep, transition_at - 0.5)
            self.assertEqual(baseline_sleep, adaptive_sleep)

            # Once the boundary is reached, each candidate selects its own
            # transition cadence rather than remaining asleep at the control
            # profile's boundary.
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_15"):
                self.assertEqual(display.animation_cadence(screen, transition_at + 0.01), 15)
            with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "transition_20"):
                self.assertEqual(display.animation_cadence(screen, transition_at + 0.01), 20)

    def test_brightness_adjustment_keeps_root_and_refreshes_once(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)

            root = display.display.root_group
            refreshes = len(display.display.refresh_targets)
            self.assertEqual(display.brightness_percent, 100)
            self.assertIs(root[-1], display._brightness_overlay)

            self.assertEqual(display.adjust_brightness(-1), 75)
            self.assertEqual(display.brightness_percent, 75)
            self.assertIs(display.display.root_group, root)
            self.assertIs(root[-1], display._brightness_overlay)
            self.assertEqual(len(display.display.refresh_targets), refreshes + 1)
            blocked = sum(1 for value in display._brightness_bitmap.values.values() if value == 1)
            self.assertEqual(blocked, (led_display.DISPLAY_WIDTH * 32) // 4)

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
            self.assertEqual([row.y for row in row_groups[:4]], [11, 19, 27, 64])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + 0.2,
            )
            self.assertEqual(display.display.root_assignments, assignments)
            self.assertEqual([row[0] for row in display._todoist_rows], row_groups)
            self.assertEqual([row.y for row in row_groups[:4]], [7, 15, 23, 31])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + led_display.AGENDA_SLIDE_SECONDS,
            )
            self.assertEqual([row.y for row in row_groups[1:4]], [11, 19, 27])


    def test_page_waits_for_longest_marquee_and_settled_pause_before_slide(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(0)

            self.assertGreater(transition_at, screen["page_seconds"])
            row_groups = [row[0] for row in display._todoist_rows]
            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at - 0.1,
            )
            self.assertEqual([row.y for row in row_groups[:4]], [11, 19, 27, 64])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + 0.2,
            )
            self.assertEqual([row.y for row in row_groups[:4]], [7, 15, 23, 31])

    def test_cadence_uses_8hz_for_marquee_and_12hz_only_for_page_slide(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            transition_at = display._todoist_page_transition_at(0)

            self.assertEqual(display.animation_cadence(screen, 1.0), TODOIST_MARQUEE_FPS)
            self.assertEqual(
                display.animation_cadence(screen, transition_at + 0.2),
                TODOIST_PAGE_SLIDE_FPS,
            )
            self.assertEqual(
                display.animation_cadence(screen, transition_at + led_display.AGENDA_SLIDE_SECONDS + 1.0),
                TODOIST_MARQUEE_FPS,
            )

    def test_header_clock_stays_visible_without_weather_rotation(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(3)
            screen["weather"] = {"temperature_c": 17, "icon": "clear_day"}
            phase = 7.5
            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=phase)

            expected_item, expected_offset = led_display._header_item_state(phase, screen["weather"])
            self.assertEqual(expected_item, "clock")
            self.assertEqual(expected_offset, 0)
            self.assertEqual(display.animation_cadence(screen, phase), TODOIST_MARQUEE_FPS)
            self.assertNotEqual(display._animation_class(screen, phase), "header_slide")
            self.assertEqual(
                display._todoist_clock_group.x if expected_item == "clock" else display._todoist_weather_group.x,
                expected_offset,
            )
            self.assertEqual(led_display._header_item_state(13.99, screen["weather"]), ("clock", 0))
            self.assertEqual(led_display._header_item_state(14.0, screen["weather"]), ("clock", 0))

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

    def test_departures_calling_animates_but_header_switch_does_not(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 8
            display.show(screen, clock_time="19:40", phase=0)

            self.assertEqual(display.animation_cadence(screen, 8.1), DEPARTURES_CALLING_FPS)
            self.assertEqual(display.animation_cadence(screen, 4.2), 0)
            self.assertEqual(display.animation_cadence(screen, 0.5), 0)
            self.assertGreater(display.animation_sleep_seconds(screen, 0.5), 0)

            long_screen = departures_screen(long_calling=True)
            long_screen["summary_seconds"] = 8
            self.assertEqual(display.animation_cadence(long_screen, 10.0), DEPARTURES_CALLING_FPS)
            self.assertEqual(display.animation_cadence(long_screen, 12.5), DEPARTURES_CALLING_FPS)

    def test_baseline_rail_cadence_only_runs_while_pixels_are_moving(self):
        with patch.object(led_display, "MATRIX_ANIMATION_PROFILE", "baseline"):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                screen = departures_screen()
                screen["summary_seconds"] = 8

                self.assertEqual(display.animation_cadence(screen, 4.2), 0)
                self.assertEqual(
                    display.animation_cadence(screen, 8.1), MATRIX_REFRESH_FPS
                )

    def test_departure_sleep_boundary_matches_list_based_reference(self):
        with patch.dict(sys.modules, fake_modules()), patch.object(
            led_display, "MATRIX_RAIL_ROWS_SCROLL", True
        ):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 8
            screen["calling_seconds"] = 32
            screen["upcoming_train_pause_seconds"] = 2
            screen["services"].extend(
                copy.deepcopy(screen["services"][-1]) for _ in range(5)
            )

            def legacy_periodic_boundary(elapsed, edges, cycle):
                within = max(0.0, float(elapsed or 0)) % cycle
                candidates = []
                for edge in edges:
                    delta = (float(edge) % cycle) - within
                    if delta <= 1e-6:
                        delta += cycle
                    candidates.append(delta)
                return min(candidates) if candidates else cycle

            for phase in (8.1, 8.7, 10.9, 18.2, 24.3, 31.9, 32.0, 39.5):
                with self.subTest(phase=phase):
                    calling_seconds = screen["calling_seconds"]
                    summary_seconds = screen["summary_seconds"]
                    cycle = summary_seconds + calling_seconds
                    within = phase % cycle
                    boundaries = [
                        led_display._header_next_boundary_seconds(
                            phase, screen.get("weather")
                        )
                    ]
                    if led_display.rail_phase(
                        phase, summary_seconds, calling_seconds
                    ) == "summary":
                        boundaries.append(summary_seconds - within)
                    else:
                        boundaries.append(cycle - within)
                        calling_elapsed = led_display.rail_marquee_elapsed(
                            phase, summary_seconds, calling_seconds
                        )
                        upcoming_count = len(screen["services"]) - 1
                        pause = screen["upcoming_train_pause_seconds"]
                        max_start = max(0, upcoming_count - 2)
                        if max_start:
                            step = pause + led_display.DEPARTURE_SLIDE_SECONDS
                            normal = (max_start + 1) * step
                            row_cycle = (
                                normal
                                + led_display.DEPARTURE_RESET_GAP_SECONDS
                                + led_display.DEPARTURE_RESET_SLIDE_SECONDS
                            )
                            row_edges = [
                                0.0,
                                normal,
                                normal + led_display.DEPARTURE_RESET_GAP_SECONDS,
                                row_cycle,
                            ]
                            for index in range(max_start + 1):
                                edge = index * step + pause
                                row_edges.extend(
                                    (edge, edge + led_display.DEPARTURE_SLIDE_SECONDS)
                                )
                            boundaries.append(
                                legacy_periodic_boundary(
                                    calling_elapsed, row_edges, row_cycle
                                )
                            )
                        speed, _ = led_display._station_scroll_settings(screen)
                        travel = led_display.rail_calling_timing(
                            screen["services"], speed,
                            font_width=led_display.WEATHER_FONT_WIDTH,
                        )[0]
                        marquee_cycle = travel + led_display.CALLING_MARQUEE_PAUSE_SECONDS
                        boundaries.append(
                            legacy_periodic_boundary(
                                calling_elapsed,
                                (0.0, travel, marquee_cycle),
                                marquee_cycle,
                            )
                        )
                    expected = max(0.05, min(boundaries))
                    self.assertAlmostEqual(
                        display.animation_sleep_seconds(screen, phase), expected
                    )

    def test_animation_active_tracks_pixels_that_are_moving(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            long_screen = departures_screen(long_calling=True)
            long_screen["summary_seconds"] = 8
            self.assertFalse(display.animation_active(long_screen, 3.0))
            self.assertTrue(display.animation_active(long_screen, 10.0))

    def test_calling_marquee_motion_detection_tracks_repeating_cycle(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen(long_calling=True)
            screen["summary_seconds"] = 8
            text = led_display.calling_text(screen["services"][0])
            prefix_width = len(led_display.CALLING_LABEL) * led_display.WEATHER_FONT_WIDTH
            station_text = text[len(led_display.CALLING_LABEL):]
            speed, _ = led_display._station_scroll_settings(screen)
            travel = (led_display.DISPLAY_WIDTH - prefix_width
                      + len(station_text) * led_display.WEATHER_FONT_WIDTH) / speed

            def phase_for_calling_elapsed(elapsed):
                cycle_index = int(elapsed // 12.0)
                within_call = elapsed % 12.0
                return cycle_index * 20.0 + 8.0 + within_call

            self.assertFalse(display._departures_calling_moving(
                screen, phase_for_calling_elapsed(travel + 0.5), 12, 8
            ))
            self.assertTrue(display._departures_calling_moving(
                screen, phase_for_calling_elapsed(
                    travel + led_display.CALLING_MARQUEE_PAUSE_SECONDS + 0.1
                ), 12, 8
            ))

    def test_rail_cache_ignores_nonvisual_weather_metadata(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["weather"] = {
                "temperature_c": 17,
                "icon": "clear_day",
                "stale": False,
                "fetched_at": "2026-10-04T10:00:00Z",
            }
            display.show(screen, clock_time="19:40", phase=0)
            screen["weather"]["fetched_at"] = "2026-10-04T10:00:10Z"

            self.assertTrue(display._rail_cache_matches(screen))

    def test_departures_scene_attaches_clock_and_weather_overlay(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["weather"] = {"temperature_c": 17, "icon": "clear_day"}
            display.show(screen, clock_time="19:40", phase=0)
            self.assertIsNotNone(display._rail_clock_group)
            self.assertIsNotNone(display._rail_weather_group)
            self.assertIn(display._rail_clock_group, display._rail_group)
            self.assertIn(display._rail_weather_group, display._rail_group)

    def test_departures_phase_switch_reuses_prebuilt_layouts(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 8

            display.show(screen, clock_time="19:40", phase=0)
            summary_group = display._rail_group
            summary_labels = display._rail_calling_labels

            display.show(screen, clock_time="19:40", phase=8)
            calling_group = display._rail_group
            calling_labels = display._rail_calling_labels
            self.assertIsNot(summary_group, calling_group)
            self.assertTrue(calling_labels)

            display.show(screen, clock_time="19:40", phase=20)
            self.assertIs(display._rail_group, summary_group)
            self.assertIs(display._rail_calling_labels, summary_labels)
            display.show(screen, clock_time="19:40", phase=28)
            self.assertIs(display._rail_group, calling_group)
            self.assertIs(display._rail_calling_labels, calling_labels)

    def test_calling_layout_has_one_marquee_between_trains_one_and_two(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            display.show(screen, clock_time="19:40", phase=10.0)

            rows = led_display.rail_rows(screen["services"], 10.0)
            self.assertEqual(
                [kind for kind, _ in rows],
                ["service", "calling", "service", "service"],
            )
            self.assertIs(rows[0][1], screen["services"][0])
            self.assertIs(rows[1][1], screen["services"][0])
            self.assertIs(rows[2][1], screen["services"][1])
            self.assertIs(rows[3][1], screen["services"][2])
            self.assertEqual(len(display._rail_calling_labels), 1)
            self.assertEqual(
                display._rail_calling_labels[0]["text"],
                led_display.calling_text(screen["services"][0]),
            )
            visible_labels = [child.text for row in display._rail_departure_rows
                              for child in row if hasattr(child, "text")]
            self.assertIn("2nd", visible_labels)
            self.assertIn("3rd", visible_labels)

    def test_moving_train_viewport_preserves_fixed_rows_and_full_lower_glyphs(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 0
            screen["calling_seconds"] = 120
            screen["weather"] = None
            # More than two upcoming services activates the row slide.
            screen["services"].append(copy.deepcopy(screen["services"][-1]))
            for phase in (0, 2.2, 2.4):
                with self.subTest(phase=phase):
                    display.show(screen, clock_time="19:40", phase=phase)
                    root = display._rail_group
                    mask = next(child for child in root
                                if isinstance(child, FakeTileGrid)
                                and child.bitmap.width == led_display.DISPLAY_WIDTH
                                and child.bitmap.height > 8)
                    mask_index = next(i for i, child in enumerate(root) if child is mask)
                    self.assertEqual(mask.y, 0)
                    # The first lower row's seven-pixel glyph spans y=17..23.
                    self.assertEqual(mask.y + mask.bitmap.height, 17)
                    for row in display._rail_departure_rows:
                        self.assertLess(next(i for i, child in enumerate(root)
                                             if child is row), mask_index)
                    fixed = root[mask_index + 1]
                    self.assertIn("1st", [child.text for child in fixed
                                          if isinstance(child, FakeLabel)])
                    calling_prefix = display._rail_calling_labels[0]["prefix"]
                    self.assertTrue(any(isinstance(child, FakeGroup)
                                        and any(item is calling_prefix for item in child)
                                        for child in fixed))

    def test_departure_scroll_updates_only_active_rows_without_changing_layout(self):
        with patch.dict(sys.modules, fake_modules()), patch.object(
            led_display, "MATRIX_RAIL_ROWS_SCROLL", True
        ):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 0
            screen["calling_seconds"] = 30
            screen["weather"] = None
            screen["services"].extend(
                copy.deepcopy(screen["services"][-1]) for _ in range(4)
            )
            row_step = led_display.RAIL_ROW_Y[3] - led_display.RAIL_ROW_Y[2]
            hidden_y = led_display.RAIL_ROW_Y[-1] + 8
            phases = (0, 2.1, 2.9, 3.0, 5.9, 6.1, 9.3, 12.8, 13.1, 13.7, 14.0)

            for phase in phases:
                with self.subTest(phase=phase):
                    display.show(screen, clock_time="19:40", phase=phase)
                    start, progress, reset_progress = led_display.departure_scroll_state(
                        led_display.rail_marquee_elapsed(phase, 0, 30),
                        max(0, len(screen["services"]) - 1),
                        screen.get("upcoming_train_pause_seconds", 2),
                        visible_rows=2,
                    )
                    expected = []
                    for index in range(len(display._rail_departure_rows)):
                        if reset_progress is None:
                            row_y = hidden_y + index * row_step
                        elif reset_progress > 0:
                            if index < 2:
                                row_y = (
                                    led_display.RAIL_ROW_Y[2]
                                    + 2 * row_step
                                    - int(reset_progress * 2 * row_step)
                                    + index * row_step
                                )
                            else:
                                row_y = hidden_y + index * row_step
                        elif start <= index <= start + 2:
                            row_y = (
                                led_display.RAIL_ROW_Y[2]
                                + (index - start) * row_step
                                - int(progress * row_step)
                            )
                        else:
                            row_y = hidden_y + index * row_step
                        expected.append(row_y)
                    self.assertEqual(
                        [row.y for row in display._rail_departure_rows], expected
                    )

    def test_departures_animation_activity_tracks_only_first_train_calling_row(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["weather"] = None
            long_stops = [
                {"station": "Long station name {}".format(index), "time": "20:{:02d}".format(index)}
                for index in range(10)
            ]
            screen["services"][1]["stops"] = long_stops
            screen["services"][2]["stops"] = long_stops
            # Use the production-style no-summary layout with enough calling
            # time for the short first-train text to settle. Long stop lists on
            # later trains must not keep the first-train marquee active.
            screen["summary_seconds"] = 0
            screen["calling_seconds"] = 30

            short_text = led_display.calling_text(screen["services"][0])
            short_station_text = short_text[len(led_display.CALLING_LABEL):]
            short_speed, _ = led_display._station_scroll_settings(screen)
            short_travel = (
                led_display.DISPLAY_WIDTH
                - len(led_display.CALLING_LABEL) * led_display.WEATHER_FONT_WIDTH
                + len(short_station_text) * led_display.WEATHER_FONT_WIDTH
            ) / short_speed
            quiet_phase = short_travel + 0.5
            self.assertFalse(display.animation_active(screen, quiet_phase))
            screen["services"][0]["stops"] = long_stops
            self.assertTrue(display.animation_active(screen, quiet_phase))

    def test_departures_cache_reuses_scenes_for_equal_new_api_payload(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 8
            display.show(screen, clock_time="19:40", phase=0)
            scenes = display._rail_scenes
            calling_group = scenes["calling"]["group"]

            refreshed_screen = copy.deepcopy(screen)
            self.assertIsNot(refreshed_screen["services"], screen["services"])
            self.assertEqual(refreshed_screen["services"], screen["services"])
            display.show(refreshed_screen, clock_time="19:40", phase=8)

            self.assertIs(display._rail_scenes, scenes)
            self.assertIs(display._rail_group, calling_group)

    def test_todoist_cache_reuses_scene_for_equal_new_api_payload(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)
            date = "2026-09-20"
            display.show(screen, clock_time="19:40", clock_date=date, phase=0)
            scene = display._todoist_group
            rows = [row[0] for row in display._todoist_rows]

            refreshed_screen = copy.deepcopy(screen)
            self.assertIsNot(refreshed_screen["events"], screen["events"])
            self.assertEqual(refreshed_screen["events"], screen["events"])
            display.show(refreshed_screen, clock_time="19:40", clock_date=date, phase=0.1)

            self.assertIs(display._todoist_group, scene)
            self.assertEqual([row[0] for row in display._todoist_rows], rows)

    def test_board_local_calling_override_bypasses_admin_speed_minimum(self):
        with patch.object(led_display, "CALLING_SCROLL_SPEED_OVERRIDE", 8):
            speed, _ = led_display._station_scroll_settings({"station_scroll_speed": 40})
        self.assertEqual(speed, 8.0)

    def test_prepared_departures_segments_match_legacy_text_and_colours(self):
        with patch.dict(sys.modules, fake_modules()):
            legacy_screen = departures_screen(long_calling=True)
            prepared_screen = copy.deepcopy(legacy_screen)
            prepared_screen["rail_presentation"] = prepare_rail_presentation(
                prepared_screen["services"], 20, 2, 8
            )

            legacy_display = led_display.MatrixDisplay()
            legacy_display.show(legacy_screen, clock_time="19:40", phase=1.0)
            legacy_labels = legacy_display._rail_calling_labels[0]
            legacy_segments = tuple(
                (label.text, label.color) for label in legacy_labels["first"]
            )

            prepared_display = led_display.MatrixDisplay()
            prepared_display.show(prepared_screen, clock_time="19:40", phase=1.0)
            prepared_labels = prepared_display._rail_calling_labels[0]
            prepared_segments = tuple(
                (label.text, label.color) for label in prepared_labels["first"]
            )

            self.assertEqual(prepared_segments, legacy_segments)
            self.assertEqual(
                prepared_labels["station_width"],
                prepared_screen["rail_presentation"]["calling_station_width_px"],
            )

    def test_departures_marquee_moves_visible_segments_with_stable_text(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen(long_calling=True)

            display.show(screen, clock_time="19:40", phase=10.0)
            labels = display._rail_calling_labels[0]
            label_text = tuple(label.text for label in labels["first"])
            first_x = labels["first"].x

            display.show(screen, clock_time="19:40", phase=10.125)
            self.assertNotEqual(labels["first"].x, first_x)
            self.assertEqual(tuple(label.text for label in labels["first"]), label_text)

            for frame in range(2, 17):
                display.show(
                    screen,
                    clock_time="19:40",
                    phase=10.0 + frame / MATRIX_REFRESH_FPS,
                )

            final_text = tuple(label.text for label in labels["first"])
            self.assertEqual(final_text, label_text)
            self.assertTrue(all(len(label.text) <= 24 for label in labels["first"]))

    def test_todoist_long_titles_use_fixed_chunks_while_the_group_moves(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(1)
            screen["events"][0]["title"] = "A" * 140

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            _, title_group, _, _ = display._todoist_rows[0]
            self.assertGreater(len(title_group), 1)
            self.assertTrue(all(len(label.text) <= 24 for label in title_group))
            labels = tuple(label.text for label in title_group)
            initial_x = title_group.x

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=1.0 / MATRIX_REFRESH_FPS)
            self.assertLess(title_group.x, initial_x)
            self.assertEqual(tuple(label.text for label in title_group), labels)

    def test_boundary_sleep_uses_earliest_header_event(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = departures_screen()
            screen["summary_seconds"] = 8
            display.show(screen, clock_time="19:40", phase=0)

            sleep_seconds = display.animation_sleep_seconds(screen, 0.5)
            self.assertEqual(sleep_seconds, 7.5)
            self.assertEqual(display.animation_cadence(screen, 4.0), 0)

            todoist = todoist_screen(6)
            todoist["weather"] = {"temperature_c": 17, "icon": "clear_day"}
            display.show(todoist, clock_time="19:40", clock_date="2026-09-20", phase=0)
            sleep_seconds = display.animation_sleep_seconds(todoist, 0.5)
            self.assertEqual(sleep_seconds, 18.25)
            self.assertEqual(display.animation_cadence(todoist, 4.0), TODOIST_MARQUEE_FPS)

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
            display.note_fetch_on_animation_capable_screen()
            display.note_cadence_switch()

            with patch.object(display.display, "refresh", return_value=True):
                with patch.object(led_display, "ticks_ms", side_effect=[10000, 10250, 10250]):
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
            self.assertEqual(display._stats_fetch_on_animation_capable_screen, 1)
            self.assertEqual(display._stats_cadence_switches, 1)

    def test_slow_departures_refresh_is_reported_without_global_telemetry(self):
        with patch.object(led_display, "MATRIX_TELEMETRY_ENABLED", False):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                with patch.object(display.display, "refresh", return_value=True):
                    with patch.object(led_display, "ticks_ms", return_value=1000):
                        with patch.object(led_display, "elapsed_seconds", return_value=0.25):
                            with patch("builtins.print") as output:
                                self.assertTrue(display._refresh("departures_calling"))
                output.assert_called_once()
                self.assertIn("RAIL REFRESH SLOW", output.call_args.args[0])
                self.assertIn("0.250s", output.call_args.args[0])
                self.assertEqual(display._last_rail_refresh_seconds, 0.25)

    def test_fast_departures_refresh_does_not_emit_diagnostic(self):
        with patch.object(led_display, "MATRIX_TELEMETRY_ENABLED", False):
            with patch.dict(sys.modules, fake_modules()):
                display = led_display.MatrixDisplay()
                with patch.object(display.display, "refresh", return_value=True):
                    with patch.object(led_display, "ticks_ms", return_value=1000):
                        with patch.object(led_display, "elapsed_seconds", return_value=0.125):
                            with patch("builtins.print") as output:
                                self.assertTrue(display._refresh("departures_calling"))
                output.assert_not_called()
                self.assertEqual(display._last_rail_refresh_seconds, 0.125)

    def test_animation_class_telemetry_attributes_changed_and_unchanged_ticks(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            updates = (
                ("todoist", "todoist_marquee", True),
                ("todoist", "todoist_page_slide", False),
                ("todoist", "header_slide", True),
                ("rail", "departures_calling", True),
            )
            for scene, animation_class, changed in updates:
                display._record_animation_update(scene, changed, 0.01, animation_class)

            for animation_class in (
                "todoist_marquee",
                "todoist_page_slide",
                "header_slide",
                "departures_calling",
            ):
                self.assertEqual(
                    display._stats_animation_classes[animation_class]["ticks"],
                    1,
                )
            self.assertEqual(display._stats_animation_classes["todoist_marquee"]["changed"], 1)
            self.assertEqual(display._stats_animation_classes["todoist_page_slide"]["changed"], 0)
            self.assertEqual(display._stats_animation_classes["header_slide"]["changed"], 1)
            self.assertEqual(display._stats_animation_classes["departures_calling"]["changed"], 1)

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

    def test_rail_auto_refresh_override_is_limited_to_rail_screen(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "immediate"):
            with patch.object(led_display, "MATRIX_RAIL_AUTO_REFRESH_EXPERIMENT", True):
                with patch.dict(sys.modules, fake_modules()):
                    display = led_display.MatrixDisplay()
                    display.show(departures_screen(), clock_time="19:40", phase=8.1)

                    self.assertTrue(display.display.auto_refresh)
                    self.assertEqual(display.display.refresh_targets, [])

                    display.show(todoist_screen(3), clock_time="19:40", phase=0)

                    self.assertFalse(display.display.auto_refresh)
                    self.assertTrue(display.display.refresh_targets)

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

    def test_telemetry_disabled_keeps_animation_updates_without_counting(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "auto_refresh"):
            with patch.object(led_display, "MATRIX_TELEMETRY_ENABLED", False):
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

                    self.assertEqual(display._todoist_rows[0][1].x, first_x - 1)
                    self.assertEqual(display._stats_animation_ticks, 0)
                    self.assertEqual(display._stats_changes, 0)
                    self.assertEqual(display.display.refresh_targets, [])

    def test_invalid_presentation_mode_is_rejected(self):
        with patch.object(led_display, "MATRIX_PRESENTATION_MODE", "unknown"):
            with patch.dict(sys.modules, fake_modules()):
                with self.assertRaises(ValueError):
                    led_display.MatrixDisplay()


if __name__ == "__main__":
    unittest.main()
