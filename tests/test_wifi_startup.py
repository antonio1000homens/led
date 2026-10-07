import unittest
from types import SimpleNamespace
from unittest import mock

from wifi_startup import start_wifi


class WifiStartupTests(unittest.TestCase):
    def settings(self, **overrides):
        values = dict(DISPLAY_BACKEND="matrix", SCREEN_SOURCE="api",
                      WIFI_STARTUP_DELAY_SECONDS=10, WIFI_TX_POWER_DBM=8)
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_limit_is_applied_after_delay_before_application_connects(self):
        events = []

        class Radio:
            enabled = False
            connected = False

            def __setattr__(self, name, value):
                events.append((name, value))
                object.__setattr__(self, name, value)

        radio = Radio()
        start_wifi(self.settings(), radio, lambda delay: events.append(("sleep", delay)))
        self.assertEqual(events, [("enabled", False), ("sleep", 10),
                                  ("enabled", True), ("tx_power", 8)])

    def test_fixture_execution_does_not_start_hardware_wifi(self):
        radio, sleep = mock.Mock(), mock.Mock()
        for overrides in ({"DISPLAY_BACKEND": "fixture"}, {"SCREEN_SOURCE": "fixture"}):
            start_wifi(self.settings(**overrides), radio, sleep)
        self.assertEqual(radio.mock_calls, [])
        sleep.assert_not_called()

    def test_invalid_configuration_does_not_enable_radio(self):
        for overrides in ({"WIFI_STARTUP_DELAY_SECONDS": -1},
                          {"WIFI_TX_POWER_DBM": 30}):
            radio, sleep = mock.Mock(), mock.Mock()
            with self.assertRaises(ValueError):
                start_wifi(self.settings(**overrides), radio, sleep)
            self.assertEqual(radio.mock_calls, [])
            sleep.assert_not_called()
