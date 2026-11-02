"""Regression checks for semantic Alexa timer themes and fixed right-side objects."""
import unittest
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))
from timer_state import TimerState, validate_snapshot
from timer_visuals import finish_pose, clock_layout
from timer_semantic import (
    SEMANTIC_THEMES, CHARACTER_ROWS, DESTINATION_ROWS,
    CHARACTER_COLORS, CHARACTER_SYMBOLS, DESTINATION_COLORS,
    DESTINATION_SYMBOLS, destination_position, semantic_character_position,
    semantic_marker_x, semantic_background_index,
)


class SemanticTimerTests(unittest.TestCase):
    def test_destinations_and_characters_fit_all_clock_widths(self):
        for theme in SEMANTIC_THEMES:
            self.assertEqual(len(CHARACTER_ROWS[theme]), 13)
            self.assertTrue(all(len(row) == 13 for row in CHARACTER_ROWS[theme]))
            for rows, symbols, colors in (
                (CHARACTER_ROWS[theme], CHARACTER_SYMBOLS[theme], CHARACTER_COLORS[theme]),
                (DESTINATION_ROWS[theme], DESTINATION_SYMBOLS[theme], DESTINATION_COLORS[theme]),
            ):
                self.assertTrue(all(set(row) <= set(symbols) for row in rows))
                self.assertLessEqual(max(symbols.values()), len(colors) - 1)
                # The actual board has one bit per RGB channel.
                self.assertTrue(all(channel in (0, 255)
                    for color in colors for channel in
                    ((color >> 16) & 255, (color >> 8) & 255, color & 255)))
            for text in ("00:00", "9:59:59", "10:00:00"):
                clock_x = clock_layout(text)[0]
                dx, dy = destination_position(theme, clock_x)
                dest_rows = DESTINATION_ROWS[theme]
                width, height = len(dest_rows[0]) * 2, len(dest_rows) * 2
                self.assertLessEqual(dx + width, clock_x - 4)
                self.assertGreaterEqual(dy, 0)
                self.assertLessEqual(dy + height, 32)
                end_x = dx - 3
                for progress in (0, .25, .5, .75, 1):
                    x, y = semantic_character_position(theme, clock_x, progress)
                    self.assertLessEqual(x + 26, end_x)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(y + 26, 32)
                self.assertGreater(semantic_marker_x(theme, clock_x, 9), 100)
                self.assertLess(semantic_marker_x(theme, clock_x, 9), dx)
            for y in range(32):
                for x in range(194):
                    self.assertIn(semantic_background_index(theme, x, y), range(8))
            self.assertEqual(finish_pose(theme, 1.5), finish_pose(theme, 5))

    @staticmethod
    def snapshot(timestamp, timers):
        return {"schema_version": 1, "event": "upsert", "source": "homeassistant",
                "device": "living-room-alexa", "published_at": timestamp, "timers": timers}

    def test_pending_to_ready_preserves_deadline_progress_and_completion(self):
        state = TimerState()
        running = {"timer_id": "abc", "state": "running",
                   "ends_at": "2026-11-02T20:05:00Z", "duration_seconds": 300,
                   "label": "Brush your teeth", "theme_status": "pending"}
        # 20:00:00 UTC epoch.
        t0 = 1793650000
        from timer_state import iso_epoch
        t0 = iso_epoch("2026-11-02T20:00:00Z")
        self.assertEqual(state.accept(self.snapshot("2026-11-02T20:00:00Z",
                                                    [running]), t0, 100), (True, "accepted"))
        initial = dict(state.selected(t0, 100))
        self.assertEqual(initial["theme_status"], "pending")
        self.assertIsNone(initial["theme"])
        self.assertEqual(initial["remaining_seconds"], 300)
        self.assertAlmostEqual(initial["progress"], 0)
        self.assertTrue(state.accept(self.snapshot("2026-11-02T20:00:02Z",
                                                  [running]), t0 + 2, 102)[0])
        self.assertEqual(state.selected(t0 + 5, 105)["theme"], "generic")
        self.assertEqual(state.selected(t0 + 5, 105)["theme_status"], "ready")
        updated = dict(running, theme_status="ready", theme="bedtime")
        self.assertTrue(state.accept(self.snapshot("2026-11-02T20:02:30Z",
                                                  [updated]), t0 + 150, 250)[0])
        current = state.selected(t0 + 150, 250)
        self.assertEqual(current["theme"], "bedtime")
        self.assertEqual(current["remaining_seconds"], 150)
        self.assertAlmostEqual(current["progress"], .5)
        finished = state.selected(t0 + 300, 400)
        self.assertEqual(finished["state"], "complete")
        self.assertEqual(finished["theme"], "bedtime")
        self.assertEqual(state.selected(t0 + 301, 401)["theme"], "bedtime")

    def test_invalid_theme_values_are_rejected_without_mutation(self):
        base = {"timer_id": "abc", "state": "paused",
                "remaining_seconds": 20}
        for bad in (
            {"theme": "naughty"},
            {"theme": "generic", "theme_status": "pending"},
            {"theme_status": "ready"},
            {"theme_status": "unknown"},
            {"theme": 12},
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_snapshot(self.snapshot("2026-11-02T20:00:00Z",
                                                [dict(base, **bad)]), "living-room-alexa")
        validate_snapshot(self.snapshot("2026-11-02T20:00:00Z", [base]),
                          "living-room-alexa")


if __name__ == "__main__":
    unittest.main()
