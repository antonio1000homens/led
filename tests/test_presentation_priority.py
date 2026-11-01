import unittest

from presentation_priority import select_presentation


class PresentationPriorityTests(unittest.TestCase):
    def test_reminder_flash_temporarily_overlays_every_scene(self):
        self.assertEqual(select_presentation(True, True, True), "reminder")

    def test_timer_owns_display_over_football_and_rotation(self):
        self.assertEqual(select_presentation(False, True, True), "timer")
        self.assertEqual(select_presentation(False, True, False), "timer")

    def test_football_prompt_owns_display_over_rotation(self):
        self.assertEqual(select_presentation(False, False, True), "football")

    def test_normal_rotation_is_the_fallback(self):
        self.assertEqual(select_presentation(False, False, False), "rotation")


if __name__ == "__main__":
    unittest.main()
