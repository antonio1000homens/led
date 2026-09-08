"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

import board

from formatting import format_row, header


class MatrixDisplay:
    def __init__(self):
        import displayio
        import framebufferio
        import rgbmatrix
        from adafruit_display_text import label
        import terminalio

        displayio.release_displays()
        matrix = rgbmatrix.RGBMatrix(
            width=256,
            height=32,
            bit_depth=4,
            addr_pins=board.MTX_ADDRESS[:4],
            **board.MTX_COMMON,
        )
        self.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
        self.display.root_group = displayio.Group()
        self.label_type = label.Label
        self.font = terminalio.FONT

    def show(self, station, services, stale=False):
        import displayio
        palette = displayio.Palette(4)
        palette[0], palette[1], palette[2], palette[3] = 0x000000, 0xFFFFFF, 0xFFAA00, 0xFF3300
        group = displayio.Group()
        group.append(self.label_type(self.font, text=header(station, stale), color=0xFFAA00, x=0, y=3))
        for index, service in enumerate(services[:3]):
            color = 0xFF3300 if service.get("cancelled") else 0xFFFFFF
            group.append(self.label_type(self.font, text=format_row(service), color=color, x=0, y=11 + index * 7))
        self.display.root_group = group


class FixtureDisplay:
    """Wokwi's WS2812 matrix surrogate, with serial output as a fallback."""
    def __init__(self):
        try:
            import neopixel
            self.pixels = neopixel.NeoPixel(board.GP0, 256 * 32, brightness=0.15, auto_write=False)
        except Exception:
            self.pixels = None

    def _pixel(self, x, y, color):
        if self.pixels is None or not (0 <= x < 256 and 0 <= y < 32):
            return
        index = y * 256 + (x if y % 2 == 0 else 255 - x)
        self.pixels[index] = color

    def _text(self, value, x, y, color):
        glyphs = {
            " ": (0, 0, 0, 0, 0), "-": (0, 0, 1, 0, 0), ":": (0, 1, 0, 0, 1),
            "0": (1, 1, 1, 1, 1), "1": (0, 1, 1, 0, 0), "2": (1, 0, 1, 1, 1),
            "3": (1, 0, 1, 0, 1), "4": (1, 1, 1, 0, 0), "5": (1, 1, 0, 0, 1),
            "6": (1, 1, 0, 1, 1), "7": (1, 0, 0, 0, 0), "8": (1, 1, 1, 1, 1),
            "9": (1, 1, 1, 0, 1),
        }
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for char in value.upper():
            if char in alphabet:
                n = alphabet.index(char) + 1
                bits = tuple((n >> i) & 1 for i in range(5))
            else:
                bits = glyphs.get(char, (1, 0, 0, 0, 1))
            for column, bit in enumerate(bits):
                if bit:
                    for row in range(5):
                        self._pixel(x + column, y + row, color)
            x += 6

    def show(self, station, services, stale=False):
        if self.pixels is not None:
            self.pixels.fill((0, 0, 0))
            self._text(header(station, stale), 0, 0, (255, 100, 0))
            for index, service in enumerate(services[:3]):
                color = (255, 20, 0) if service.get("cancelled") else (255, 255, 255)
                self._text(format_row(service), 0, 8 + index * 8, color)
            self.pixels.show()
        print("\n" + header(station, stale))
        for service in services[:3]:
            print(format_row(service).rstrip())


def create(settings):
    return MatrixDisplay() if settings.DISPLAY_BACKEND == "matrix" else FixtureDisplay()
