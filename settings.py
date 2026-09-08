"""Safe defaults for the Wokwi fixture simulation.

Copy this file to settings_local.py for a physical board and override the
display/provider/network values there. Never commit credentials.
"""

DISPLAY_BACKEND = "fixture"  # fixture or matrix
DATA_SOURCE = "fixture"  # fixture or national_rail
STATION_CRS = "NEM"
FILTER_CRS = None
POLL_SECONDS = 30
MAX_ROWS = 3

WIFI_SSID = ""
WIFI_PASSWORD = ""
NATIONAL_RAIL_USERNAME = ""
NATIONAL_RAIL_PASSWORD = ""

