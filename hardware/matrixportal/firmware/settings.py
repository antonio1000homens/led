"""Safe defaults for the Wokwi fixture simulation.

Copy this file to settings_local.py for a physical board and override the
display/provider/network values there. Never commit credentials.
"""

try:
    import os
except ImportError:  # pragma: no cover - CircuitPython always provides os
    os = None


def _web_workflow_value(name):
    """Read a CircuitPython settings.toml value when available."""
    return os.getenv(name, "") if os is not None else ""

DISPLAY_BACKEND = "fixture"  # fixture or matrix
SCREEN_SOURCE = "fixture"  # fixture or api
SCREEN_API_URL = "http://127.0.0.1:8000"
STATION_CRS = "NEM"  # used only by the local fixture screen
POLL_SECONDS = 30
ANIMATE = True
ANIMATION_SECONDS = 8
FRAME_SECONDS = 0.2

# MatrixPortal boot brightness. Runtime button changes are session-local.
MATRIX_BRIGHTNESS_PERCENT = 100

# Enable the reminder listener; the experimental gate remains available as a
# board-local override for disabling the feature.
MQTT_ENABLED = True
MQTT_ENABLE_EXPERIMENTAL = True
MQTT_TOPIC = "led/flash/reminder"
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""

WIFI_SSID = _web_workflow_value("WIFI_SSID")
WIFI_PASSWORD = _web_workflow_value("WIFI_PASSWORD")
WIFI_STARTUP_DELAY_SECONDS = 10
WIFI_TX_POWER_DBM = 8
