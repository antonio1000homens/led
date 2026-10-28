"""Regression coverage for the SL7 bus sweep (issue #226)."""

import ast
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
import display as led_display


class Group(list):
    def __init__(self, x=0, y=0):
        super().__init__()
        self.x, self.y = x, y


class Bitmap(dict):
    def __init__(self, width, height, colors):
        super().__init__()
        self.width, self.height = width, height


class Palette(dict):
    def __init__(self, count):
        super().__init__()

    def make_transparent(self, index):
        pass


class BusIntroAnimationTests(unittest.TestCase):
    def test_bus_motion_and_tfl_red_on_matrix_display(self):
        displayio = types.SimpleNamespace(
            Group=Group, Bitmap=Bitmap, Palette=Palette,
            TileGrid=lambda bitmap, pixel_shader, **kwargs: types.SimpleNamespace(
                bitmap=bitmap, palette=pixel_shader, **kwargs),
        )
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.display = types.SimpleNamespace(root_group=None)
        display._bus_intro_group = None
        display._scaled_label = mock.Mock()
        display._attach_brightness_overlay = mock.Mock()
        display._refresh = mock.Mock()
        display._record_animation_update = mock.Mock()
        display._animation_class = mock.Mock(return_value="steam_train")
        screen = {
            "kind": "bus_intro", "id": "sl7-heathrow-intro",
            "animation_speed": 24, "words": "Beep! Beep!..."
        }
        with mock.patch.dict(sys.modules, {"displayio": displayio}):
            display._show_bus_intro(screen, 0)
            scene = display.display.root_group
            motion = display._bus_intro_motion_group
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH)
            self.assertEqual((motion[0].bitmap.width, motion[0].bitmap.height), (84, 24))
            self.assertEqual(motion[0].palette[led_display.DOUBLE_DECKER_BUS_PALETTE_INDEX['R']], 0xFF0000)
            self.assertEqual(
                motion[0].bitmap[6, 0], led_display.DOUBLE_DECKER_BUS_PALETTE_INDEX['D']
            )

            display._show_bus_intro(screen, led_display.DISPLAY_WIDTH / 24)
            self.assertEqual(motion.x, 0)
            # The bus reaches the left edge and stays fully visible there.
            display._show_bus_intro(screen, (led_display.DISPLAY_WIDTH + 100) / 24)
            self.assertEqual(motion.x, 0)
            self.assertIs(scene, display.display.root_group)
            display._scaled_label.assert_called_once()

    def test_fallback_fixture_bus_stops_at_left_edge(self):
        display = led_display.FixtureDisplay.__new__(led_display.FixtureDisplay)
        display.pixels = None
        display._pixel = mock.Mock()
        display._text = mock.Mock()
        screen = {"words": "Beep", "animation_speed": 40}
        with mock.patch.object(led_display, "draw_double_decker_bus") as draw_sprite:
            display._bus_intro(screen, 0)
            draw_sprite.assert_called_once_with(
                display._pixel, led_display.DISPLAY_WIDTH,
                led_display.BUS_VERTICAL_OFFSET,
                limited_palette=led_display.MATRIX_BIT_DEPTH == 1,
            )
            self.assertEqual(
                display._text.call_args,
                mock.call("Beep", led_display.DISPLAY_WIDTH + 84 + led_display.BUS_TEXT_GAP,
                          12 + led_display.BUS_VERTICAL_OFFSET, (255, 170, 0)),
            )
            display._bus_intro(screen, (led_display.DISPLAY_WIDTH + 70) / 40)
            self.assertEqual(draw_sprite.call_args.args[1], 0)

    def test_bus_keeps_real_phase_with_animations_disabled(self):
        tree = ast.parse((Path(__file__).parents[1] / "code.py").read_text())
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_display_phase", "_smooth_bus_intro", "_smooth_football")
        ]
        scope = {
            "settings": types.SimpleNamespace(ANIMATE=False, DISPLAY_BACKEND="matrix"),
            "_smooth_departures": lambda screen: False,
            "_smooth_steam_train": lambda screen: False,
            "_smooth_football": lambda screen: True,
            "_smooth_queue": lambda screen: False,
            "_smooth_sun_weather": lambda screen: False,
            "_smooth_bin_collection": lambda screen: False,
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "code.py", "exec"), scope)
        self.assertEqual(
            scope["_display_phase"]({"kind": "bus_intro"}, 7.5), 7.5
        )
        self.assertEqual(
            scope["_display_phase"]({"kind": "football_score"}, 7.5), 7.5
        )
        self.assertEqual(
            scope["_display_phase"]({"kind": "unrelated"}, 7.5), 2
        )

    def test_bus_intro_uses_smooth_animation_scheduler(self):
        tree = ast.parse((Path(__file__).parents[1] / "code.py").read_text())
        assignment = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "smooth_animation"
                    for target in node.targets)
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_smooth_bus_intro"
                for node in ast.walk(assignment.value)
            ),
            "bus intro must use the same frame paced loop as the train intro",
        )
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        bus_fps = display.animation_cadence({"kind": "bus_intro"}, 0)
        train_fps = display.animation_cadence({"kind": "steam_train_intro"}, 0)
        self.assertEqual(bus_fps, train_fps)

    def test_intro_scene_is_prebuilt_without_becoming_visible(self):
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display._bus_intro_cache_matches = mock.Mock(return_value=False)
        display._build_bus_intro_scene = mock.Mock()
        self.assertTrue(display.prepare_intro({"kind": "bus_intro"}))
        display._build_bus_intro_scene.assert_called_once_with({"kind": "bus_intro"})
        display._bus_intro_cache_matches.return_value = True
        display._build_bus_intro_scene.reset_mock()
        self.assertFalse(display.prepare_intro({"kind": "bus_intro"}))
        display._build_bus_intro_scene.assert_not_called()

    def test_simulator_matches_red_bus_and_left_edge_stop(self):
        source = (Path(__file__).parents[1] / "simulator/index.html").read_text()
        bus = source.split("function drawBus(screen, phase)", 1)[1].split(
            "function splitSl7Due", 1
        )[0]
        self.assertIn("doubleDeckerBusSprite.rows.forEach", bus)
        self.assertIn("doubleDeckerBusSprite.palette[symbol]", bus)
        self.assertIn("const x = Math.max(0, Math.round(", bus)
        self.assertIn("const BUS_WIDTH = 84 * FONT_PIXEL_SCALE", source)


if __name__ == "__main__":
    unittest.main()
