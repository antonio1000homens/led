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
    def test_clock_and_complete_text_loop_together_without_rebuilding(self):
        fake = types.SimpleNamespace(Group=Group, Bitmap=Bitmap, Palette=Palette,
                                     TileGrid=lambda *a, **k: types.SimpleNamespace(**k))
        display = led_display.MatrixDisplay.__new__(led_display.MatrixDisplay)
        display.display = types.SimpleNamespace(root_group=None)
        display._scaled_label = mock.Mock()
        display._attach_brightness_overlay = mock.Mock()
        display._refresh = mock.Mock()
        screen = {"kind": "flash", "id": "one",
                  "label": "Long reminder message that cannot fit on one screen",
                  "duration_seconds": 30}
        width = (
            led_display.REMINDER_TEXT_X
            + len(screen["label"]) * led_display.WEATHER_FONT_WIDTH * led_display.REMINDER_TEXT_SCALE
        )
        travel = led_display.DISPLAY_WIDTH + width + led_display.REMINDER_SCROLL_GAP
        cycle_seconds = travel / led_display.REMINDER_SCROLL_SPEED

        with mock.patch.dict(sys.modules, {"displayio": fake}):
            display.show(screen, phase=0)
            root = display.display.root_group
            motion = root[0]
            self.assertEqual(motion.x, led_display.DISPLAY_WIDTH)
            display._scaled_label.assert_called_once_with(
                motion,
                screen["label"],
                0xFFFFFF,
                led_display.REMINDER_TEXT_X,
                5,
                scale=led_display.REMINDER_TEXT_SCALE,
            )

            # The full clock/message train clears the left edge instead of
            # stopping when a reminder is wider than the panel.
            display.show(screen, phase=(travel - 1) / led_display.REMINDER_SCROLL_SPEED)
            self.assertLessEqual(motion.x + width, 0)
            self.assertIs(display.display.root_group, root)

            # Once fully off-screen, the same cached train wraps back in from
            # the right and keeps moving for the remainder of the reminder.
            display.show(screen, phase=cycle_seconds + 0.5)
            self.assertGreater(motion.x, 0)
            self.assertLess(motion.x, led_display.DISPLAY_WIDTH)
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
