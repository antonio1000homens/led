import ast
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
import display as led_display


class Group(list):
    def __init__(self, x=0):
        super().__init__()
        self.x = x


class Bitmap(dict):
    def __init__(self, *args):
        super().__init__()


class Palette(dict):
    def __init__(self, *args):
        super().__init__()

    def make_transparent(self, index):
        pass


class ReminderAnimationTests(unittest.TestCase):
    def test_clock_and_complete_text_travel_together_without_rebuilding(self):
        fake = types.SimpleNamespace(Group=Group, Bitmap=Bitmap, Palette=Palette,
                                     TileGrid=lambda *a, **k: types.SimpleNamespace(**k))
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.display = types.SimpleNamespace(root_group=None)
        display._scaled_label = mock.Mock()
        display._attach_brightness_overlay = mock.Mock()
        display._refresh = mock.Mock()
        screen = {"kind": "flash", "id": "one", "label": "Long reminder " * 8,
                  "duration_seconds": 12}
        with mock.patch.dict(sys.modules, {"displayio": fake}):
            display.show(screen, phase=0)
            root = display.display.root_group
            motion = root[0]
            self.assertEqual(motion.x, 256)
            display._scaled_label.assert_called_once_with(
                motion, screen["label"], 0xFFFFFF, 37, 5, scale=3)
            display.show(screen, phase=6)
            self.assertIs(display.display.root_group, root)
            self.assertLess(motion.x, 0)
            display.show(screen, phase=12)
            self.assertLessEqual(motion.x + 37 + len(screen["label"]) * 15, 0)
            self.assertEqual(display._scaled_label.call_count, 1)
            display.show({**screen, "id": "two", "label": "New reminder"}, phase=0)
            self.assertIsNot(display.display.root_group, root)

    def test_reminder_preserves_elapsed_phase_when_general_animation_is_disabled(self):
        tree = ast.parse((Path(__file__).parents[1] / "code.py").read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == "_display_phase")
        scope = {"settings": types.SimpleNamespace(ANIMATE=False)}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "code.py", "exec"), scope)
        self.assertEqual(scope["_display_phase"]({"kind": "flash"}, 3.25), 3.25)

    def test_clock_fills_panel_height_and_has_bold_hands(self):
        self.assertTrue(led_display.reminder_clock_pixel(14, 0))
        self.assertTrue(led_display.reminder_clock_pixel(14, 28))
        self.assertTrue(led_display.reminder_clock_pixel(14, 5))
        self.assertTrue(led_display.reminder_clock_pixel(22, 14))
        self.assertFalse(led_display.reminder_clock_pixel(0, 0))
