"""Contracts for MatrixPortal 1-bit fallback and 2-bit art palettes."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))

import matrix_config
import weather_sprites
import double_decker_bus
import timer_visuals
import timer_semantic
import recycling_lorries
import football_ball


class MatrixColourPaletteTests(unittest.TestCase):
    def test_default_depth_and_board_local_one_bit_fallback(self):
        self.assertEqual(matrix_config.MATRIX_BIT_DEPTH, 2)
        with patch.dict(sys.modules, {
            "settings_local": types.SimpleNamespace(MATRIX_BIT_DEPTH=1),
        }):
            importlib.reload(matrix_config)
            self.assertEqual(matrix_config.MATRIX_BIT_DEPTH, 1)
        try:
            with patch.dict(sys.modules, {
                "settings_local": types.SimpleNamespace(MATRIX_BIT_DEPTH=3),
            }):
                with self.assertRaisesRegex(ValueError, "must be 1 or 2"):
                    importlib.reload(matrix_config)
        finally:
            sys.modules.pop("settings_local", None)
            importlib.reload(matrix_config)

    def test_legacy_one_bit_palettes_are_preserved(self):
        self.assertEqual(weather_sprites.PALETTE_8["Y"], 0xFFFF00)
        self.assertEqual(double_decker_bus.PALETTE_8["R"], (255, 0, 0))
        self.assertEqual(len(timer_visuals.BACKGROUND_COLORS), 4)
        self.assertIn("bedtime", timer_semantic.SEMANTIC_BACKGROUND_COLORS)
        self.assertIn("paper", recycling_lorries.PALETTES_1BIT)

    def test_enhanced_palettes_use_only_two_bit_channel_levels(self):
        colors = list(weather_sprites.PALETTE_64.values())
        colors.extend(tuple(color) for color in double_decker_bus.PALETTE_64.values())
        colors.extend(color for palette in timer_visuals.BACKGROUND_COLORS_2BIT.values()
                      for color in palette)
        colors.extend(color for palette in recycling_lorries.PALETTES_2BIT.values()
                      for rgb in palette.values() for color in rgb)
        colors.extend(color for palette in timer_semantic.SEMANTIC_BACKGROUND_COLORS_2BIT.values()
                      for color in palette)
        colors.extend(color for palette in timer_semantic.CHARACTER_COLORS_2BIT.values()
                      for color in palette)
        colors.extend(color for palette in timer_semantic.DESTINATION_COLORS_2BIT.values()
                      for color in palette)
        colors.extend(color for color in football_ball.PALETTE_2BIT.values())
        for color in colors:
            if color is None:
                continue
            channels = ((color >> 16) & 255, (color >> 8) & 255, color & 255) \
                if isinstance(color, int) else color
            for channel in channels:
                self.assertIn(channel, (0, 85, 170, 255))

    def test_pixel_art_helpers_can_select_enhanced_palette(self):
        bus_pixels = {}
        bus_x = double_decker_bus.ROWS[0].index("D")
        double_decker_bus.draw(
            lambda x, y, color: bus_pixels.__setitem__((x, y), color),
            0, 0, two_bit_palette=True,
        )
        self.assertEqual(bus_pixels[(bus_x, 0)], double_decker_bus.PALETTE_64["D"])

        weather_pixels = {}
        weather_sprites.draw_sprite(
            lambda x, y, color: weather_pixels.__setitem__((x, y), color),
            "sunny", 0, 0, limited_palette=False, two_bit_palette=True,
        )
        self.assertEqual(weather_pixels[(6, 0)], weather_sprites.PALETTE_64["Y"])


if __name__ == "__main__":
    unittest.main()
