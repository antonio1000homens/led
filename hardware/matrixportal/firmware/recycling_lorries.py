"""84x28 LED recycling lorries facing LEFT for 256x32 RGB matrices.

Two variants: 'paper' (blue) and 'plastic_glass' (green).
Each character corresponds to one physical pixel; '.' is transparent.
Sprite strings and RGB tuples are defined statically to avoid generating
new images or palettes while animating (helpful for constrained heaps).
"""

WIDTH = 84
HEIGHT = 28
DEFAULT_Y = 2

PALETTES = {
    'paper': {
        'O': (13, 31, 47),
        'N': (19, 26, 37),
        'K': (64, 79, 94),
        'W': (250, 250, 245),
        'S': (128, 210, 245),
        'T': (47, 133, 176),
        'B': (23, 104, 200),
        'H': (68, 166, 244),
        'D': (12, 69, 145),
        'G': (186, 197, 201),
        'Y': (255, 191, 51),
        'R': (245, 90, 59),
    },
    'plastic_glass': {
        'O': (13, 31, 47),
        'N': (19, 26, 37),
        'K': (64, 79, 94),
        'W': (250, 250, 245),
        'S': (128, 210, 245),
        'T': (47, 133, 176),
        'B': (28, 152, 85),
        'H': (91, 212, 135),
        'D': (16, 103, 59),
        'G': (186, 197, 201),
        'Y': (255, 191, 51),
        'R': (245, 90, 59),
    },
}

PALETTES_1BIT = {
    'paper': {
        'O': (0, 0, 0),
        'N': (0, 0, 0),
        'K': (0, 0, 0),
        'W': (255, 255, 255),
        'S': (0, 255, 255),
        'T': (0, 255, 255),
        'B': (0, 0, 255),
        'H': (0, 255, 255),
        'D': (0, 0, 0),
        'G': (255, 255, 255),
        'Y': (255, 255, 0),
        'R': (255, 0, 0),
    },
    'plastic_glass': {
        'O': (0, 0, 0),
        'N': (0, 0, 0),
        'K': (0, 0, 0),
        'W': (255, 255, 255),
        'S': (0, 255, 255),
        'T': (0, 255, 255),
        'B': (0, 255, 0),
        'H': (0, 255, 0),
        'D': (0, 0, 0),
        'G': (255, 255, 255),
        'Y': (255, 255, 0),
        'R': (255, 0, 0),
    },
}

