"""Contracts for the four child-friendly LED timer themes."""
import json
import shutil
import subprocess
import sys
import unittest
import types
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))
sys.path.insert(0, str(ROOT / "shared"))

from timer_visuals import (
    TIMER_THEMES, CLOCK_FONT, BACKGROUND_COLORS, SPRITE_ROWS,
    SPRITE_SYMBOLS, SPRITE_COLORS, ACCENT_ROWS, accent_positions,
    background_index, clock_layout, finish_pose, rotate_sprite, theme_for_timer,
)


class TimerVisualTests(unittest.TestCase):
    def test_stable_theme_selection_uses_only_timer_id(self):
        for timer_id in ("alexa-1", "timer/3", "morning", "a-longer-test-id"):
            self.assertEqual(theme_for_timer(timer_id), theme_for_timer(timer_id))
            self.assertIn(theme_for_timer(timer_id), TIMER_THEMES)
        self.assertEqual({theme_for_timer("child-{}".format(i)) for i in range(40)},
                         set(TIMER_THEMES))

    def test_clock_uses_compact_font_and_rightmost_pixel(self):
        for label in ("00:00", "59:59", "1:00:00", "12:34:56"):
            x, y, scale, width = clock_layout(label)
            self.assertEqual(x + width, 255)
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x, 200)
            self.assertLessEqual(y + 7 * scale, 32)
            self.assertTrue(all(c in CLOCK_FONT for c in label))
        self.assertEqual(clock_layout("00:00"), (195, 5, 3, 60))

    def test_finishing_characters_stop_moving_after_1_point_5_seconds(self):
        for theme in TIMER_THEMES:
            self.assertEqual(finish_pose(theme, 1.5), finish_pose(theme, 5))
        self.assertEqual(finish_pose("caterpillar", 1.5), (0, 0, 0))
        self.assertLess(finish_pose("caterpillar", .35)[2], 0)
        self.assertEqual(finish_pose("race", 1.5), (0, 0, 0))
        self.assertEqual(finish_pose("rocket", 1.5), (3, 0, 7))
        self.assertEqual(finish_pose("stars", 1.5), (0, 0, 0))
        self.assertNotEqual(finish_pose("race", .5), finish_pose("race", 1.5))

    def test_all_background_palettes_and_sprites_fit_matrix(self):
        for theme in TIMER_THEMES:
            self.assertEqual(len(BACKGROUND_COLORS[theme]), 8)
            self.assertTrue(ACCENT_ROWS[theme])
            for y in range(32):
                for x in range(194):
                    self.assertIn(background_index(theme, x, y), range(8))
            self.assertNotEqual(accent_positions(theme, 0),
                                accent_positions(theme, 1))
            if theme in SPRITE_ROWS:
                rows = SPRITE_ROWS[theme]
                self.assertLessEqual(max(len(row) for row in rows), 24)
                self.assertLessEqual(len(rows), 16)
                for row in rows:
                    self.assertTrue(set(row) <= set(SPRITE_SYMBOLS[theme]))
                self.assertTrue(all(0 <= idx < len(SPRITE_COLORS[theme])
                                    for idx in SPRITE_SYMBOLS[theme].values()))
                for turn in range(4):
                    rotated = rotate_sprite(rows, turn)
                    self.assertEqual(len(rotated), len(rows[0]) if turn % 2 else len(rows))

    def test_rotate_sprite_pads_ragged_rows_without_string_ljust(self):
        self.assertEqual(rotate_sprite(("AB", "C"), 0), ("AB", "C."))
        self.assertEqual(rotate_sprite(("AB", "C"), 1), ("CA", ".B"))

    def test_completion_sprite_rotations_use_positive_indexing(self):
        rows = ("ABC", "DEF")
        self.assertEqual(rotate_sprite(rows, 0), ("ABC", "DEF"))
        self.assertEqual(rotate_sprite(rows, 1), ("DA", "EB", "FC"))
        self.assertEqual(rotate_sprite(rows, 2), ("FED", "CBA"))
        self.assertEqual(rotate_sprite(rows, 3), ("CF", "BE", "AD"))
        source = (ROOT / "hardware/matrixportal/firmware/timer_visuals.py").read_text()
        self.assertNotIn("[::-1]", source)

    def test_running_state_has_no_scenery_or_completion_words(self):
        display = (ROOT / "hardware/matrixportal/firmware/display.py").read_text()
        render = display[display.index("    def _show_alexa_timer("):
                         display.index("    def _todoist_cache_matches(")]
        self.assertIn("if complete:", render)
        self.assertIn("background_index(theme, x, y)", render)
        self.assertNotIn('"YUM!"', render)
        self.assertNotIn('"WIN!"', render)
        self.assertNotIn('"LANDED!"', render)

    def test_matrix_scene_is_reused_and_background_exists_only_when_complete(self):
        class Group(list):
            pass

        class Bitmap:
            def __init__(self, width, height, count):
                self.width, self.height, self.count = width, height, count
                self.data = {}

            def __setitem__(self, pos, color):
                x, y = pos
                if not (0 <= x < self.width and 0 <= y < self.height):
                    raise AssertionError("bitmap write out of bounds: {} in {}x{}".format(
                        pos, self.width, self.height))
                self.data[pos] = color

            def fill(self, color):
                self.data.clear()

        class Palette(list):
            def __init__(self, count):
                super().__init__([0] * count)

            def make_transparent(self, index):
                pass

        class Grid:
            def __init__(self, bitmap, pixel_shader=None, x=0, y=0):
                self.bitmap, self.pixel_shader = bitmap, pixel_shader
                self.x, self.y = x, y

        fake_displayio = types.SimpleNamespace(
            Group=Group, Bitmap=Bitmap, Palette=Palette, TileGrid=Grid)
        sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
        with patch.dict(sys.modules, {"displayio": fake_displayio}):
            import display
            for theme in TIMER_THEMES:
                with self.subTest(theme=theme):
                    renderer = display.MatrixDisplay.__new__(display.MatrixDisplay)
                    renderer.display = types.SimpleNamespace(root_group=None)
                    presentations = []

                    def present_when_positioned(group):
                        # A scene must not become visible while the active
                        # sprite is still off-screen and markers overlap at 0,0.
                        self.assertTrue(any(tile.x != -100
                                            for tile in renderer._timer_actor_frames))
                        self.assertFalse(any(tile.x == 0 and tile.y == 0
                                             for tile in renderer._timer_markers))
                        presentations.append(group)
                        renderer.display.root_group = group

                    renderer._present = present_when_positioned
                    renderer._refresh = lambda *_args: True
                    renderer.font = object()
                    renderer.label_type = lambda *_args, **kwargs: types.SimpleNamespace(**kwargs)
                    screen = {"kind": "alexa_timer", "timer_id": theme,
                              "theme": theme, "state": "running",
                              "remaining_seconds": 120, "progress": 0.0}
                    renderer._show_alexa_timer(screen, 0)
                    self.assertEqual(len(presentations), 1)
                    running_group = renderer.display.root_group
                    self.assertFalse(any(isinstance(item, Grid) and
                                         (item.bitmap.width, item.bitmap.height) == (194, 32)
                                         for item in running_group))
                    screen["remaining_seconds"], screen["progress"] = 60, .5
                    renderer._show_alexa_timer(screen, 1)
                    self.assertEqual(len(presentations), 1)
                    self.assertIs(renderer.display.root_group, running_group)

                    screen["state"] = "paused"
                    renderer._show_alexa_timer(screen, 1)
                    self.assertEqual(len(presentations), 2)
                    paused_group = renderer.display.root_group
                    self.assertFalse(any(isinstance(item, Grid) and
                                         (item.bitmap.width, item.bitmap.height) == (194, 32)
                                         for item in paused_group))

                    screen.update(state="complete", remaining_seconds=0,
                                  progress=1, completion_elapsed_seconds=0)
                    renderer._show_alexa_timer(screen, 0)
                    self.assertEqual(len(presentations), 3)
                    complete_group = renderer.display.root_group
                    backgrounds = [item for item in complete_group
                                   if isinstance(item, Grid)
                                   and (item.bitmap.width, item.bitmap.height) == (194, 32)]
                    self.assertEqual(len(backgrounds), 1)
                    accent_positions_at_start = [(tile.x, tile.y)
                                                 for tile in renderer._timer_accents]
                    screen["completion_elapsed_seconds"] = 1.0
                    renderer._show_alexa_timer(screen, 1)
                    self.assertIs(renderer.display.root_group, complete_group)
                    self.assertIs(renderer.display.root_group[0], backgrounds[0])
                    self.assertNotEqual(accent_positions_at_start,
                                        [(tile.x, tile.y) for tile in renderer._timer_accents])
                    screen["completion_elapsed_seconds"] = 4.0
                    renderer._show_alexa_timer(screen, 4)
                    self.assertIs(renderer.display.root_group, complete_group)
                    self.assertEqual(len(presentations), 3)

                    # 10:00:00 -> 9:59:59 shortens the clock by one glyph
                    # without changing scale; the bitmap must be rebuilt.
                    screen.update(state="running", remaining_seconds=36000,
                                  progress=0)
                    renderer._show_alexa_timer(screen, 0)
                    ten_hours_group = renderer.display.root_group
                    self.assertEqual(len(presentations), 4)
                    self.assertEqual(renderer._timer_clock_bitmap.width, 64)
                    self.assertEqual(renderer._timer_clock_grid.x, 191)
                    screen["remaining_seconds"] = 35999
                    renderer._show_alexa_timer(screen, 0)
                    nine_hours_group = renderer.display.root_group
                    self.assertIsNot(ten_hours_group, nine_hours_group)
                    self.assertEqual(len(presentations), 5)
                    self.assertEqual(renderer._timer_clock_bitmap.width, 56)
                    self.assertEqual(renderer._timer_clock_grid.x, 199)
                    # Same-length changes retain the new group and bitmap.
                    screen["remaining_seconds"] = 35998
                    renderer._show_alexa_timer(screen, 0)
                    self.assertIs(renderer.display.root_group, nine_hours_group)
                    self.assertEqual(len(presentations), 5)
                    # An edited timer can gain an hour digit again.
                    screen["remaining_seconds"] = 36000
                    renderer._show_alexa_timer(screen, 0)
                    self.assertIsNot(renderer.display.root_group, nine_hours_group)
                    self.assertEqual(len(presentations), 6)
                    self.assertEqual(renderer._timer_clock_bitmap.width, 64)
                    self.assertEqual(renderer._timer_clock_grid.x, 191)

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for simulator parity")
    def test_simulator_and_firmware_geometry_agree(self):
        html = (ROOT / "simulator/index.html").read_text()
        helpers = html[html.index("    const ALEXA_TIMER_THEMES ="):
                       html.index("    function drawCalendarDue(")]
        harness = helpers + """
process.stdout.write(JSON.stringify({
  theme: alexaTimerTheme('child-7'),
  clock: alexaTimerClockLayout('00:00'),
  rocket: alexaTimerFinishPose('rocket',1.5),
  race: alexaTimerFinishPose('race',1.5),
  gardenIndex: alexaTimerBackgroundIndex('caterpillar',8,28),
  accents: alexaTimerAccentPositions('rocket',1)
}));
"""
        result = subprocess.run(["node", "-e", harness], capture_output=True,
                                text=True, check=True)
        values = json.loads(result.stdout)
        self.assertEqual(values["theme"], theme_for_timer("child-7"))
        x, y, scale, _ = clock_layout("00:00")
        self.assertEqual(values["clock"], {"x": x, "y": y, "scale": scale})
        self.assertEqual(values["rocket"],
                         {"rotation": 3, "dy": finish_pose("rocket", 1.5)[2]})
        self.assertEqual(values["race"],
                         {"rotation": 0, "dy": finish_pose("race", 1.5)[2]})
        self.assertEqual(values["gardenIndex"], background_index("caterpillar",8,28))
        self.assertEqual(values["accents"], [list(pt) for pt in accent_positions("rocket",1)])


if __name__ == "__main__":
    unittest.main()
