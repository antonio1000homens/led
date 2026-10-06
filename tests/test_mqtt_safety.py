import unittest

import settings


class MqttSafetyTests(unittest.TestCase):
    def test_checked_in_firmware_keeps_mqtt_dormant(self):
        self.assertFalse(settings.MQTT_ENABLED)
        self.assertFalse(settings.MQTT_ENABLE_EXPERIMENTAL)
        self.assertEqual(settings.MQTT_BROKER, "")

    def test_flash_duration_is_not_a_local_setting(self):
        self.assertFalse(hasattr(settings, "FLASH_SCREEN_DURATION_SECONDS"))


if __name__ == "__main__":
    unittest.main()