ROWS = {
    'paper': (
        '....................................................................................',
        '....................................................................................',
        '....................................................................................',
        '.................OOOOOOOOOOOOO......................................................',
        '.................OHHHHHHHHHHHBOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO...',
        '................OBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHBO...',
        '...............OBBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHDD...',
        '...............OBBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHDD...',
        '..............OOOOOOOOOOOOBBBBOBHBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBGGGGGGGGGBBDHBBDD...',
        '..............OOWSSSSSSSOK.D..OBHBBBBBBBBBBBBBBBBBBBBBBBBBBBBWWWGGWWWWWWHHBDHGGDOOO.',
        '.............OOWSSSSSSSSOK.D..DDHBBBWWBBBWBBWWBBWWWBWWBBBBBBBWWWGGWWWWWWWHBDHGGDOOO.',
        '..........KKOOWSSSSSSSSSOK.D..DDHBBBWBWBWBWBWBWBWBBBWBWBBBBBBWWWGGWWWWWWWWBDHBBDODD.',
        '.........NKKOOWSSSSSSSSSOK.D..DDHBBBWWBBWWWBWWBBWWBBWWBBBBBBBWWWGGWDDDDDWWBDHBBDODD.',
        '..........KKOOOOOOOOOOOOOK.D..DDHBBBWBBBWBWBWBBBWBBBWBWBBBBBBWWWGGWWWWWWWWBDHBBDODD.',
        '.........OO................D..DDHBBBWBBBWBWBWBBBWWWBWBWBBBBBBWWWGGWDDDDDWWBDHBBDODD.',
        '.......OO................GGG..DDHBBBBBBBBBBBBBBBBBBBBBBBBBBBBWWWGGWWWWWWWWBDHGGDODR.',
        '......BYBBBBBBBBBBBBWWWBBBBDBBDDHBBBBBBBBBBBBBBBBBBBBBBBBBBBBWWWGGWDDDDDWWBDHGGDODD.',
        '....WWWWBBBBBBBBBBBWBBWWBBBDBBDDHBBBBBBBBBBBBBBBBBBBBBBBBBBBBWWWWWWWWWWWWWBDBBBDGGG.',
        '....WWWWBBBBBBBBBBBWWWBBBBBDBBBBHDDDDDDDDDDDDDDDDDDDDDDDDDDDDDSSSSSSSSSSDDDDDDDDGGG.',
        '....DDDDDDDDDDDDDNNONNDDDDDDDDDBDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDNNONNDDDDDDDDDBOOO.',
        '....DDDDDDDDDDDDNNNNNNNDDDDDDDDOOGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGNNNNNNNGGGGGGGGGOO..',
        '....OOOOOOOOOOONNKKKKKNNOOOOOOOOOKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKNNKKKKKNNKKKKKOOOORO.',
        '...YYYGGGGGGOOONNKGGGKNNOOOOOOOOOKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKNNKGGGKNNKKKKKOOOOOO.',
        '...GGGGGGGGG...ONKGWGKNO.......................................ONKGWGKNO............',
        '...............NNKGGGKNN.......................................NNKGGGKNN............',
        '...............NNNKKKNNN.......................................NNNKKKNNN............',
        '................NNNNNNN.........................................NNNNNNN.............',
        '.................NNONN...........................................NNONN..............',
    ),
    'plastic_glass': (
        '....................................................................................',
        '....................................................................................',
        '....................................................................................',
        '.................OOOOOOOOOOOOO......................................................',
        '.................OHHHHHHHHHHHBOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO...',
        '................OBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHBO...',
        '...............OBBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHHDD...',
        '...............OBBBBBBBBBBBBBBOBHHHHHHHHHHHHHHHHHHHHHHHHHYYYHHHHHHHHHHHHHHHHHHHDD...',
        '..............OOOOOOOOOOOOBBBBOBHBBBBBBBBBBBBBBBBBBBBBBBWWWWWBBBBBBBSSSBBBBDHBBDD...',
        '..............OOWSSSSSSSOK.D..OBHBBBBBBBBBBBBBBBBBBBBBBBWWWWWBBBBBBBSTSBBBBDHGGDOOO.',
        '.............OOWSSSSSSSSOK.D..DDHBBBBBBWWBBBBBBBWWBBBBBBBWWWBBBBBBBBSTSBBBBDHGGDOOO.',
        '..........KKOOWSSSSSSSSSOK.D..DDHBBBBBBWBWBBWBBWBBBBBBBBBWWWBBBBBBBBSTSBBBBDHBBDODD.',
        '.........NKKOOWSSSSSSSSSOK.D..DDHBBBBBBWWBBWWWBWBWBBBBBHWWWWWHBBBBBWWWWWBBBDHBBDODD.',
        '..........KKOOOOOOOOOOOOOK.D..DDHBBBBBBWBBBBWBBWBWBBBBBWWWWWWWBBBBWWWWWWWBBDHBBDODD.',
        '.........OO................D..DDHBBBBBBWBBBBBBBBWWBBBBBWWDDDWWBBBBWWSSSSWBBDHBBDODD.',
        '.......OO................GGG..DDHBBBBBBBBBBBBBBBBBBBBBBWWDDDWWBBBBWSSSSSWBBDHGGDODR.',
        '......BYBBBBBBBBBBBBWWWBBBBDBBDDHBBBBBBBBBBBBBBBBBBBBBBWWWWWWWBBBBWSSSSSWBBDHGGDODD.',
        '....WWWWBBBBBBBBBBBWBBWWBBBDBBDDHBBBBBBBBBBBBBBBBBBBBBBWWWWWWWBBBBWSSSSSWBBDBBBDGGG.',
        '....WWWWBBBBBBBBBBBWWWBBBBBDBBBBHDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDGGG.',
        '....DDDDDDDDDDDDDNNONNDDDDDDDDDBDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDNNONNDDDDDDDDDBOOO.',
        '....DDDDDDDDDDDDNNNNNNNDDDDDDDDOOGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGNNNNNNNGGGGGGGGGOO..',
        '....OOOOOOOOOOONNKKKKKNNOOOOOOOOOKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKNNKKKKKNNKKKKKOOOORO.',
        '...YYYGGGGGGOOONNKGGGKNNOOOOOOOOOKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKNNKGGGKNNKKKKKOOOOOO.',
        '...GGGGGGGGG...ONKGWGKNO.......................................ONKGWGKNO............',
        '...............NNKGGGKNN.......................................NNKGGGKNN............',
        '...............NNNKKKNNN.......................................NNNKKKNNN............',
        '................NNNNNNN.........................................NNNNNNN.............',
        '.................NNONN...........................................NNONN..............',
    ),
}

