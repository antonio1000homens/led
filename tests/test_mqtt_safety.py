import unittest

import settings


class MqttSafetyTests(unittest.TestCase):
    def test_mqtt_enabled_but_requires_board_local_broker_configuration(self):
        self.assertTrue(settings.MQTT_ENABLED)
        self.assertTrue(settings.MQTT_ENABLE_EXPERIMENTAL)
        self.assertEqual(settings.MQTT_BROKER, "")
        self.assertEqual(settings.MQTT_STARTUP_DELAY_SECONDS, 30)
        self.assertEqual(settings.MQTT_TOPIC, "led/flash/reminder")
        self.assertEqual(settings.MQTT_SCREENS_TOPIC, "led/screens/+")

    def test_flash_duration_is_not_a_local_setting(self):
        self.assertFalse(hasattr(settings, "FLASH_SCREEN_DURATION_SECONDS"))


if __name__ == "__main__":
    unittest.main()
