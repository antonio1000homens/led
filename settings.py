"""Safe defaults for the Wokwi fixture simulation.

Copy this file to settings_local.py for a physical board and override the
display/provider/network values there. Never commit credentials.
"""

DISPLAY_BACKEND = "fixture"  # fixture or matrix
SCREEN_SOURCE = "fixture"  # fixture or api
SCREEN_API_URL = "http://127.0.0.1:8000"
STATION_CRS = "NEM"  # used only by the local fixture screen
POLL_SECONDS = 30
ANIMATE = True
ANIMATION_SECONDS = 8
FRAME_SECONDS = 0.2

# Issue #74 remains dormant until Home Assistant issue #3 and the broker path
# are approved. Both flags are required so a local settings file cannot
# accidentally enable a broker connection by supplying credentials alone.
MQTT_ENABLED = False
MQTT_ENABLE_EXPERIMENTAL = False
MQTT_TOPIC = "led/flash/reminder"
MQTT_BROKER = ""
MQTT_PORT = 1883
MQTT_USERNAME = ""
MQTT_PASSWORD = ""
FLASH_SCREEN_DURATION_SECONDS = 5

WIFI_SSID = ""
WIFI_PASSWORD = ""
