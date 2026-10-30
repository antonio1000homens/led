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

# Optional isolated MatrixPortal train-motion experiment. Enable only in the
# board-local settings_local.py; normal fixture and production screens ignore it.
STEAM_TRAIN_TEST = False
STEAM_TRAIN_TEST_FPS = 8
STEAM_TRAIN_TEST_SPEED = 8
STEAM_TRAIN_TEST_SLEEP_SLICE_MS = 0
STEAM_TRAIN_TEST_WIFI_OFF_AFTER_SECONDS = 0
STEAM_TRAIN_TEST_WIFI_OFF_DURATION_SECONDS = 30

# MatrixPortal boot brightness. Runtime button changes are session-local.
MATRIX_BRIGHTNESS_PERCENT = 100

# MQTT cycle screens and flash events are enabled by default; board-local broker
# settings are required, and runtime Flash controls gate transient flash events.
MQTT_ENABLED = True
MQTT_ENABLE_EXPERIMENTAL = True
MQTT_TOPIC = "led/flash/reminder"
MQTT_ASSISTANT_RESPONSE_TOPIC = "led/flash/assistant-response"
MQTT_SCREENS_TOPIC = "led/screens/+"
MQTT_FOOTBALL_TOPIC = "led/football/+"
MQTT_FOOTBALL_ENABLED = True
MQTT_BOARD_STATUS_TOPIC = "led/board/screen"
MQTT_BOARD_HEALTH_TOPIC = "led/board/health"
# Synchronous outbound telemetry can stall display rendering on slow broker
# connections. Leave it off unless explicitly enabled in settings_local.py.
MQTT_BOARD_TELEMETRY_ENABLED = False
FIRMWARE_REVISION = "led-football-v1"
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
MQTT_STARTUP_DELAY_SECONDS = 0

WIFI_SSID = _web_workflow_value("WIFI_SSID")
WIFI_PASSWORD = _web_workflow_value("WIFI_PASSWORD")
WIFI_STARTUP_DELAY_SECONDS = 10
WIFI_TX_POWER_DBM = 8
