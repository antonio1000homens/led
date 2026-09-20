import unittest

from button_control import DebouncedButton


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


if __name__ == "__main__":
    unittest.main()
