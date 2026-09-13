"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

import board

from formatting import (
    AGENDA_VISIBLE_ROWS,
    QUEUE_VISIBLE_ROWS,
    agenda_scroll_state,
    calendar_row,
    calling_text,
    format_row,
    queue_scroll_state,
    row_slide_phase,
)


DISPLAY_WIDTH = 256
CLOCK_X = 226
STALE_X = 190
QUEUE_FIRST_Y = 11
QUEUE_ROW_HEIGHT = 8
AGENDA_FIRST_Y = 11
AGENDA_ROW_HEIGHT = 8
WEATHER_Y = 24
WEATHER_LABEL_Y = 27
WEATHER_ICON_WIDTH = 7
WEATHER_GAP = 1
WEATHER_FONT_WIDTH = 6

WEATHER_ICONS = {
    "clear_day": ("..#.#..", "...#...", ".#####.", "..###..", ".#####.", "...#...", "..#.#.."),
    "clear_night": ("...###.", "..###..", ".###...", ".###...", ".####..", "..####.", "...###."),
    "partly_cloudy_day": (".#.#...", "..#....", ".###...", "...##..", "..#####", ".######", "......."),
    "partly_cloudy_night": ("..##...", ".##....", ".###...", "...##..", "..#####", ".######", "......."),
    "cloudy": (".......", "...##..", "..####.", ".######", "#######", ".......", "......."),
    "fog": (".......", ".#####.", ".......", "#######", ".......", ".#####.", "......."),
    "rain": ("...##..", "..####.", ".######", "#######", "..#.#..", ".#.#...", "#.#...."),
    "snow": ("...##..", "..####.", ".######", "#######", ".#.#.#.", "..#.#..", ".#.#.#."),
    "storm": ("...##..", "..####.", ".######", "#######", "...##..", "..##...", "...#..."),
    "unknown": (".#####.", "##...##", "....##.", "...##..", "..##...", ".......", "..##..."),
}

WEATHER_COLORS = {
    "clear_day": 0xFFAA00,
    "clear_night": 0xAACCFF,
    "partly_cloudy_day": 0xFFCC55,
    "partly_cloudy_night": 0xAACCFF,
    "cloudy": 0xBBBBBB,
    "fog": 0x888888,
    "rain": 0x55AAFF,
    "snow": 0xFFFFFF,
    "storm": 0xFFCC00,
    "unknown": 0x888888,
}


def _clip(value, width):
    return str(value or "")[:width]


def _queue_row(ride):
    state = "{}m".format(ride.get("wait_minutes", 0)) if ride.get("open") else "CLOSED"
    name = _clip(ride.get("name"), 24).ljust(24)
    return (name + state.rjust(8))[:32]


def _weather_text(weather):
    if not isinstance(weather, dict):
        return None
    value = weather.get("temperature_c")
    if value is None:
        return "--C"
    try:
        return "{}C".format(int(round(float(value))))
    except (TypeError, ValueError):
        return "--C"


def _weather_icon(weather):
    if not isinstance(weather, dict):
        return None, WEATHER_ICONS["unknown"]
    name = str(weather.get("icon") or "unknown")
    return name, WEATHER_ICONS.get(name, WEATHER_ICONS["unknown"])


def _weather_rgb(icon_name, stale=False):
    color = WEATHER_COLORS.get(icon_name, WEATHER_COLORS["unknown"])
    return 0x777777 if stale else color


def _weather_layout(text):
    text_width = len(str(text)) * WEATHER_FONT_WIDTH
    icon_x = max(0, DISPLAY_WIDTH - (WEATHER_ICON_WIDTH + WEATHER_GAP + text_width))
    return icon_x, icon_x + WEATHER_ICON_WIDTH + WEATHER_GAP


def _rgb_tuple(color):
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _agenda_state(screen, phase):
    events = screen.get("events") or []
    visible = max(1, int(screen.get("viewport_size") or AGENDA_VISIBLE_ROWS))
    page_seconds = screen.get("page_seconds") or 5
    start, progress = agenda_scroll_state(phase, len(events), page_seconds, visible)
    return events, visible, start, progress


