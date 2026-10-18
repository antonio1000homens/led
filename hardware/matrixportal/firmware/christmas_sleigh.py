"""84x24 pixel-art Rudolph and sleigh, travelling from RIGHT to LEFT.

Each character is one RGB LED. The sprite is mirrored from the original
right-facing design. This module has no Pillow dependency at runtime.
"""

WIDTH = 84
HEIGHT = 24
TRANSPARENT = "."

PALETTE = {
    "R": (225, 48, 60),
    "D": (141, 30, 51),
    "W": (255, 246, 222),
    "G": (255, 189, 58),
    "Y": (255, 225, 126),
    "B": (147, 88, 56),
    "K": (79, 51, 55),
    "S": (152, 199, 204),
    "T": (55, 113, 119),
    "F": (53, 143, 94),
    "L": (116, 197, 105),
    "P": (247, 184, 141),
    "N": (36, 41, 59),
}

ROWS = (
    "......Y..G..........................................................................",
    "......G....G..G.....................................................................",
    ".......G..G...G.....................................................................",
    "........GGGGGG......................................................................",
    ".........G..........................................................................",
    ".........G..........................................................................",
    "........G...................................................................G.......",
    ".......BG........................................................FFFFYFFF..GGGG.....",
    ".....BBNBBB......................................................FFFFYFFFGGDGGG.....",
    "...RBBBBBBBB...............................................RRRWRRYYYYYYYYGDDDDG.....",
    "...BBBBBBBBB.BBBBBBBBB.....B..............GGG..............RRRWRRFFFFYFFFDDDDDG.....",
    "......BBBBBBBBBBBBBBBBBB..Y...............GGGG.............RRRWRRFFFFYFFFDDDDDG.....",
    ".......BBBBBBBBBBBBBBBBBBBB........YYYYYYYYYYGG............RRRWRRFFFFYFFFDDDDGG.....",
    "........BBGBBBBBBBBBBBBBB......YYYY.....GY.GRRRGGGGGGGGGGGGGGGGGGGGGGGGGGGDDDGG.....",
    "..........BBBKKBBBBBKKBBYYYYYYY.........G..GGRRRRRRRRRRRRRRRRRRRRRRRRRRRRGDDDGG.....",
    "..........BBBKKBBBBBKK..................G..GGRRRRRRRRRRYRRRRRWRRRRRRRRRRRGGGGG......",
    "............KK.......KK..................G..GGGRRRRRRRRRRRRRRRRRRRRRRRRRRGGGG.......",
    "............KK.......KK..................G....GGGRRRRRBBRRRRRRRRRRRRRRGBB..G........",
    "............KK.......KK...................G....GGGGGGGBBGGGGGGGGGGGGGG.BB...........",
    "...........KK.........KK...................G..........BB...............BB...........",
    "...........KK.........KK....................GGG.......BB...............BB.....G.....",
    "............G..........G.......................GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG.Y....",
    "................................................BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB.....",
    "....................................................................................",
)

PALETTE_INDEX = {".": 0}
for _index, _key in enumerate(PALETTE, 1):
    PALETTE_INDEX[_key] = _index


def draw(plot_pixel, x, y, display_width=256, display_height=32):
    """Draw to a framebuffer through plot_pixel(px, py, rgb)."""
    for dy, row in enumerate(ROWS):
        py = y + dy
        if py < 0 or py >= display_height:
            continue
        for dx, key in enumerate(row):
            px = x + dx
            if key != TRANSPARENT and 0 <= px < display_width:
                plot_pixel(px, py, PALETTE[key])


def draw_indexed(bitmap, x, y, display_width=256, display_height=32):
    """Draw into an indexed bitmap; configure palette with PALETTE_INDEX."""
    for dy, row in enumerate(ROWS):
        py = y + dy
        if not 0 <= py < display_height:
            continue
        for dx, key in enumerate(row):
            px = x + dx
            if key != TRANSPARENT and 0 <= px < display_width:
                bitmap[px, py] = PALETTE_INDEX[key]
