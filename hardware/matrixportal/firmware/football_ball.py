"""Tiny transparent football sprite for the firmware's match intro."""


WIDTH = 16
HEIGHT = 16
ROWS = (
    "......WWWW......",
    "....WWWWWWWW....",
    "...WWWWDDWWWW...",
    "..WWWDDDDDDWWW..",
    ".WWWWDDDDDDWWWW.",
    "WWWWDDWWWWDDWWWW",
    "WWWWDWWWWWWDWWWW",
    "WWWWWWWWWWWWWWWW",
    "WWWWWWWWWWWWWWWW",
    "WWWWDWWWWWWDWWWW",
    "WWWWDDWWWWDDWWWW",
    ".WWWWDDDDDDWWWW.",
    "..WWWDDDDDDWWW..",
    "...WWWWDDWWWW...",
    "....WWWWWWWW....",
    "......WWWW......",
)
PALETTE_INDEX = {".": 0, "W": 1, "D": 2}
PALETTE = {"W": (245, 245, 245), "D": (48, 48, 48)}


def draw_indexed(bitmap, x=0, y=0):
    for row, pixels in enumerate(ROWS):
        for column, pixel in enumerate(pixels):
            index = PALETTE_INDEX[pixel]
            if index:
                bitmap[x + column, y + row] = index
