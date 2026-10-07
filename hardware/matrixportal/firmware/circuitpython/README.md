# MatrixPortal S3 CircuitPython 10.3.0 Wi-Fi cap

This patch sets the MatrixPortal S3 radio's compile-time default transmit power to 8 dBm and waits 10 seconds before CircuitPython's native Web Workflow first enables Wi-Fi. This protects the automatic connection that happens before `boot.py` and `code.py`. Later radio starts also use the 8 dBm default. The application keeps its own 8 dBm setting as a second guard and reuses a connection that the patched runtime has already delayed and capped.

The patch is based on Adafruit CircuitPython 10.3.0, commit `d897c15f24b2a6de6529f138aed4705327020dab`. It changes the MatrixPortal S3 board configuration and the Web Workflow Wi-Fi startup path.

## Rebuild

In an Adafruit CircuitPython 10.3.0 checkout with the Espressif build prerequisites installed:

```sh
git apply --unidiff-zero /path/to/matrixportal-s3-wifi-default-8dbm.patch
make -C ports/espressif BOARD=adafruit_matrixportal_s3
```

The resulting image is `ports/espressif/build-adafruit_matrixportal_s3/firmware.uf2`. The tested build used ESP-IDF 6.0 and the board's normal Web Workflow and BLE feature configuration. BLE is left enabled so the first hardware test isolates the Wi-Fi default change.

## Hardware test

1. Back up the board's `settings.toml` and `settings_local.py` before installing firmware.
2. Connect the board to the laptop by USB. Double-tap RESET to mount `MATRXS3BOOT`, then copy the custom `firmware.uf2` onto that drive. Wait for `CIRCUITPY` to remount.
3. To test native Web Workflow, add `CIRCUITPY_WIFI_SSID` and `CIRCUITPY_WIFI_PASSWORD` to the board's `settings.toml`, copying the values locally from the existing application `WIFI_SSID` and `WIFI_PASSWORD` entries. Keep the existing `CIRCUITPY_WEB_API_PASSWORD` entry. Do not paste credentials into logs or tickets.
4. Keep the existing root `boot.py` radio-off guard. The first Web Workflow attempt is delayed and capped by the patched runtime; `boot.py` then disables Wi-Fi, and the post-boot Workflow restart is delayed and capped again. Application startup preserves that active connection rather than cycling the radio.
5. Reset on laptop power first. Allow up to 20 seconds for the post-boot Workflow restart, confirm `/cp/version.json` responds, then check serial output for `Wi-Fi already connected tx_power_dbm=8`.
6. Move the same USB cable and board to the wall supply that previously caused the loop. Check Web Workflow reachability and whether the board remains running through repeated resets and a longer soak. Record the firmware version, supply, connection result, and reset observations.
7. If the test is unstable, return to laptop power and restore the saved settings and `boot.py`. The stock UF2 can be reinstalled from the Adafruit MatrixPortal S3 download page.

This compile proves the patched firmware image builds; it does not prove radio behavior or stability on the physical board. The test should be treated as an experimental firmware install.
