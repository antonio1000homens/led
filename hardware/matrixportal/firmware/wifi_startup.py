"""Apply the MatrixPortal's measured Wi-Fi power workaround before connecting."""

import time


def start_wifi(settings, radio=None, sleep=None):
    if settings.DISPLAY_BACKEND != "matrix" or settings.SCREEN_SOURCE != "api":
        return
    if radio is None:
        import wifi

        radio = wifi.radio
    if sleep is None:
        sleep = time.sleep

    delay = float(settings.WIFI_STARTUP_DELAY_SECONDS)
    tx_power = float(settings.WIFI_TX_POWER_DBM)
    if delay < 0:
        raise ValueError("WIFI_STARTUP_DELAY_SECONDS must be non-negative")
    if not 2 <= tx_power <= 20:
        raise ValueError("WIFI_TX_POWER_DBM must be between 2 and 20")

    # With the patched MatrixPortal CircuitPython runtime, native Web Workflow
    # has already waited for the configured startup interval and connected at
    # the capped power. Keep that connection instead of cycling the radio and
    # applying the delay a second time.
    if radio.enabled and radio.connected:
        radio.tx_power = tx_power
        print("Wi-Fi already connected tx_power_dbm={}".format(radio.tx_power))
        return

    radio.enabled = False
    print("Wi-Fi startup delay={}s".format(delay))
    sleep(delay)
    radio.enabled = True
    radio.tx_power = tx_power
    print("Wi-Fi enabled tx_power_dbm={}".format(radio.tx_power))
