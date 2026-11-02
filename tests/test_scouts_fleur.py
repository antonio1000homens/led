"""Pixel-art and animation regression tests for the Scouts intro fleur-de-lis."""
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
    def test_sprite_is_colourful_bounded_and_contains_no_tent(self):
        rows = led_display.SCOUTS_FLEUR_ROWS
        symbols = led_display.SCOUTS_FLEUR_SYMBOLS
        self.assertEqual(len(rows), 26)
        self.assertTrue(all(len(row) == 40 for row in rows))
        self.assertEqual(len(symbols), len(led_display.SCOUTS_FLEUR_PALETTE))
        self.assertEqual(symbols[0], ".")
        self.assertEqual(set("".join(rows)) - set(symbols), set())
        self.assertGreaterEqual(len(set("".join(rows)) - {"."}), 7)

    def test_simulator_uses_identical_palette_pixel_art(self):
        html = (ROOT / "simulator" / "index.html").read_text(encoding="utf-8")
        match = re.search(r"const SCOUTS_FLEUR_ROWS = \\[(.*?)\\];", html, flags=re.S)
        self.assertIsNotNone(match)
        js_rows = tuple(re.findall(r"'([.CcMmGWOLlPH]{40})'", match.group(1)))
        self.assertEqual(js_rows, led_display.SCOUTS_FLEUR_ROWS)
        self.assertIn("drawScoutsFleur(x, 2);", html)
        self.assertNotIn("drawScoutsTent", html)
        self.assertIn("Scouts fleur-de-lis intro", html)

    def test_full_sprite_slides_from_right_and_holds_without_rebuild(self):
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
            self.assertIs(root[0], motion)
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH)
            self.assertEqual(motion.y, 2)
            sprite = motion[0]
            self.assertEqual((sprite.bitmap.width, sprite.bitmap.height), (40, 26))
            self.assertEqual(sprite.pixel_shader.transparent, 0)
            self.assertTrue(set(sprite.bitmap.pixels.values()) - {0})
            self.assertEqual(len(set(sprite.bitmap.pixels.values())), 11)

            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS / 2)
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH // 2)
            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS)
            self.assertEqual(motion.x, 0)
            display._show_scouts_intro(screen, led_display.SCOUTS_INTRO_SLIDE_SECONDS + 1.6)
            self.assertEqual(motion.x, 0)
            self.assertIs(display.display.root_group, root)
            self.assertIs(display._scouts_intro_motion, motion)
            self.assertEqual(display._label.call_count, 1)
            self.assertEqual(display._refresh.call_count, 3)


if __name__ == "__main__":
    unittest.main()
