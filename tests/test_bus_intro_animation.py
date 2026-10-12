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
            self.assertEqual(motion[0].palette[1], 0xFF3300)

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
        display._fill_rect = mock.Mock()
        display._text = mock.Mock()
        screen = {"words": "Beep", "animation_speed": 40}
        display._bus_intro(screen, 0)
        self.assertIn(
            mock.call(led_display.DISPLAY_WIDTH + 3, 10, 43, 12, (255, 51, 0)),
            display._fill_rect.call_args_list,
        )
        display._fill_rect.reset_mock()
        display._bus_intro(screen, (led_display.DISPLAY_WIDTH + 70) / 40)
        red_bodies = [
            call.args for call in display._fill_rect.call_args_list
            if call.args[-1] == (255, 51, 0)
        ]
        self.assertEqual(len(red_bodies), 2)
        self.assertTrue(all(args[0] >= 0 for args in red_bodies))

    def test_bus_keeps_real_phase_with_animations_disabled(self):
        tree = ast.parse((Path(__file__).parents[1] / "code.py").read_text())
        functions = [
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name in ("_display_phase", "_smooth_bus_intro")
        ]
        scope = {
            "settings": types.SimpleNamespace(ANIMATE=False, DISPLAY_BACKEND="matrix"),
            "_smooth_departures": lambda screen: False,
            "_smooth_steam_train": lambda screen: False,
            "_smooth_queue": lambda screen: False,
            "_smooth_sun_weather": lambda screen: False,
            "_smooth_bin_collection": lambda screen: False,
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "code.py", "exec"), scope)
        self.assertEqual(
            scope["_display_phase"]({"kind": "bus_intro"}, 7.5), 7.5
        )
        self.assertEqual(
            scope["_display_phase"]({"kind": "unrelated"}, 7.5), 2
        )

    def test_simulator_matches_red_bus_and_left_edge_stop(self):
        source = (Path(__file__).parents[1] / "simulator/index.html").read_text()
        bus = source.split("function drawBus(screen, phase)", 1)[1].split(
            "function drawBusWheel", 1
        )[0]
        self.assertIn("'#ff3300'", bus)
        self.assertIn("const x = Math.max(0, Math.round(", bus)


if __name__ == "__main__":
    unittest.main()
