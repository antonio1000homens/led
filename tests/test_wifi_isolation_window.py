import unittest

from wifi_isolation_window import WifiIsolationWindow


class Radio:
    def __init__(self):
        self.enabled = True
        self.connected = True


class WifiIsolationWindowTests(unittest.TestCase):
    def test_radio_is_disabled_for_window_then_restored_and_reconnected(self):
        radio = Radio()
        window = WifiIsolationWindow(50, 30)

        window.update(49.9, radio)
        self.assertTrue(radio.enabled)
        self.assertEqual(window.state, "waiting")

        window.update(50, radio)
        self.assertFalse(radio.enabled)
        self.assertEqual(window.state, "offline")

        window.update(79.9, radio)
        self.assertFalse(radio.enabled)

        radio.connected = False
        window.update(80, radio)
        self.assertTrue(radio.enabled)
        self.assertEqual(window.state, "reconnecting")

        window.update(80.1, radio)
        self.assertEqual(window.state, "reconnecting")
        radio.connected = True
        window.update(80.2, radio)
        self.assertEqual(window.state, "done")

if __name__ == "__main__":
    unittest.main()
