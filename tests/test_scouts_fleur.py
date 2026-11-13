"""Scouts outline sprite and low-allocation gradient/slide regression tests."""
import re
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
import display as led_display

ROOT = Path(__file__).resolve().parents[1]


class FakeGroup(list):
    def __init__(self, x=0, y=0):
        super().__init__()
        self.x, self.y = x, y


class FakeBitmap:
    def __init__(self, width, height, colors):
        self.width, self.height, self.colors = width, height, colors
        self.pixels = {}

    def __setitem__(self, coordinates, color):
        self.pixels[coordinates] = color


class FakePalette(list):
    def __init__(self, colors):
        super().__init__([0] * colors)
        self.transparent = None

    def make_transparent(self, index):
        self.transparent = index


class FakeTileGrid:
    def __init__(self, bitmap, pixel_shader):
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader


class ScoutsFleurTests(unittest.TestCase):
    def test_uploaded_scouts_outline_keeps_five_distinct_shapes(self):
        rows = led_display.SCOUTS_FLEUR_ROWS
        self.assertEqual(len(rows), 26)
        self.assertTrue(all(len(row) == 40 for row in rows))
        self.assertEqual(set("".join(rows)), {".", "X"})
        self.assertEqual(rows[0][19:21], "XX")  # central point
        self.assertTrue(rows[4][15:17] == "XX")  # hollow centre
        self.assertEqual(rows[8][7:12], "XXXXX")  # left petal
        self.assertEqual(rows[8][28:33], "XXXXX")  # right petal
        self.assertEqual(rows[16][11:29], "X" * 18)  # horizontal bar
        self.assertEqual(rows[25][19:21], "XX")  # lower loop
        self.assertLess(sum(row.count("X") for row in rows), 250)

    def test_firmware_and_simulator_use_exact_mask_and_colour_wheel(self):
        html = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        rows_match = re.search(r"const SCOUTS_FLEUR_ROWS = \[(.*?)\];", html, flags=re.S)
        self.assertIsNotNone(rows_match)
        js_rows = tuple(re.findall(r"'([.X]{40})'", rows_match.group(1)))
        self.assertEqual(js_rows, led_display.SCOUTS_FLEUR_ROWS)
        wheel_match = re.search(r"const SCOUTS_FLEUR_GRADIENT_WHEEL = \[(.*?)\];", html, flags=re.S)
        self.assertIsNotNone(wheel_match)
        js_wheel = tuple(int(color, 16) for color in re.findall(
            r"'#([0-9a-f]{6})'", wheel_match.group(1)
        ))
        self.assertEqual(js_wheel, led_display.SCOUTS_FLEUR_GRADIENT_WHEEL)
        self.assertEqual(len(js_wheel), 48)
        self.assertEqual(len(led_display.SCOUTS_FLEUR_PALETTE), 11)
        for band in range(led_display.SCOUTS_FLEUR_GRADIENT_BANDS):
            self.assertEqual(
                led_display.SCOUTS_FLEUR_PALETTE[band + 1],
                js_wheel[(band * led_display.SCOUTS_FLEUR_GRADIENT_SPACING) % 48],
            )
        self.assertIn("drawScoutsFleur(x, 2, elapsed);", html)
        self.assertNotIn("drawScoutsTent", html)
        self.assertIn("const SCOUTS_INTRO_SLIDE_SECONDS = 4.8", html)
        self.assertIn("const SCOUTS_FLEUR_GRADIENT_STEP_SECONDS = 0.20", html)

    def test_slow_right_to_left_slide_palette_cycles_during_hold_without_rebuild(self):
        fake_displayio = types.SimpleNamespace(
            Group=FakeGroup, Bitmap=FakeBitmap, Palette=FakePalette,
            TileGrid=FakeTileGrid,
        )
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.display = types.SimpleNamespace(root_group=None)
        display._scouts_intro_group = None
        display._scouts_intro_text = None
        display._label = mock.Mock()
        display._attach_brightness_overlay = mock.Mock()
        display._record_animation_update = mock.Mock()
        display._refresh = mock.Mock()
        screen = {"kind": "scouts_intro", "intro_text": "Be prepared..."}

        with mock.patch.dict(sys.modules, {"displayio": fake_displayio}):
            display._show_scouts_intro(screen, 0)
            root = display.display.root_group
            motion = display._scouts_intro_motion
            sprite = motion[0]
            palette = sprite.pixel_shader
            self.assertIs(root[0], motion)
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH)
            self.assertEqual(motion.y, 2)
            self.assertEqual((sprite.bitmap.width, sprite.bitmap.height), (40, 26))
            self.assertEqual(palette.transparent, 0)
            self.assertEqual(len(sprite.bitmap.pixels),
                             sum(row.count("X") for row in led_display.SCOUTS_FLEUR_ROWS))
            self.assertEqual(sprite.bitmap.pixels[(19, 0)], 1 + 19 // 4)
            self.assertEqual(palette[1], led_display.SCOUTS_FLEUR_GRADIENT_WHEEL[0])

            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS / 2)
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH // 2)
            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS)
            self.assertEqual(motion.x, 0)
            before = list(palette)
            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS + 0.4)
            self.assertEqual(motion.x, 0)
            self.assertNotEqual(list(palette), before)
            self.assertIs(display.display.root_group, root)
            self.assertIs(motion[0], sprite)
            self.assertIs(display._scouts_intro_palette, palette)
            self.assertEqual(display._label.call_count, 1)
            calls = display._refresh.call_count
            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS + 0.4)
            self.assertEqual(display._refresh.call_count, calls)
            self.assertAlmostEqual(led_display.SCOUTS_INTRO_DURATION_SECONDS, 7.2)
            self.assertEqual(led_display.SCOUTS_FLEUR_GRADIENT_STEP_SECONDS, 0.20)


if __name__ == "__main__":
    unittest.main()
