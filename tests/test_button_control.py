import unittest

from brightness import BrightnessState, pixel_is_blocked
from button_control import ButtonGesture, DebouncedButton


class DebouncedButtonTests(unittest.TestCase):
    def test_active_low_press_is_emitted_once_after_debounce(self):
        state = [True]
        button = DebouncedButton(lambda: state[0], debounce_seconds=0.05)
        state[0] = False
        self.assertFalse(button.poll(1.00))
        self.assertTrue(button.poll(1.06))
        self.assertFalse(button.poll(1.07))
        self.assertFalse(button.poll(1.20))

    def test_release_does_not_emit_press(self):
        state = [False]
        button = DebouncedButton(lambda: state[0], debounce_seconds=0.05)
        state[0] = True
        self.assertFalse(button.poll(1.00))
        self.assertFalse(button.poll(1.06))


class ButtonGestureTests(unittest.TestCase):
    def test_short_press_is_emitted_on_release(self):
        state = [True]
        gesture = ButtonGesture(lambda: state[0], debounce_seconds=0.05, long_press_seconds=0.8)
        state[0] = False
        self.assertIsNone(gesture.poll(1.00))
        self.assertIsNone(gesture.poll(1.06))
        state[0] = True
        self.assertIsNone(gesture.poll(1.10))
        self.assertEqual(gesture.poll(1.16), "short")

    def test_long_press_does_not_also_emit_short(self):
        state = [True]
        gesture = ButtonGesture(lambda: state[0], debounce_seconds=0.05, long_press_seconds=0.8)
        state[0] = False
        gesture.poll(1.00)
        gesture.poll(1.06)
        self.assertEqual(gesture.poll(1.86), "long")
        state[0] = True
        gesture.poll(1.90)
        self.assertIsNone(gesture.poll(1.96))


class BrightnessStateTests(unittest.TestCase):
    def test_levels_are_clamped_and_step_one_at_a_time(self):
        state = BrightnessState(100)
        self.assertEqual(state.adjust(1), (100, False))
        self.assertEqual(state.adjust(-1), (75, True))
        self.assertEqual(state.adjust(-1), (50, True))
        self.assertEqual(state.adjust(-1), (25, True))
        self.assertEqual(state.adjust(-1), (25, False))

    def test_dither_blocks_expected_fraction_of_four_by_four_cell(self):
        for percent, blocked in ((100, 0), (75, 4), (50, 8), (25, 12)):
            count = sum(
                1
                for y in range(4)
                for x in range(4)
                if pixel_is_blocked(x, y, percent)
            )
            self.assertEqual(count, blocked)


if __name__ == "__main__":
    unittest.main()
