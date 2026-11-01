"""Small, deterministic 256x32 Alexa timer themes.

Only the completed state draws scenery. All functions are CircuitPython-safe:
no network, randomness, image files or full-frame animation buffers.
"""
from math import sin, pi

SCENE_WIDTH = 194
FINISH_MOTION_SECONDS = 1.5
TIMER_THEMES = ("caterpillar", "race", "rocket", "stars")
# A compact 3x7 font, scaled to fill 21 pixels vertically for MM:SS.
CLOCK_FONT = {
    "0": ("111", "101", "101", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "010", "010", "111"),
    "2": ("111", "001", "001", "111", "100", "100", "111"),
    "3": ("111", "001", "001", "111", "001", "001", "111"),
    "4": ("101", "101", "101", "111", "001", "001", "001"),
    "5": ("111", "100", "100", "111", "001", "001", "111"),
    "6": ("111", "100", "100", "111", "101", "101", "111"),
    "7": ("111", "001", "001", "010", "010", "010", "010"),
    "8": ("111", "101", "101", "111", "101", "101", "111"),
    "9": ("111", "101", "101", "111", "001", "001", "111"),
    ":": ("000", "010", "010", "000", "010", "010", "000"),
}


def theme_for_timer(timer_id):
    """Stable pseudo-random theme: no theme switch on MQTT refresh or resume."""
    value = str(timer_id or "")
    checksum = sum((index + 1) * ord(character) for index, character in enumerate(value))
    return TIMER_THEMES[checksum % len(TIMER_THEMES)]


def clock_layout(text):
    """Clock always touches the far right, leaving ~194 px for the scene."""
    scale = 3 if len(text) <= 5 else 2
    width = len(text) * 4 * scale
    return max(0, 256 - width - 1), (5 if scale == 3 else 9), scale, width


def finish_pose(theme, seconds):
    """Return rotation quarter-turns, x offset, y offset (negative rises)."""
    t = min(1.0, max(0.0, float(seconds or 0) / FINISH_MOTION_SECONDS))
    if theme == "caterpillar":
        if t < 0.5:
            lift = 9 * sin(pi * 2 * t)
        else:
            lift = 5 * sin(pi * 2 * (t - 0.5))
        return 0, 0, -int(round(lift))
    if theme == "race":
        if t >= 1:
            return 0, 0, 0
        return min(3, int(t * 4)), 0, -int(round(7 * sin(pi * t)))
    if theme == "rocket":
        # A single 90-degree turn, followed by a gentle vertical touchdown.
        turn = 0 if t < 0.25 else 3
        return turn, 0, int(round(7 * max(0.0, (t - 0.3) / 0.7)))
    if theme == "stars":
        return (min(3, int(t * 4)) if t < 1 else 0), 0, 0
    raise ValueError("unsupported timer theme")


def rotate_sprite(rows, turns):
    """Rotate compact ASCII sprite frames without allocating full screen buffers."""
    rows = tuple(rows)
    width = max(len(row) for row in rows)
    rows = tuple(row.ljust(width, ".") for row in rows)
    for _ in range(turns % 4):
        rows = tuple("".join(row[x] for row in rows[::-1])
                     for x in range(len(rows[0])))
    return rows


CAR_ROWS = (
    "....................",
    ".......RRRRRR.......",
    ".....RRRRRRRRRR.....",
    "....RRRBBRRRRRRRR...",
    "...RRRRBBRRRRRRRRRR.",
    "..RRRRRRRRRRRRRRRRR.",
    ".RRRRRRRRRRRRRRRRRY.",
    "RRRRRRRRRRRRRRRRRRR.",
    "...DDDD.......DDDD.",
    "...DDDD.......DDDD.",
    "....DD.........DD..",
)
ROCKET_ROWS = (
    "......................",
    "..................RR..",
    ".................RRRR.",
    "....WWWWWWWWWWWWRRRRR",
    "..WWWWWWWWWWWWWWRRRRR",
    "WWWWWWBBBBWWWWWWRRRRR",
    "WWWWWWBBBBWWWWWWRRRRR",
    "..WWWWWWWWWWWWWWRRRRR",
    "....WWWWWWWWWWWWRRRRR",
    ".................RRRR.",
    "..................RR..",
)
STAR_ROWS = (
    "......Y......",
    "......Y......",
    "......Y......",
    "......Y......",
    "....YYYYY....",
    ".....YYY.....",
    "YYYYYYYYYYYYY",
    ".....YYY.....",
    "....YYYYY....",
    "......Y......",
    "......Y......",
    "......Y......",
    "......Y......",
)
SPRITE_ROWS = {"race": CAR_ROWS, "rocket": ROCKET_ROWS, "stars": STAR_ROWS}
SPRITE_COLORS = {
    "race": (0, 0xF14E4B, 0x65C5FF, 0x222838, 0xFFE36A),
    "rocket": (0, 0xE9F2FF, 0x59C4F4, 0xF46872),
    "stars": (0, 0xFFE36A),
}
SPRITE_SYMBOLS = {
    "race": {".": 0, "R": 1, "B": 2, "D": 3, "Y": 4},
    "rocket": {".": 0, "W": 1, "B": 2, "R": 3},
    "stars": {".": 0, "Y": 1},
}

