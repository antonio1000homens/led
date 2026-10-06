"""Keep Wi-Fi off until code.py applies its startup delay and transmit limit."""

import wifi

wifi.radio.enabled = False
