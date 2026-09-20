"""Minimal MatrixPortal S3 + HUB75 RGB smoke test.

Copy this file to CIRCUITPY/code.py for the first physical-panel test.

The repository's target panels are 64x32 and are chained horizontally. Start
with PANEL_COUNT = 1 so a wiring or power problem is isolated to one panel.
Set PANEL_COUNT = 4 after the first panel works.
"""

import time

import board
import displayio
import framebufferio
import rgbmatrix


PANEL_WIDTH = 64
PANEL_HEIGHT = 32
PANEL_COUNT = 1
BIT_DEPTH = 2
HOLD_SECONDS = 2

# Deliberately use modest RGB levels for the first test instead of driving a
# whole panel at maximum white.
TEST_COLORS = (
    ("RED", 0x400000),
    ("GREEN", 0x004000),
    ("BLUE", 0x000040),
    ("BLACK", 0x000000),
)


displayio.release_displays()

matrix = rgbmatrix.RGBMatrix(
    width=PANEL_WIDTH * PANEL_COUNT,
    height=PANEL_HEIGHT,
    bit_depth=BIT_DEPTH,
    doublebuffer=True,
    addr_pins=board.MTX_ADDRESS[:4],
    **board.MTX_COMMON,
)

display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)

bitmap = displayio.Bitmap(PANEL_WIDTH * PANEL_COUNT, PANEL_HEIGHT, 1)
palette = displayio.Palette(1)
tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)

root = displayio.Group()
root.append(tile_grid)
display.root_group = root

print("MatrixPortal S3 HUB75 smoke test started")
print("Panel count:", PANEL_COUNT)
print("Display size: {}x{}".format(PANEL_WIDTH * PANEL_COUNT, PANEL_HEIGHT))

while True:
    for name, color in TEST_COLORS:
        print(name)
        palette[0] = color
        time.sleep(HOLD_SECONDS)
