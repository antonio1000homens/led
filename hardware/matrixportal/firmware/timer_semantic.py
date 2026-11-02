"""Compact 1-bit-per-channel semantic timer pixel sprites for 256x32 HUB75.

The destinations remain pinned just left of the right-aligned clock; no
full-frame animation buffers, floating point gradients or runtime rotations.
"""
SEMANTIC_THEMES = ("bedtime", "leaving", "timeout")
# Eight distinct frames, restricted to the seven *visible* 1-bit RGB colours.
# Black is omitted because black text on a black panel disappears.
PENDING_COLOURS = (
    0x00FFFF, 0x0000FF, 0xFF00FF, 0xFF0000,
    0xFFFF00, 0x00FF00, 0xFFFFFF, 0xFFFFFF,
)
# All character frames are 13x13 source pixels and rendered at 2x.
CHARACTER_ROWS = {
    "bedtime": (
        "...YY...YY...", "..YYYYYYYYY..", ".YYYYYYYYYYY.",
        ".YYKYYYYKYY..", ".YYYYYYYYYYY.", "..YYYRRYYY...",
        "...YYYYYYY...", "...BBBBBBB...", "..BBBBBBBBB..",
        "..BBBBBBBBB..", "...BB...BB...", "...BB...BB...",
        "..YYY...YYY..",
    ),
    "leaving": (
        "....RRRRR....", "...RRRRRRR...", "...YYYYYYY...",
        "...YKYKY.....", "...YYYYYYY...", "....YYY......",
        "..MMBBBBBB...", "..MMBBBBBB...", "..MMBBBBBB...",
        "....BBBB.....", "....B..B.....", "...WW..WW....",
        "...WW..WW....",
    ),
    "timeout": (
        "..WWWWWWWWW..", "...W.....W...", "....WCCCW....",
        ".....WCW.....", "......W......", ".....WWW.....",
        "....WCCCW....", ".....WWW.....", "......W......",
        ".....WCW.....", "....WCCCW....", "...W.....W...",
        "..WWWWWWWWW..",
    ),
}
# A filled bed, open doorway and tablet silhouette: 16x18, 14x24, 16x22.
DESTINATION_ROWS = {
    "bedtime": (
        "........", "...WWW..", "...WWWW.", "YYYYYYYY",
        "YYYYYYYY", "YYYYYYYY", "WWWWWWWW", "W......W",
        "W......W",
    ),
    "leaving": (
        ".WWWWW.", ".W...W.", ".W...W.", ".W...W.",
        ".W...W.", ".W...W.", ".W...Y.", ".W...W.",
        ".W...W.", ".W...W.", ".W...W.", "WWWWWWW",
    ),
    "timeout": (
        ".WWWWWW.", "WBBBBBBW", "WBCCCCBW", "WBCCCCBW",
        "WBCCCCBW", "WBCCCCBW", "WBCCCCBW", "WBCCCCBW",
        "WBBBBBBW", "WBBBBBBW", ".WWWWWW.",
    ),
}
CHARACTER_COLORS = {
    "bedtime": (0, 0xFFFF00, 0xFFFFFF, 0x0000FF, 0xFF0000, 0x000000),
    "leaving": (0, 0xFF0000, 0xFFFF00, 0x0000FF, 0xFF00FF, 0xFFFFFF, 0x000000),
    "timeout": (0, 0xFFFFFF, 0x00FFFF),
}
DESTINATION_COLORS = {
    "bedtime": (0, 0xFFFFFF, 0xFFFF00),
    "leaving": (0, 0xFFFFFF, 0xFFFF00),
    "timeout": (0, 0xFFFFFF, 0x0000FF, 0x00FFFF),
}
CHARACTER_SYMBOLS = {
    "bedtime": {".": 0, "Y": 1, "K": 5, "B": 3, "R": 4},
    "leaving": {".": 0, "R": 1, "Y": 2, "K": 6, "B": 3, "M": 4, "W": 5},
    "timeout": {".": 0, "W": 1, "C": 2},
}
DESTINATION_SYMBOLS = {
    "bedtime": {".": 0, "W": 1, "Y": 2},
    "leaving": {".": 0, "W": 1, "Y": 2},
    "timeout": {".": 0, "W": 1, "B": 2, "C": 3},
}
SEMANTIC_BACKGROUND_COLORS = {
    "bedtime": (0x000000, 0x0000FF, 0x000000, 0x0000FF,
                0xFFFF00, 0xFFFFFF, 0x0000FF, 0x000000),
    "leaving": (0x000000, 0x0000FF, 0x00FF00, 0x00FF00,
                0xFFFF00, 0xFF0000, 0x00FFFF, 0xFFFFFF),
    "timeout": (0x000000, 0x0000FF, 0x000000, 0x0000FF,
                0x00FFFF, 0xFFFFFF, 0x0000FF, 0x000000),
}
SEMANTIC_ACCENT_COLORS = {
    "bedtime": 0xFFFFFF,
    "leaving": 0x00FFFF,
    "timeout": 0x00FFFF,
}
SEMANTIC_ACCENT_ROWS = {
    "bedtime": ("..S..", ".SSS.", "SSSSS", ".SSS.", "..S.."),
    "leaving": ("SSSS", "SSSS"),
    "timeout": ("..S..", ".SSS.", "SSSSS", ".SSS.", "..S.."),
}


def destination_position(theme, clock_x):
    """Keep the fixed item safely next to the clock even with HH:MM:SS."""
    rows = DESTINATION_ROWS[theme]
    width, height = len(rows[0]) * 2, len(rows) * 2
    return max(0, int(clock_x) - width - 4), (32 - height) // 2


def semantic_character_position(theme, clock_x, progress, completed=False,
                                vertical_offset=0):
    width = len(CHARACTER_ROWS[theme][0]) * 2
    height = len(CHARACTER_ROWS[theme]) * 2
    target_x = destination_position(theme, clock_x)[0] - width - 3
    x = (target_x if completed else
         int(round(-width + (target_x + width) * max(0, min(1, progress)))))
    base_y = 32 - height
    return x, max(0, min(32 - height, base_y + int(vertical_offset)))


def semantic_marker_x(theme, clock_x, index):
    """10 progress markers avoid the destination itself."""
    target = destination_position(theme, clock_x)[0] - 6
    return int(round(13 + (target - 13) * ((index + 1) / 10))) - 3


def semantic_background_index(theme, x, y):
    """Static scene rasterized only after completion; eight colour indices."""
    if theme == "bedtime":
        if y >= 29:
            return 6
        return 5 if (x * 11 + y * 17) % 113 == 0 else 1
    if theme == "leaving":
        if y >= 27:
            return 2
        if 5 <= y <= 25 and x % 55 in (0, 1):
            return 7
        return 3 if y >= 22 else 1
    if theme == "timeout":
        if y >= 29:
            return 6
        return 4 if (x * 17 + y * 11) % 127 == 0 else 1
    raise ValueError("unknown semantic timer theme")


def semantic_accent_positions(theme, seconds):
    tick = int(max(0, seconds) * 4)
    if theme == "bedtime":
        return ((19 + tick % 7, 5), (92 + tick % 5, 13))
    if theme == "leaving":
        return ((26 + tick % 10, 8), (103 + tick % 10, 14))
    return ((26 + tick % 7, 10), (107 - tick % 7, 17))
