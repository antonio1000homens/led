import random
import sys
import types
import unittest
from pathlib import Path
import shutil
import subprocess

from christmas_tracker import (
    CHRISTMAS_INTRO_SECONDS, CHRISTMAS_SCREEN_SECONDS, SLEIGH_END_X, SLEIGH_SLIDE_SECONDS,
    SLEIGH_START_X, days_until_christmas, sleigh_x, snow_active,
    with_christmas_tracker,
)
from screen_client import ClockState, ScreenRotation


class FakeGroup(list):
    def __init__(self, *args, x=0, y=0):
        super().__init__(*args)
        self.x, self.y = x, y


class FakeBitmap:
    def __init__(self, width, height, color_count):
        self.width, self.height, self.color_count = width, height, color_count
        self.pixels = {}

    def __setitem__(self, key, value):
        self.pixels[key] = value


class FakePalette(list):
    def __init__(self, size):
        super().__init__([None] * size)

    def make_transparent(self, index):
        self.transparent = index


class FakeTileGrid:
    def __init__(self, bitmap, pixel_shader, x=0, y=0):
        self.bitmap, self.pixel_shader = bitmap, pixel_shader
        self.x, self.y, self.hidden = x, y, False


class FakeLabel:
    def __init__(self, font, **kwargs):
        self.text = kwargs.get("text")
        self.__dict__.update(kwargs)


