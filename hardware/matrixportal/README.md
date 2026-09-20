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
