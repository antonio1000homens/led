import sys
import types
import unittest
from unittest.mock import patch


sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

import display as led_display
from matrix_config import MATRIX_REFRESH_FPS, TODOIST_MARQUEE_SPEED


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


class MatrixTodoistPerformanceTests(unittest.TestCase):
    def setUp(self):
        led_display.board.MTX_ADDRESS = (0, 1, 2, 3)
        led_display.board.MTX_COMMON = {}

    def test_marquee_speed_matches_refresh_for_one_pixel_per_frame(self):
        self.assertEqual(MATRIX_REFRESH_FPS, 7)
        self.assertEqual(TODOIST_MARQUEE_SPEED, 7.0)

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
            self.assertEqual(title_group.x, first_x - 1)
            self.assertEqual(display.display.refresh_targets[-1], MATRIX_REFRESH_FPS)

    def test_page_slide_reuses_row_groups_and_changes_only_positions(self):
        with patch.dict(sys.modules, fake_modules()):
            display = led_display.MatrixDisplay()
            screen = todoist_screen(6)

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=0)
            row_groups = [row[0] for row in display._todoist_rows]
            assignments = display.display.root_assignments
            self.assertEqual([row.y for row in row_groups[:4]], [11, 19, 27, 64])

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=5.2)
            self.assertEqual(display.display.root_assignments, assignments)
            self.assertEqual([row[0] for row in display._todoist_rows], row_groups)
            self.assertEqual([row.y for row in row_groups[:4]], [-1, 7, 15, 23])

            display.show(screen, clock_time="19:40", clock_date="2026-09-20", phase=5.5)
            self.assertEqual([row.y for row in row_groups[3:6]], [11, 19, 27])


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
            self.assertEqual([row.y for row in row_groups[:4]], [11, 19, 27, 64])

            display.show(
                screen,
                clock_time="19:40",
                clock_date="2026-09-20",
                phase=transition_at + 0.2,
            )
            self.assertEqual([row.y for row in row_groups[:4]], [-1, 7, 15, 23])

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
            self.assertEqual(second_title_group.x, led_display.AGENDA_TITLE_X - 1)


if __name__ == "__main__":
    unittest.main()