class ChristmasTrackerTests(unittest.TestCase):
    def test_countdown_boundaries_and_year_rollover(self):
        self.assertEqual(days_until_christmas("2026-12-24"), 1)
        self.assertEqual(days_until_christmas("2026-12-25"), 0)
        self.assertEqual(days_until_christmas("2026-12-26"), 364)
        self.assertEqual(days_until_christmas("2024-12-26"), 364)
        self.assertEqual(days_until_christmas("2027-01-01"), 358)
        self.assertIsNone(days_until_christmas("2026-02-29"))

    def test_countdown_uses_the_board_london_local_date(self):
        clock = ClockState()
        clock.sync("2026-12-25T00:30:00Z", 100)
        self.assertEqual(clock.date_text(100), "2026-12-25")
        self.assertEqual(days_until_christmas(clock.date_text(100)), 0)

    def test_intro_finishes_before_countdown_screen_snow_starts(self):
        self.assertEqual(sleigh_x(0), SLEIGH_START_X)
        self.assertLess(sleigh_x(1), SLEIGH_START_X)
        self.assertEqual(sleigh_x(SLEIGH_SLIDE_SECONDS), SLEIGH_END_X)
        self.assertTrue(snow_active(0))
        self.assertEqual(CHRISTMAS_INTRO_SECONDS, 8)
        self.assertEqual(CHRISTMAS_SCREEN_SECONDS, 18)

    def test_renderer_keeps_the_full_screen_on_the_animation_scheduler(self):
        sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
        import display

        renderer = display.MatrixDisplay.__new__(display.MatrixDisplay)
        screen = {"kind": "christmas_tracker"}
        self.assertEqual(renderer._animation_class(screen, 0), "christmas_tracker")
        self.assertTrue(renderer.animation_active(screen, 10))
        self.assertGreater(renderer.animation_cadence(screen, 10), 0)

    def test_scene_and_flake_state_are_reused_after_sleigh_transition(self):
        sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
        import display

        fake_displayio = types.SimpleNamespace(
            Group=FakeGroup, Bitmap=FakeBitmap, Palette=FakePalette,
            TileGrid=FakeTileGrid,
        )
        old_module = sys.modules.get("displayio")
        sys.modules["displayio"] = fake_displayio
        try:
            renderer = display.MatrixDisplay.__new__(display.MatrixDisplay)
            renderer.font = object()
            renderer.label_type = FakeLabel
            renderer._christmas_group = None
            renderer._christmas_snow_grid = None
            renderer._christmas_snow_bitmap = None
            renderer._christmas_countdown = None
            renderer._christmas_days = None
            renderer._christmas_flakes = None
            renderer._christmas_snow_visible = True
            renderer._build_christmas_scene({}, "2026-12-24")
            group = renderer._christmas_group
            flakes = renderer._christmas_flakes
            bitmap = renderer._christmas_snow_bitmap
            countdown = renderer._christmas_countdown
            self.assertEqual(countdown.text, "1 DAYS")
            self.assertEqual((countdown.x, countdown.y), (88, 5))
            self.assertEqual(group[3].text, "UNTIL CHRISTMAS")
            self.assertEqual((group[3].x, group[3].y), (88, 21))
            renderer._update_christmas_scene(0, "2026-12-24")
            self.assertFalse(renderer._christmas_snow_grid.hidden)
            first_positions = tuple(flake[2] for flake in flakes)
            renderer._update_christmas_scene(4, "2026-12-24")
            self.assertIs(renderer._christmas_group, group)
            self.assertIs(renderer._christmas_flakes, flakes)
            self.assertIs(renderer._christmas_snow_bitmap, bitmap)
            self.assertNotEqual(tuple(flake[2] for flake in flakes), first_positions)
            renderer._update_christmas_scene(5, "2026-12-25")
            self.assertEqual(countdown.text, "0 DAYS")
        finally:
            if old_module is None:
                del sys.modules["displayio"]
            else:
                sys.modules["displayio"] = old_module

    def test_local_screen_joins_the_rotation_without_becoming_a_gc_window(self):
        screens = with_christmas_tracker([
            {"id": "feed", "kind": "message", "duration_seconds": 3}
        ])
        self.assertEqual(len(screens), 3)
        self.assertEqual(screens[1]["kind"], "christmas_tracker_intro")
        self.assertEqual(screens[1]["words"], "HO HO HO...")
        self.assertEqual(screens[2]["kind"], "christmas_tracker")
        self.assertEqual(screens[1]["source"], "firmware")
        self.assertEqual(len(with_christmas_tracker(screens)), 3)
        rotation = ScreenRotation(rng=random.Random(2))
        rotation.update(screens, 0)
        tracker = [item for item in rotation.screens
                   if item.get("kind") == "christmas_tracker"]
        self.assertEqual(len(tracker), 1)
        self.assertEqual(tracker[0]["id"], "christmas-tracker")
        self.assertEqual(tracker[0]["duration_seconds"], CHRISTMAS_SCREEN_SECONDS)
        self.assertFalse(ScreenRotation.is_maintenance_screen(tracker[0]))
        self.assertEqual(rotation.screens[rotation.index + 1]["kind"], "christmas_tracker_intro")
        self.assertEqual(rotation.screens[rotation.index + 2]["kind"], "christmas_tracker")
        self.assertTrue(rotation.is_paired_transition("christmas-tracker-intro", rotation.screens[rotation.index + 2]))

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for simulator checks")
    def test_simulator_countdown_and_screen_sequence(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "simulator" / "index.html").read_text(encoding="utf-8")
        start = html.index("    function christmasDaysUntil(date)")
        end = html.index("    function splitSl7Due(item)", start)
        functions = html[start:end]
        harness = """
const CHRISTMAS_SCREEN_SECONDS = 18;
const CHRISTMAS_INTRO_SECONDS = 8;
const londonDateFormatter = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/London', year:'numeric', month:'2-digit', day:'2-digit'});
""" + functions + """
const results = [
  christmasDaysUntil(new Date('2026-12-24T23:30:00Z')),
  christmasDaysUntil(new Date('2026-12-25T12:00:00Z')),
  christmasDaysUntil(new Date('2026-12-26T12:00:00Z')),
  withChristmasTracker([{id:'x',kind:'message'}]).filter(x=>x.kind==='christmas_tracker_intro' || x.kind==='christmas_tracker').map(x=>x.kind)
];
process.stdout.write(JSON.stringify(results));
"""
        output = subprocess.check_output(["node", "-e", harness], text=True)
        self.assertEqual(output, '[1,0,364,["christmas_tracker_intro","christmas_tracker"]]')
        self.assertIn("drawChristmasIntro(screen, phase)", html)
        self.assertIn("drawChristmasTracker(screen, phase, wallClock)", html)
        self.assertIn("drawLedTextScaled(`${days} DAYS`, 88 * px, -4 * px, 2)", functions)
        self.assertIn("drawLedText('UNTIL CHRISTMAS', 88 * px, 12 * px)", functions)


if __name__ == "__main__":
    unittest.main()
