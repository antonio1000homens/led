"""Contracts for the four child-friendly LED timer themes."""
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))

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

    def test_running_state_has_no_scenery_or_completion_words(self):
        display = (ROOT / "hardware/matrixportal/firmware/display.py").read_text()
        render = display[display.index("    def _show_alexa_timer("):
                         display.index("    def _todoist_cache_matches(")]
        self.assertIn("if complete:", render)
        self.assertIn("background_index(theme, x, y)", render)
        self.assertNotIn('"YUM!"', render)
        self.assertNotIn('"WIN!"', render)
        self.assertNotIn('"LANDED!"', render)

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