# Palettes are deliberately small (8 colours maximum); background is created
# only when complete, and is never re-rasterized for subsequent animation ticks.
BACKGROUND_COLORS = {
    "caterpillar": (0x142B47, 0x235137, 0x327344, 0x76C65B,
                    0xFFCA63, 0xF184B9, 0x78A2C4, 0x416A49),
    "race": (0x222B46, 0x3E506C, 0x3A4355, 0x657487,
             0xE1CC81, 0xEE9A9A, 0x8BD3A2, 0x94A9C0),
    "rocket": (0x0D1636, 0x233451, 0x426EB0, 0x4CB8CE,
               0x68C793, 0x91BDE7, 0x566F8F, 0xA8D0E2),
    "stars": (0x21173F, 0x32204F, 0x50346A, 0xA66EC1,
              0xFAD56F, 0x72D4FF, 0xD9A1D9, 0x6C599A),
}


def background_index(theme, x, y):
    """Index into the theme's 8-colour background palette."""
    if theme == "caterpillar":
        if y >= 28:
            return 2
        if y >= 21 + ((x // 29) % 4):
            if x % 27 == 5 and y <= 26:
                return 4 if (x // 27) % 2 else 5
            return 1 if y < 26 else 7
        if y >= 20 and x % 27 == 5:
            return 3
        return 0
    if theme == "race":
        if y >= 20:
            return 4 if y in (27, 28) and x % 20 < 9 else (3 if y < 25 else 2)
        if y >= 14:
            return 7
        if 4 <= y <= 12 and x % 6 in (1, 2):
            return (4, 5, 6)[(x // 6 + y // 3) % 3]
        return 1 if y >= 3 else 0
    if theme == "rocket":
        if x >= 160 and (x - 174) ** 2 + (y - 16) ** 2 < 133:
            return 4 if (x + y) % 6 < 2 else (3 if y < 18 else 2)
        if y >= 29 and x > 139:
            return 6
        return 5 if (x * 19 + y * 13) % 137 == 0 else 0
    if theme == "stars":
        if y >= 24:
            return 2 if x % 15 < 7 else 1
        if (x * 11 + y * 17) % 89 == 0:
            return 4 if x % 2 else 5
        return 0 if y < 17 else 1
    raise ValueError("unsupported timer theme")


ACCENT_ROWS = {
    "caterpillar": ("....SSSS....", ".SSSSSSSSSS.", "SSSSSSSSSSSS", "..SSSSSSSS.."),
    "race": ("RRRRWWWW", "RRRRWWWW", "WWWWRRRR", "WWWWRRRR"),
    "rocket": ("..S..", "..S..", "SSSSS", "..S..", "..S.."),
    "stars": ("..S..", "..S..", "SSSSS", "..S..", "..S.."),
}
ACCENT_COLORS = {
    "caterpillar": 0x8EB6D4,
    "race": 0xF6F5FF,
    "rocket": 0xD1ECFF,
    "stars": 0xF9C86E,
}


def accent_positions(theme, seconds):
    """Slow background motion only during completed timer state."""
    tick = int(max(0, seconds) * 4)
    if theme == "caterpillar":
        return ((10 + tick // 2, 5), (100 + tick // 3, 10))
    if theme == "race":
        return ((28, 3 + tick % 3), (117, 4 + (tick + 1) % 3))
    if theme == "rocket":
        return ((25 + tick % 7, 7), (87, 16 + tick % 3))
    return ((27 + tick % 5, 6), (124 - tick % 5, 17))
