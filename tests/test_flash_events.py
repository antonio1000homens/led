import unittest

from flash_events import FlashState, parse_flash_event


EVENT = {
    "id": "reminder-1",
    "type": "reminder",
    "label": "Take washing out",
    "due_at": "2026-09-21T18:00:00+01:00",
    "expires_at": "2026-09-21T18:05:00+01:00",
    "source": "alexa",
}


class FlashEventTests(unittest.TestCase):
    def test_valid_event_is_normalized_and_expiry_is_checked(self):
        event = parse_flash_event(EVENT, 1790000000)
        self.assertEqual(event["label"], "Take washing out")
        self.assertIsNone(parse_flash_event(EVENT, 1790010400))

    def test_malformed_event_is_ignored(self):
        for value in ({}, {**EVENT, "type": "other"}, {**EVENT, "expires_at": "bad"}):
            self.assertIsNone(parse_flash_event(value, 0))

    def test_duplicate_is_ignored_and_new_event_replaces_active(self):
        state = FlashState(enabled=True, duration_seconds=5)
        self.assertTrue(state.accept(EVENT, 0))
        self.assertFalse(state.accept(EVENT, 1))
        replacement = {**EVENT, "id": "reminder-2", "label": "Close the door"}
        self.assertTrue(state.accept(replacement, 2))
        self.assertEqual(state.screen()["label"], "Close the door")
        self.assertTrue(state.active(6))
        self.assertFalse(state.active(8))

    def test_disabled_state_does_not_parse_or_retain_events(self):
        state = FlashState(enabled=False)
        self.assertFalse(state.accept(EVENT, 0))
        self.assertIsNone(state.screen())


if __name__ == "__main__":
    unittest.main()