class MatrixDisplay:
    def __init__(self):
        import displayio
        import framebufferio
        import rgbmatrix
        from adafruit_display_text import label
        import terminalio

        displayio.release_displays()
        matrix = rgbmatrix.RGBMatrix(
            width=DISPLAY_WIDTH,
            height=32,
            bit_depth=4,
            addr_pins=board.MTX_ADDRESS[:4],
            **board.MTX_COMMON,
        )
        self.display = framebufferio.FramebufferDisplay(matrix, auto_refresh=True)
        self.display.root_group = displayio.Group()
        self.label_type = label.Label
        self.font = terminalio.FONT

    def _label(self, group, text, color, x, y):
        group.append(self.label_type(self.font, text=str(text), color=color, x=x, y=y))

    def _header_mask(self, group):
        import displayio

        bitmap = displayio.Bitmap(DISPLAY_WIDTH, 8, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0x000000
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=0))

    def _rail(self, group, screen, phase):
        services = screen.get("services") or []
        primary = services[0] if services else {"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting"}
        primary_slide = row_slide_phase(phase, 0)
        self._label(group, format_row(primary), 0xFFFFFF, -int((1 - primary_slide) * 220), 3)
        calling = calling_text(primary)
        calling_width = len(calling) * WEATHER_FONT_WIDTH
        calling_x = 0 if calling_width <= DISPLAY_WIDTH else -int((phase * 45) % (calling_width + 40))
        self._label(group, calling, 0xFFAA00, calling_x, 10)
        for index, service in enumerate(services[1:3], start=1):
            slide = row_slide_phase(phase, index)
            x = -int((1 - slide) * 220)
            color = 0xFF3300 if service.get("cancelled") and int(phase * 2) % 2 else 0xFFFFFF
            self._label(group, format_row(service), color, x, 17 + (index - 1) * 8)

    def _queues(self, group, screen, phase):
        rides = screen.get("rides") or []
        if not rides:
            self._label(group, "Queue data unavailable", 0xFFFFFF, 0, QUEUE_FIRST_Y)
        else:
            start, progress = queue_scroll_state(phase, len(rides))
            row_count = QUEUE_VISIBLE_ROWS + (1 if progress > 0 else 0)
            y_offset = int(progress * QUEUE_ROW_HEIGHT)
            for slot in range(row_count):
                ride_index = start + slot
                if ride_index >= len(rides):
                    break
                ride = rides[ride_index]
                self._label(group, _queue_row(ride), 0xFFFFFF if ride.get("open") else 0xFF3300, 0, QUEUE_FIRST_Y + slot * QUEUE_ROW_HEIGHT - y_offset)
        self._header_mask(group)
        self._label(group, _clip(screen.get("title") or "THORPE PARK", 30), 0xFFAA00, 0, 3)

    def _calendar(self, group, screen, phase):
        events, visible, start, progress = _agenda_state(screen, phase)
        if not events:
            self._label(group, "No upcoming events", 0xFFFFFF, 0, AGENDA_FIRST_Y)
        else:
            row_count = min(len(events) - start, visible * 2 if progress > 0 else visible)
            y_offset = int(progress * visible * AGENDA_ROW_HEIGHT)
            for slot in range(max(0, row_count)):
                event_index = start + slot
                if event_index >= len(events):
                    break
                self._label(group, calendar_row(events[event_index]), 0xFFFFFF, 0, AGENDA_FIRST_Y + slot * AGENDA_ROW_HEIGHT - y_offset)
        self._header_mask(group)
        self._label(group, _clip(screen.get("title") or "UPCOMING", 30), 0xFFAA00, 0, 3)

    def _weather(self, group, weather):
        text = _weather_text(weather)
        if text is None:
            return
        import displayio

        icon_x, text_x = _weather_layout(text)
        icon_name, rows = _weather_icon(weather)
        stale = bool(weather.get("stale")) if isinstance(weather, dict) else False
        bitmap = displayio.Bitmap(DISPLAY_WIDTH - icon_x, 8, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = _weather_rgb(icon_name, stale)
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    bitmap[x, y] = 1
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=icon_x, y=WEATHER_Y))
        self._label(group, text, 0xAAAAAA if stale else 0xFFFFFF, text_x, WEATHER_LABEL_Y)

    def show(self, screen, clock_time="--:--", phase=2):
        import displayio

        group = displayio.Group()
        kind = screen.get("kind")
        if kind == "rail_combined":
            self._rail(group, screen, phase)
        elif kind == "theme_park_queues":
            self._queues(group, screen, phase)
        elif kind == "calendar_agenda":
            self._calendar(group, screen, phase)
        else:
            self._label(group, _clip(screen.get("title") or "Display unavailable", 30), 0xFFFFFF, 0, 3)
        if screen.get("stale"):
            self._label(group, "STALE", 0xFF3300, STALE_X, 3)
        self._label(group, clock_time, 0xFFAA00, CLOCK_X, 3)
        self._weather(group, screen.get("weather"))
        self.display.root_group = group


