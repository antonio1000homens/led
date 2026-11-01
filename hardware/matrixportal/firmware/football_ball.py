"""Tiny transparent football sprite for the match presentation."""


WIDTH = 16
HEIGHT = 16
ROWS = (
    "......DWWW......",
    "....DDDWWWWW....",
    "...DDDDWWWWWD...",
    "..DDDDWWWWWWDD..",
    ".WWWDWWWDWWDDDD.",
    "WWWWWDDDDDWWDDDW",
    "WWWWWDDDDDDWWWDW",
    "WWWWDDDDDDDWWWWW",
    "WWWWDDDDDDWWWWWW",
    "WWWDWDDDDDWWWWWW",
    "WDDDDWDWWWWWDWWW",
    ".DDDDWWWWWWDDDD.",
    "..DDDDWWWWDDDD..",
    "...DDWWWWWDDD...",
    "....DWWWWWWD....",
    "......WWWW......",
)
# Source-coordinate transform uses a fixed 1/1024 scale; no frame heap allocation.
_ROLL_COS = (1024, 724, 0, -724, -1024, -724, 0, 724)
_ROLL_SIN = (0, 724, 1024, 724, 0, -724, -1024, -724)


PALETTE_INDEX = {".": 0, "W": 1, "D": 2}
PALETTE = {"W": (245, 245, 245), "D": (48, 48, 48)}


def draw_indexed(bitmap, x=0, y=0):
    for row, pixels in enumerate(ROWS):
        for column, pixel in enumerate(pixels):
            index = PALETTE_INDEX[pixel]
            if index:
                bitmap[x + column, y + row] = index

def draw_rolling_indexed(bitmap, frame):
    """Redraw a rotating pattern inside a fixed circular silhouette.

    Uses one persistent bitmap: no rotated TileGrid/Bitmap objects per frame.
    """
    frame = int(frame) % 8
    cosine = _ROLL_COS[frame]
    sine = _ROLL_SIN[frame]
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if ROWS[y][x] == ".":
                bitmap[x, y] = 0
                continue
            dx = 2 * x - 15
            dy = 2 * y - 15
            sx = (15 * 1024 + dx * cosine + dy * sine + 1024) // 2048
            sy = (15 * 1024 - dx * sine + dy * cosine + 1024) // 2048
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT and ROWS[sy][sx] == "D":
                bitmap[x, y] = 2
            else:
                bitmap[x, y] = 1
