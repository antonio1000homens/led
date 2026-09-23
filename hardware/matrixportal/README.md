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
`firmware/display.py`:

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

From the repository root, create an uncommitted local settings file if needed:

```sh
cp firmware/settings_local.py.example settings_local.py
```

Then stage and install the application. The install helper flattens `firmware/`
and `shared/` into the layout CircuitPython expects while leaving an existing
`settings_local.py` and `lib/` directory untouched:

```sh
bash scripts/install-firmware.sh /Volumes/CIRCUITPY
cp settings_local.py /Volumes/CIRCUITPY/
```

To inspect the exact payload without writing to the board:

```sh
bash scripts/stage-firmware.sh
ls .build/circuitpy
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
is deliberately dormant. `firmware/settings.py` keeps both `MQTT_ENABLED` and
`MQTT_ENABLE_EXPERIMENTAL` false, with an empty broker setting. Do not copy
broker credentials or enable either gate until Home Assistant issue #3 and the
broker path have passed review.

Flash enablement and display duration are runtime values from `/api/screens`;
they are not configured in `settings_local.py`. The board uses the safe
five-second default until its first successful runtime-config refresh.

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


## Dirty-region refresh benchmark

Issue #92 contains a standalone benchmark for checking whether smaller
`displayio` dirty regions reduce the time spent in
`FramebufferDisplay.refresh()` on the four-panel MatrixPortal S3 chain.

This benchmark temporarily replaces the production `code.py`. It does not use
Wi-Fi, HTTP, MQTT, fonts, or the application renderer.

Copy it to the board:

```sh
cp hardware/matrixportal/partial_refresh_benchmark.py /Volumes/CIRCUITPY/code.py
```

Connect to the serial console and capture the `BENCH` lines. The script runs
three rounds and alternates scenario order to reduce bias from runtime drift.
It compares:

- a full 256×32 dirty TileGrid;
- a 256×8 dirty band;
- a 32×8 dirty band;
- a 32×8 TileGrid moving by one pixel.

All cases use the production-oriented matrix constraints for this experiment:
`bit_depth=1`, `doublebuffer=True`,
`FramebufferDisplay(auto_refresh=False)`, and
`refresh(target_frames_per_second=None)`.

The lit pattern is intentionally sparse so the full-screen case does not drive
all LEDs continuously while still dirtifying the complete TileGrid extent.

Expected serial output is aggregate-only:

```text
MatrixPortal dirty-region refresh benchmark
CONFIG width=256 height=32 bit_depth=1 doublebuffer=True warmup=12 samples=80 rounds=3
ROUND 1
BENCH scenario=full_256x32 count=80 min_ms=... avg_ms=... max_ms=...
BENCH scenario=band_256x8 count=80 min_ms=... avg_ms=... max_ms=...
BENCH scenario=band_32x8 count=80 min_ms=... avg_ms=... max_ms=...
BENCH scenario=move_32x8_1px count=80 min_ms=... avg_ms=... max_ms=...
...
BENCH COMPLETE
```

Do not interpret a smaller dirty area as a native partial HUB75 scan. The
benchmark is specifically intended to determine whether the current
CircuitPython RGBMatrix/Protomatter presentation cost remains effectively
global after `displayio` has already limited composition to dirty regions.

After testing, restore the production application with:

```sh
bash scripts/install-firmware.sh /Volumes/CIRCUITPY
cp settings_local.py /Volumes/CIRCUITPY/
```


## Short-transition cadence experiment

Issue #94 adds explicit application-cadence profiles for matched physical
comparisons. The checked-in and production default is `transition_20` (fixed
B8 presentation with 20 Hz page/header transitions).
The opt-in candidates are:

- `adaptive`: current P1 behaviour, with 12 Hz page/header/departures
  transitions and the Todoist marquee at 8 Hz;
- `transition_15`: P2, with only Todoist page/header transitions at 15 Hz;
- `transition_20`: P3, with only Todoist page/header transitions at 20 Hz.

Set one value in the ignored board-local `settings_local.py`, then install the
current application and reload CircuitPython:

```python
MATRIX_ANIMATION_PROFILE = "transition_15"
```

```sh
bash scripts/install-firmware.sh /Volumes/CIRCUITPY
```

Capture `MATRIX PRESENTATION`, `MATRIX STATS`, and `FRAME PACE` serial lines
for matched runs. The class counters in `MATRIX STATS` distinguish Todoist
marquee, Todoist page slide, header slide, and departures calling updates.
Do not change marquee speed, slide duration, or presentation mode as part of
this comparison. Restore `transition_20` after temporary candidate runs and
verify a clean boot before treating the board as deployable.

For a deterministic local payload that actually exercises both Todoist pages
and the clock/weather header, run the backend with both fixture sources:

```sh
LED_SERVER_HOST=0.0.0.0 bash scripts/run-server.sh \
  --calendar-source fixture \
  --weather-source fixture
```

The calendar fixture is emitted with the production Todoist source identity,
viewport/page timing, and an extended screen duration calculated for all six
events. The weather fixture avoids making the comparison depend on an external
weather request.