# Indexed rendering allows one palette index layout for both versions.
# When changing type on the same Bitmap, update its palette first.
INDEX = {'.': 0, 'O': 1, 'N': 2, 'K': 3, 'W': 4,
         'S': 5, 'T': 6, 'B': 7, 'H': 8, 'D': 9,
         'G': 10, 'Y': 11, 'R': 12}


def draw(plot_pixel, x, y=DEFAULT_Y, kind='paper',
         display_width=256, display_height=32, limited_palette=False):
    """Plot a clipped sprite. plot_pixel(px, py, (r,g,b)).

    Works with an existing RGB framebuffer and pixel callback. Does NOT
    clear previously drawn pixels; clear/rebuild the frame before calling.
    """
    data = ROWS[kind]
    colors = PALETTES_1BIT[kind] if limited_palette else PALETTES[kind]
    start_x = max(0, -x)
    stop_x = min(WIDTH, display_width - x)
    start_y = max(0, -y)
    stop_y = min(HEIGHT, display_height - y)
    if start_x >= stop_x or start_y >= stop_y:
        return
    for dy in range(start_y, stop_y):
        line = data[dy]
        py = y + dy
        for dx in range(start_x, stop_x):
            key = line[dx]
            if key != '.':
                plot_pixel(x + dx, py, colors[key])


def draw_indexed(bitmap, x, y=DEFAULT_Y, kind='paper',
                 display_width=256, display_height=32):
    """Draw onto an existing indexed 256x32 displayio.Bitmap.

    Set palette entries using palette_for() once when choosing the lorry.
    Bitmap should be cleared (e.g. bitmap.fill(0)) before each draw.
    """
    data = ROWS[kind]
    start_x = max(0, -x)
    stop_x = min(WIDTH, display_width - x)
    start_y = max(0, -y)
    stop_y = min(HEIGHT, display_height - y)
    if start_x >= stop_x or start_y >= stop_y:
        return
    for dy in range(start_y, stop_y):
        line = data[dy]
        py = y + dy
        for dx in range(start_x, stop_x):
            key = line[dx]
            if key != '.':
                bitmap[x + dx, py] = INDEX[key]


def palette_for(kind='paper', limited_palette=False):
    """Create a displayio.Palette with index 0 as black background.

    Use with a displayio.Bitmap(256, 32, len(INDEX)) in an RGB LED matrix.
    """
    import displayio
    palette = displayio.Palette(len(INDEX))
    palette[0] = 0x000000
    colors = PALETTES_1BIT[kind] if limited_palette else PALETTES[kind]
    for key in colors:
        r,g,b = colors[key]
        palette[INDEX[key]] = (r << 16) | (g << 8) | b
    return palette


# To animate from RIGHT to LEFT:
# x = 256
# each animation tick: clear framebuffer, draw(..., x, 2, kind), refresh
# x -= 1
# if x <= -WIDTH: x = 256
