# MatrixPortal S3 CircuitPython 10.3.0 Wi-Fi cap

This patch sets the ESP32-S3 radio's compile-time default transmit power to 8 dBm for the MatrixPortal S3 board. CircuitPython applies this default when starting the radio, before the native Web Workflow reads its reserved Wi-Fi settings and connects. The same default also applies to later radio starts. The application keeps its own 8 dBm setting as a second guard.

The patch is based on Adafruit CircuitPython 10.3.0, commit `d897c15f24b2a6de6529f138aed4705327020dab`, and changes only `ports/espressif/boards/adafruit_matrixportal_s3/mpconfigboard.h`.

## Rebuild

In an Adafruit CircuitPython 10.3.0 checkout with the Espressif build prerequisites installed:

```sh
git apply /path/to/matrixportal-s3-wifi-default-8dbm.patch
make -C ports/espressif BOARD=adafruit_matrixportal_s3
```

The resulting image is `ports/espressif/build-adafruit_matrixportal_s3/firmware.uf2`. The tested build used ESP-IDF 6.0 and the board's normal Web Workflow and BLE feature configuration. BLE is left enabled so the first hardware test isolates the Wi-Fi default change.

## Hardware test

1. Back up the board's `settings.toml` and `settings_local.py` before installing firmware.
2. Connect the board to the laptop by USB. Double-tap RESET to mount `MATRXS3BOOT`, then copy the custom `firmware.uf2` onto that drive. Wait for `CIRCUITPY` to remount.
3. To test native Web Workflow, add `CIRCUITPY_WIFI_SSID` and `CIRCUITPY_WIFI_PASSWORD` to the board's `settings.toml`, copying the values locally from the existing application `WIFI_SSID` and `WIFI_PASSWORD` entries. Keep the existing `CIRCUITPY_WEB_API_PASSWORD` entry. Do not paste credentials into logs or tickets.
4. Temporarily remove the root `boot.py` radio-off guard from `CIRCUITPY`; otherwise the application boot script disables Wi-Fi after CircuitPython starts Web Workflow. Keep the original file in the backup from step 1.
5. Reset on laptop power first. Confirm `/cp/version.json` responds, then check the board's serial output for the application Wi-Fi startup line reporting `tx_power_dbm=8`.
6. Move the same USB cable and board to the wall supply that previously caused the loop. Check Web Workflow reachability and whether the board remains running through repeated resets and a longer soak. Record the firmware version, supply, connection result, and reset observations.
7. If the test is unstable, return to laptop power and restore the saved settings and `boot.py`. The stock UF2 can be reinstalled from the Adafruit MatrixPortal S3 download page.

This compile proves the patched firmware image builds; it does not prove radio behavior or stability on the physical board. The test should be treated as an experimental firmware install.
