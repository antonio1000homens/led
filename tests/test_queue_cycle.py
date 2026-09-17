import unittest

from queue_cycle import (
    QUEUE_PARK_FLASH_SECONDS,
    QUEUE_SPLASH_FLASH_SECONDS,
    QUEUE_SPLASH_SLIDE_IN_SECONDS,
    QUEUE_SPLASH_SLIDE_UP_SECONDS,
    queue_cycle_state,
    queue_park_data_seconds,
    queue_scroll_state,
    queue_slide_seconds,
)
from queue_display import queue_render_state


class QueueScrollTimingTests(unittest.TestCase):
    def test_scroll_speed_controls_slide_duration(self):
        self.assertAlmostEqual(queue_slide_seconds(8), 1.0)
        self.assertAlmostEqual(queue_slide_seconds(16), 0.5)
        self.assertAlmostEqual(queue_slide_seconds(40), 0.2)

    def test_pause_holds_rows_before_upward_scroll(self):
        self.assertEqual(queue_scroll_state(1.9, 5, pause_seconds=2, scroll_speed=16), (0, 0.0))
        start, progress = queue_scroll_state(2.25, 5, pause_seconds=2, scroll_speed=16)
        self.assertEqual(start, 0)
        self.assertAlmostEqual(progress, 0.5)
        self.assertEqual(queue_scroll_state(2.6, 5, pause_seconds=2, scroll_speed=16), (1, 0.0))

    def test_final_viewport_pauses_before_park_switch(self):
        duration = queue_park_data_seconds(5, pause_seconds=2, scroll_speed=16)
        # 2s first viewport + two (0.5s slide + 2s pause) steps.
        self.assertAlmostEqual(duration, 7.0)


class QueueParkCycleTests(unittest.TestCase):
    def test_cycles_thorpe_then_chessington_then_back(self):
        counts = [5, 4]
        thorpe_data = queue_park_data_seconds(5, 1, 16)
        chess_data = queue_park_data_seconds(4, 1, 16)
        park, _, mode, _ = queue_cycle_state(QUEUE_PARK_FLASH_SECONDS + 0.1, counts, 1, 16, False)
        self.assertEqual((park, mode), (0, "data"))

        second_start = QUEUE_PARK_FLASH_SECONDS + thorpe_data
        park, _, mode, _ = queue_cycle_state(second_start + 0.01, counts, 1, 16, False)
        self.assertEqual((park, mode), (1, "flash"))

        total = (
            QUEUE_PARK_FLASH_SECONDS + thorpe_data
            + QUEUE_PARK_FLASH_SECONDS + chess_data
        )
        park, _, mode, _ = queue_cycle_state(total + 0.01, counts, 1, 16, False)
        self.assertEqual((park, mode), (0, "flash"))

    def test_splash_sequence_precedes_each_parks_data(self):
        counts = [3, 3]
        park, _, mode, _ = queue_cycle_state(0.1, counts, 1, 16, True)
        self.assertEqual((park, mode), (0, "splash_in"))

        t = QUEUE_SPLASH_SLIDE_IN_SECONDS + 0.01
        self.assertEqual(queue_cycle_state(t, counts, 1, 16, True)[2], "splash_flash")
        t += QUEUE_SPLASH_FLASH_SECONDS
        self.assertEqual(queue_cycle_state(t, counts, 1, 16, True)[2], "splash_up")
        t += QUEUE_SPLASH_SLIDE_UP_SECONDS
        self.assertEqual(queue_cycle_state(t, counts, 1, 16, True)[2], "data")

    def test_render_state_uses_current_park_and_shared_timing(self):
        screen = {
            "id": "queue-times",
            "kind": "theme_park_queues",
            "queue_scroll_pause_seconds": 2,
            "queue_scroll_speed": 16,
            "splash_enabled": False,
            "parks": [
                {"id": "thorpe-park", "title": "THORPE PARK", "stale": False, "rides": [
                    {"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}
                ]},
                {"id": "chessington", "title": "CHESSINGTON", "stale": True, "rides": [
                    {"name": "E"}, {"name": "F"}, {"name": "G"}
                ]},
            ],
        }
        first, phase, mode, _ = queue_render_state(screen, QUEUE_PARK_FLASH_SECONDS + 0.1)
        self.assertEqual(first["title"], "THORPE PARK")
        self.assertFalse(first["stale"])
        self.assertEqual(mode, "data")
        self.assertEqual(phase, 0.0)

        second_start = QUEUE_PARK_FLASH_SECONDS + queue_park_data_seconds(4, 2, 16)
        second, _, mode, _ = queue_render_state(screen, second_start + 0.01)
        self.assertEqual(second["title"], "CHESSINGTON")
        self.assertTrue(second["stale"])
        self.assertEqual(mode, "flash")


if __name__ == "__main__":
    unittest.main()