class FixtureDisplay:
    """Wokwi's WS2812 matrix surrogate, with serial output as a fallback."""

    def __init__(self):
        try:
            import neopixel
            self.pixels = neopixel.NeoPixel(board.GP0, DISPLAY_WIDTH * 32, brightness=0.15, auto_write=False)
        except Exception:
            self.pixels = None

    def _pixel(self, x, y, color):
        if self.pixels is None or not (0 <= x < DISPLAY_WIDTH and 0 <= y < 32):
            return
        index = y * DISPLAY_WIDTH + (x if y % 2 == 0 else DISPLAY_WIDTH - 1 - x)
        self.pixels[index] = color

    def _text(self, value, x, y, color):
        glyphs = {
            " ": (0, 0, 0, 0, 0), "-": (0, 0, 1, 0, 0), ":": (0, 1, 0, 0, 1),
            "0": (1, 1, 1, 1, 1), "1": (0, 1, 1, 0, 0), "2": (1, 0, 1, 1, 1),
            "3": (1, 0, 1, 0, 1), "4": (1, 1, 1, 0, 0), "5": (1, 1, 0, 0, 1),
            "6": (1, 1, 0, 1, 1), "7": (1, 0, 0, 0, 0), "8": (1, 1, 1, 1, 1), "9": (1, 1, 1, 0, 1),
        }
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for char in str(value).upper():
            if char in alphabet:
                n = alphabet.index(char) + 1
                bits = tuple((n >> i) & 1 for i in range(5))
            else:
                bits = glyphs.get(char, (1, 0, 0, 0, 1))
            for column, bit in enumerate(bits):
                if bit:
                    for row in range(5):
                        self._pixel(x + column, y + row, color)
            x += WEATHER_FONT_WIDTH

    def _clear_rows(self, start_y, end_y):
        if self.pixels is None:
            return
        for y in range(start_y, end_y):
            for x in range(DISPLAY_WIDTH):
                self._pixel(x, y, (0, 0, 0))

    def _draw_screen(self, screen, phase):
        kind = screen.get("kind")
        if kind == "rail_combined":
            services = screen.get("services") or []
            primary = services[0] if services else {"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting"}
            primary_slide = row_slide_phase(phase, 0)
            self._text(format_row(primary), -int((1 - primary_slide) * 220), 0, (255, 255, 255))
            text = calling_text(primary)
            text_width = len(text) * WEATHER_FONT_WIDTH
            calling_x = 0 if text_width <= DISPLAY_WIDTH else -int((phase * 45) % (text_width + 40))
            self._text(text, calling_x, 8, (255, 100, 0))
            for index, service in enumerate(services[1:3], start=1):
                slide = row_slide_phase(phase, index)
                x = -int((1 - slide) * 220)
                color = (255, 20, 0) if service.get("cancelled") and int(phase * 2) % 2 else (255, 255, 255)
                self._text(format_row(service), x, 16 + (index - 1) * 8, color)
        elif kind == "theme_park_queues":
            rides = screen.get("rides") or []
            if not rides:
                self._text("Queue data unavailable", 0, 8, (255, 255, 255))
            else:
                start, progress = queue_scroll_state(phase, len(rides))
                row_count = QUEUE_VISIBLE_ROWS + (1 if progress > 0 else 0)
                y_offset = int(progress * QUEUE_ROW_HEIGHT)
                for slot in range(row_count):
                    ride_index = start + slot
                    if ride_index >= len(rides):
                        break
                    ride = rides[ride_index]
                    self._text(_queue_row(ride), 0, 8 + slot * QUEUE_ROW_HEIGHT - y_offset, (255, 255, 255) if ride.get("open") else (255, 20, 0))
            self._clear_rows(0, 8)
            self._text(_clip(screen.get("title") or "THORPE PARK", 30), 0, 0, (255, 100, 0))
        elif kind == "calendar_agenda":
            events, visible, start, progress = _agenda_state(screen, phase)
            if not events:
                self._text("No upcoming events", 0, 8, (255, 255, 255))
            else:
                row_count = min(len(events) - start, visible * 2 if progress > 0 else visible)
                y_offset = int(progress * visible * AGENDA_ROW_HEIGHT)
                for slot in range(max(0, row_count)):
                    event_index = start + slot
                    if event_index >= len(events):
                        break
                    self._text(calendar_row(events[event_index]), 0, 8 + slot * AGENDA_ROW_HEIGHT - y_offset, (255, 255, 255))
            self._clear_rows(0, 8)
            self._text(_clip(screen.get("title") or "UPCOMING", 30), 0, 0, (255, 100, 0))
        else:
            self._text(_clip(screen.get("title") or "Display unavailable", 30), 0, 0, (255, 255, 255))

    def _weather(self, weather):
        text = _weather_text(weather)
        if text is None or self.pixels is None:
            return
        icon_x, text_x = _weather_layout(text)
        for y in range(WEATHER_Y, 32):
            for x in range(icon_x, DISPLAY_WIDTH):
                self._pixel(x, y, (0, 0, 0))
        icon_name, rows = _weather_icon(weather)
        stale = bool(weather.get("stale")) if isinstance(weather, dict) else False
        color = _rgb_tuple(_weather_rgb(icon_name, stale))
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    self._pixel(icon_x + x, WEATHER_Y + y, color)
        self._text(text, text_x, WEATHER_Y, (170, 170, 170) if stale else (255, 255, 255))

    def show(self, screen, clock_time="--:--", phase=2):
        if self.pixels is not None:
            self.pixels.fill((0, 0, 0))
            self._draw_screen(screen, phase)
            if screen.get("stale"):
                self._text("STALE", STALE_X, 0, (255, 20, 0))
            self._text(clock_time, CLOCK_X, 0, (255, 100, 0))
            self._weather(screen.get("weather"))
            self.pixels.show()

        print("\n[{}] {}".format(clock_time, screen.get("title") or screen.get("kind") or "screen"))
        kind = screen.get("kind")
        if kind == "rail_combined":
            services = screen.get("services") or []
            if services:
                print(format_row(services[0]).rstrip())
                print(calling_text(services[0]))
                for service in services[1:3]:
                    print(format_row(service).rstrip())
        elif kind == "theme_park_queues":
            rides = screen.get("rides") or []
            start, _ = queue_scroll_state(phase, len(rides))
            for ride in rides[start:start + QUEUE_VISIBLE_ROWS]:
                print(_queue_row(ride).rstrip())
        elif kind == "calendar_agenda":
            events, visible, start, _ = _agenda_state(screen, phase)
            if not events:
                print("No upcoming events")
            for event in events[start:start + visible]:
                print(calendar_row(event).rstrip())
        weather = screen.get("weather")
        if isinstance(weather, dict):
            print("WEATHER {} {}".format(weather.get("icon") or "unknown", _weather_text(weather) or "--C"))
        if screen.get("stale"):
            print("STALE")


def create(settings):
    return MatrixDisplay() if settings.DISPLAY_BACKEND == "matrix" else FixtureDisplay()
