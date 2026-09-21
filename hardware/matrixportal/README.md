# MatrixPortal S3 first hardware test

This folder contains a deliberately small CircuitPython smoke test for the
physical HUB75 panels.

## Safe first connection

Start with one panel:

- power the MatrixPortal S3 from its USB-C connector;
- power the HUB75 panel from the separate regulated 5 V LED power supply;
- connect the MatrixPortal HUB75 output to the panel's **IN** connector;
- the HUB75 cable provides signal grounds between the controller and panel;
- do not try to power the LED panel from USB.

The test defaults to one 64x32 panel. Once one panel works, change
`PANEL_COUNT = 4` to test the repository's full 256x32 horizontal chain.

## Install CircuitPython from macOS

1. Use a USB-C cable that carries data, not a charge-only cable.
2. Connect the MatrixPortal S3 to the Mac.
3. Double-click **RESET**. A drive named `MATRXS3BOOT` should appear.
4. Download the current stable MatrixPortal S3 CircuitPython UF2 from:
   <https://circuitpython.org/board/adafruit_matrixportal_s3/>
5. Drag the UF2 onto `MATRXS3BOOT`.
6. The board reboots and a drive named `CIRCUITPY` appears.

If the board already mounts as `CIRCUITPY`, CircuitPython is already
installed and you can skip the UF2 step.

## Run the RGB smoke test

Copy `rgb_test.py` from this folder to the root of the `CIRCUITPY` drive
and rename it to `code.py`:

```sh
cp hardware/matrixportal/rgb_test.py /Volumes/CIRCUITPY/code.py
```

CircuitPython automatically reloads `code.py` when the file is saved.

With the panel powered separately you should see the whole panel cycle every
two seconds through dim red, green, blue, and black.

The colours are intentionally limited to roughly 25% per channel for this
first test rather than turning the entire panel full-bright white.

## Serial console on macOS

To see the test messages, find the CircuitPython USB serial device:

```sh
ls /dev/cu.usbmodem*
```

Then connect with the macOS `screen` command, substituting the device name
shown above:

```sh
screen /dev/cu.usbmodemXXXX 115200
```

Exit `screen` with **Ctrl-A**, then **\\** and confirm.

Expected output repeats the colour names:

```text
MatrixPortal S3 HUB75 smoke test started
Panel count: 1
Display size: 64x32
RED
GREEN
BLUE
BLACK
```

## After one panel works

Change:

```python
PANEL_COUNT = 1
```

to:

```python
PANEL_COUNT = 4
```

Then connect panel 1 **OUT** to panel 2 **IN**, panel 2 **OUT** to panel 3
**IN**, and panel 3 **OUT** to panel 4 **IN**. Each panel still needs its
proper 5 V power connection.

The smoke test intentionally uses the same MatrixPortal S3 pin setup as
`display.py`:

```python
addr_pins=board.MTX_ADDRESS[:4],
**board.MTX_COMMON,
```

If a panel displays repeated rows, shifted rows, wrong colours, or no image
while the serial test is running, check the panel model/scan type and HUB75
IN/OUT orientation before changing the application renderer.

## Install the production application

After the four-panel smoke test works, replace the smoke-test `code.py` with
the real application. Put this uncommitted `settings_local.py` on the root of
the `CIRCUITPY` drive:

```python
DISPLAY_BACKEND = "matrix"
SCREEN_SOURCE = "api"
SCREEN_API_URL = "https://led.alf-broadcast.co.uk"

POLL_SECONDS = 30
ANIMATE = False  # use static pages for maximum HUB75 stability
FRAME_SECONDS = 0.2

WIFI_SSID = "YOUR_WIFI_NAME"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
```

Keep Wi-Fi credentials out of `settings.py` and out of Git. The application
uses `wifi.radio.connect(...)` through `ScreenClient` and reads production
screen data from `/api/screens`.

From the repository root, copy the application and its CircuitPython modules:

```sh
cp code.py settings.py queue_display.py queue_cycle.py display.py \
   formatting.py fixtures.py screen_client.py button_control.py matrix_runtime.py \
   flash_events.py mqtt_client.py \
   gtsr4.pem /Volumes/CIRCUITPY/
cp settings_local.py /Volumes/CIRCUITPY/
```

The current runtime dependencies are listed in `requirements.txt`. Install
them into a temporary macOS environment and target the board:

```sh
python3 -m venv .venv-circuitpy
source .venv-circuitpy/bin/activate
pip install circup
circup install -r requirements.txt
```

The MQTT dependency is included for the issue #74 listener, but the listener
is deliberately dormant. `settings.py` keeps both `MQTT_ENABLED` and
`MQTT_ENABLE_EXPERIMENTAL` false, with an empty broker setting. Do not copy
broker credentials or enable either gate until Home Assistant issue #3 and the
broker path have passed review.

When that gate is eventually approved, `circup install -r requirements.txt`
installs `adafruit_minimqtt` into `CIRCUITPY/lib`; the board still uses only
uncommitted `settings_local.py` for broker hostname, port, topic and any
credentials. The board connects outbound and does not require a reserved IP.

`gtsr4.pem` is a public Google Trust Services root certificate required by the
current `led.alf-broadcast.co.uk` certificate chain on this CircuitPython
firmware. Keep it on `CIRCUITPY`; it contains no project secret.

The production application starts in normal mode. Press **UP** to toggle
diagnostic mode. In diagnostic mode, **DOWN** cycles moderate-brightness
full-panel red, green, blue, white, and black. Press **UP** again to return to
the application. In normal mode, **DOWN** immediately advances to the next
screen and restarts its display duration. A reset always returns to normal
mode.

## Serial diagnostics on macOS

With the board connected over USB-C, find its CircuitPython serial device:

```sh
ls /dev/cu.usbmodem*
```

Connect at 115200 baud:

```sh
screen /dev/cu.usbmodemXXXX 115200
```

Startup messages, Wi-Fi failures, API failures, and rendered screen details
are printed there. Exit `screen` with **Ctrl-A**, then **\\**, then confirm
with **y**. Press **Ctrl-D** to reload CircuitPython after saving files; use
**Ctrl-C** to interrupt the running application when debugging.

Always eject `CIRCUITPY` before unplugging it:

```sh
diskutil eject /dev/diskN
```

Replace `diskN` with the external disk shown by `diskutil list`. Keep the
MatrixPortal on USB-C and the HUB75 panels on their separate regulated 5 V
supply; never hot-plug HUB75 cables while powered.
