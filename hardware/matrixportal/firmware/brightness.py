"""Brightness helpers for the bit-depth-1 MatrixPortal display.

CircuitPython RGBMatrix exposes only binary output enable today, so the
production bit-depth-1 path uses a static ordered-dither mask to reduce the
number of lit pixels without changing HUB75 scan timing.
"""

BRIGHTNESS_LEVELS = (25, 50, 75, 100)

_BAYER_4X4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def normalize_brightness(percent):
    """Return the nearest supported brightness percentage."""
    try:
        value = int(percent)
    except (TypeError, ValueError):
        value = 100
    return min(BRIGHTNESS_LEVELS, key=lambda candidate: abs(candidate - value))


def pixel_is_blocked(x, y, percent):
    """Return True when the ordered-dither overlay should black this pixel."""
    percent = normalize_brightness(percent)
    if percent >= 100:
        return False
    lit_slots = (percent * 16) // 100
    return _BAYER_4X4[int(y) & 3][int(x) & 3] >= lit_slots


class BrightnessState:
    """Track one of the supported session brightness levels."""

    def __init__(self, percent=100):
        self._index = BRIGHTNESS_LEVELS.index(normalize_brightness(percent))

    @property
    def percent(self):
        return BRIGHTNESS_LEVELS[self._index]

    def adjust(self, direction):
        """Move one level and return (percent, changed)."""
        step = 1 if direction > 0 else -1 if direction < 0 else 0
        new_index = max(0, min(len(BRIGHTNESS_LEVELS) - 1, self._index + step))
        changed = new_index != self._index
        self._index = new_index
        return self.percent, changed
