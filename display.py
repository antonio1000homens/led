"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

import time

import board

from formatting import (
    AGENDA_TITLE_X,
    AGENDA_VISIBLE_ROWS,
    QUEUE_VISIBLE_ROWS,
    agenda_scroll_state,
    agenda_title_marquee_x,
    calendar_due_text,
    todoist_due_label,
    calendar_row_parts,
    calendar_row_text,
    calling_marquee_x,
    calling_text,
    departure_scroll_state,
    ordinal_label,
    format_row,
    queue_scroll_state,
    row_slide_phase,
    service_status_text,
)


DISPLAY_WIDTH = 256
CLOCK_X = 226
HEADER_SLOT_X = 224
STALE_X = 190
QUEUE_FIRST_Y = 11
QUEUE_ROW_HEIGHT = 8
AGENDA_FIRST_Y = 11
AGENDA_ROW_HEIGHT = 8
WEATHER_ICON_WIDTH = 7
WEATHER_FONT_WIDTH = 6
WEATHER_GAP = 1
HEADER_GAP = 4
HEADER_HOLD_SECONDS = 4.0
HEADER_SLIDE_SECONDS = 0.6
HEADER_SLOT_WIDTH = DISPLAY_WIDTH - HEADER_SLOT_X
CALLING_SCROLL_SPEED = 30.0
CALLING_SCROLL_GAP = 28
MIN_CALLING_SCROLL_SPEED = 10.0
MAX_CALLING_SCROLL_SPEED = 80.0
MIN_CALLING_SCROLL_GAP = 8
MAX_CALLING_SCROLL_GAP = 80
RAIL_ORDINAL_X = 0
RAIL_TIME_X = 24
RAIL_DESTINATION_X = 60
RAIL_PLATFORM_X = 132
RAIL_PLATFORM_WIDTH = 3 * WEATHER_FONT_WIDTH

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
    return str(value or "")[:max(0, int(width or 0))]


def _queue_parts(ride):
    state = "{}m".format(ride.get("wait_minutes", 0)) if ride.get("open") else "CLOSED"
    return str(ride.get("name") or "Unknown"), state


def _queue_row(ride):
    name, state = _queue_parts(ride)
    return (_clip(name, 24).ljust(24) + state.rjust(8))[:32]


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


def _header_content_right(screen):
    return max(0, (STALE_X if screen.get("stale") else HEADER_SLOT_X) - HEADER_GAP)


def _right_aligned_x(text, right_edge):
    return max(0, int(right_edge) - len(str(text or "")) * WEATHER_FONT_WIDTH)


def _left_text(text, right_edge):
    return _clip(text, max(0, int(right_edge) // WEATHER_FONT_WIDTH))


def _fit_text_pixels(text, width):
    return _clip(text, max(0, int(width) // WEATHER_FONT_WIDTH))


def _bounded_number(value, default, minimum, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)
    return min(float(maximum), max(float(minimum), number))


def _station_scroll_settings(screen):
    speed = _bounded_number(
        screen.get("station_scroll_speed"),
        CALLING_SCROLL_SPEED,
        MIN_CALLING_SCROLL_SPEED,
        MAX_CALLING_SCROLL_SPEED,
    )
    return speed, CALLING_SCROLL_GAP


def _weather_group_layout(weather, offset=0):
    text = _weather_text(weather) or "--C"
    width = WEATHER_ICON_WIDTH + WEATHER_GAP + len(text) * WEATHER_FONT_WIDTH
    group_x = max(0, DISPLAY_WIDTH - width) + int(offset)
    return text, group_x, group_x + WEATHER_ICON_WIDTH + WEATHER_GAP


def _header_item_state(phase, weather):
    """Return (item, x-offset) for the clock/weather top-right carousel."""
    if not isinstance(weather, dict):
        return "clock", 0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0
    segment = HEADER_HOLD_SECONDS + HEADER_SLIDE_SECONDS
    within = phase % (segment * 2)
    if within < HEADER_HOLD_SECONDS:
        return "clock", 0
    if within < segment:
        progress = (within - HEADER_HOLD_SECONDS) / HEADER_SLIDE_SECONDS
        return "weather", int((1.0 - progress) * HEADER_SLOT_WIDTH)
    within -= segment
    if within < HEADER_HOLD_SECONDS:
        return "weather", 0
    progress = (within - HEADER_HOLD_SECONDS) / HEADER_SLIDE_SECONDS
    return "clock", int((1.0 - progress) * HEADER_SLOT_WIDTH)


def _rail_columns(service, ordinal=1):
    return (
        ordinal_label(ordinal),
        _clip(service.get("time", "--:--"), 5),
        str(service.get("destination") or "Unknown"),
        ("P" + str(service.get("platform", "-")))[:3],
        service_status_text(service),
    )


def _rgb_tuple(color):
    return ((color >> 16) & 0xFF, (color >> 8) & 0xFF, color & 0xFF)


def _agenda_state(screen, phase):
    events = screen.get("events") or []
    visible = max(1, int(screen.get("viewport_size") or AGENDA_VISIBLE_ROWS))
    page_seconds = screen.get("page_seconds") or 5
    start, progress = agenda_scroll_state(phase, len(events), page_seconds, visible)
    return events, visible, start, progress


def _calendar_due_layout(screen, clock_date, clock_time):
    """Keep the legacy header countdown for non-Todoist calendar feeds."""
    if screen.get("kind") != "calendar_agenda" or screen.get("source") == "todoist":
        return "", 0
    events = screen.get("events") or []
    if not events:
        return "", 0
    text = calendar_due_text(events[0], clock_date, clock_time)
    if not text:
        return "", 0
    right_edge = (STALE_X if screen.get("stale") else HEADER_SLOT_X) - HEADER_GAP
    return text, max(0, right_edge - len(text) * WEATHER_FONT_WIDTH)


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
        group.append(self.label_type(self.font, text=str(text), color=color, x=int(x), y=int(y)))

    def _mask(self, group, x, y, width, height=8):
        import displayio

        width = max(1, int(width))
        height = max(1, int(height))
        bitmap = displayio.Bitmap(width, height, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0x000000
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=int(x), y=int(y)))

    def _header_mask(self, group):
        self._mask(group, 0, 0, DISPLAY_WIDTH, 8)

    def _rail_service(self, group, service, color, x_offset, y, right_edge, ordinal=1):
        ordinal_text, time_text, destination, platform, status = _rail_columns(service, ordinal)
        status_x = _right_aligned_x(status, right_edge) if status else int(right_edge)
        platform_width = min(RAIL_PLATFORM_WIDTH, len(platform) * WEATHER_FONT_WIDTH)
        platform_x = RAIL_PLATFORM_X
        if status and status_x < platform_x + platform_width + HEADER_GAP:
            platform_x = max(RAIL_DESTINATION_X, status_x - platform_width - HEADER_GAP)
        destination_width = max(0, platform_x - HEADER_GAP - RAIL_DESTINATION_X)
        self._label(group, ordinal_text, color, RAIL_ORDINAL_X + x_offset, y)
        self._label(group, time_text, color, RAIL_TIME_X + x_offset, y)
        self._label(group, _fit_text_pixels(destination, destination_width), color, RAIL_DESTINATION_X + x_offset, y)
        self._label(group, platform, color, platform_x + x_offset, y)
        if status:
            self._label(group, status, color, status_x + x_offset, y)

    def _rail(self, group, screen, phase):
        services = screen.get("services") or []
        primary = services[0] if services else {"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting"}
        rail_right_edge = _header_content_right(screen)
        primary_slide = row_slide_phase(phase, 0)
        primary_x = -int((1 - primary_slide) * 220)
        primary_color = 0xFF3300 if primary.get("cancelled") and int(phase * 2) % 2 else 0xFFFFFF
        self._rail_service(group, primary, primary_color, primary_x, 3, rail_right_edge, 1)

        calling = calling_text(primary)
        scroll_speed, scroll_gap = _station_scroll_settings(screen)
        calling_x = calling_marquee_x(
            calling,
            phase,
            display_width=DISPLAY_WIDTH,
            font_width=WEATHER_FONT_WIDTH,
            speed=scroll_speed,
            gap=scroll_gap,
        )
        if calling_x is not None:
            self._label(group, calling, 0xFFAA00, calling_x, 10)

        upcoming = services[1:]
        if not upcoming:
            self._label(group, "No upcoming services", 0xFFFFFF, 0, 17)
        start, progress, reset_progress = departure_scroll_state(
            phase, len(upcoming), screen.get("upcoming_train_pause_seconds")
        )
        if reset_progress > 0:
            for slot in range(min(2, len(upcoming))):
                service = upcoming[slot]
                entry = max(0.0, min(1.0, (reset_progress - slot * 0.15) / 0.4))
                x = -int((1.0 - entry) * 220)
                color = 0xFF3300 if service.get("cancelled") and int(phase * 2) % 2 else 0xFFFFFF
                self._rail_service(group, service, color, x, 17 + slot * 8, rail_right_edge, slot + 2)
        else:
            for slot in range(3 if progress > 0 else 2):
                index = start + slot
                if index >= len(upcoming):
                    break
                service = upcoming[index]
                color = 0xFF3300 if service.get("cancelled") and int(phase * 2) % 2 else 0xFFFFFF
                y = 17 + slot * 8 - int(progress * 8)
                self._rail_service(group, service, color, 0, y, rail_right_edge, index + 2)

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
                name, state = _queue_parts(ride)
                state_x = _right_aligned_x(state, DISPLAY_WIDTH)
                y = QUEUE_FIRST_Y + slot * QUEUE_ROW_HEIGHT - y_offset
                color = 0xFFFFFF if ride.get("open") else 0xFF3300
                self._label(group, _left_text(name, max(0, state_x - HEADER_GAP)), color, 0, y)
                self._label(group, state, color, state_x, y)
        self._header_mask(group)
        self._label(group, _clip(screen.get("title") or "THORPE PARK", 30), 0xFFAA00, 0, 3)

    def _calendar(self, group, screen, phase, clock_date=""):
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
                event = events[event_index]
                when, title = calendar_row_parts(event)
                y = AGENDA_FIRST_Y + slot * AGENDA_ROW_HEIGHT - y_offset
                due = todoist_due_label(event, clock_date) if screen.get("source") == "todoist" else ""
                if due:
                    due_x = _right_aligned_x(due, DISPLAY_WIDTH)
                    title_width = max(0, due_x - HEADER_GAP - AGENDA_TITLE_X)
                    self._label(group, _fit_text_pixels(title, title_width), 0xFFFFFF, AGENDA_TITLE_X, y)
                else:
                    self._label(group, title, 0xFFFFFF, agenda_title_marquee_x(title, phase), y)
                self._mask(group, 0, y - 3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)
                self._label(group, when, 0xFFFFFF, 0, y)
                if due:
                    due_progress = row_slide_phase(phase, slot)
                    due_offset = int((1.0 - due_progress) * DISPLAY_WIDTH)
                    self._label(group, due, 0xFFFFFF, due_x + due_offset, y)
        self._header_mask(group)
        self._label(group, _clip(screen.get("title") or "UPCOMING", 30), 0xFFAA00, 0, 3)

    def _header_weather(self, group, weather, offset=0):
        if not isinstance(weather, dict):
            return
        import displayio

        text, icon_x, text_x = _weather_group_layout(weather, offset)
        icon_name, rows = _weather_icon(weather)
        stale = bool(weather.get("stale"))
        bitmap = displayio.Bitmap(WEATHER_ICON_WIDTH, 8, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = _weather_rgb(icon_name, stale)
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    bitmap[x, y] = 1
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=icon_x, y=0))
        self._label(group, text, 0xAAAAAA if stale else 0xFFFFFF, text_x, 3)

    def show(self, screen, clock_time="--:--", clock_date="", phase=2):
        import displayio

        group = displayio.Group()
        kind = screen.get("kind")
        if kind == "rail_combined":
            self._rail(group, screen, phase)
        elif kind == "theme_park_queues":
            self._queues(group, screen, phase)
        elif kind == "calendar_agenda":
            self._calendar(group, screen, phase, clock_date)
        else:
            self._label(group, _clip(screen.get("title") or "Display unavailable", 30), 0xFFFFFF, 0, 3)
        due_text, due_x = _calendar_due_layout(screen, clock_date, clock_time)
        if due_text:
            self._label(group, due_text, 0xFFFFFF, due_x, 3)
        if screen.get("stale"):
            self._label(group, "STALE", 0xFF3300, STALE_X, 3)
        self._mask(group, HEADER_SLOT_X, 0, HEADER_SLOT_WIDTH, 8)
        item, offset = _header_item_state(time.monotonic(), screen.get("weather"))
        if item == "weather":
            self._header_weather(group, screen.get("weather"), offset)
        else:
            self._label(group, clock_time, 0xFFAA00, CLOCK_X + offset, 3)
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
        x = int(x)
        y = int(y)
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

    def _clear_rect(self, start_x, start_y, end_x, end_y):
        if self.pixels is None:
            return
        for y in range(max(0, int(start_y)), min(32, int(end_y))):
            for x in range(max(0, int(start_x)), min(DISPLAY_WIDTH, int(end_x))):
                self._pixel(x, y, (0, 0, 0))

    def _clear_rows(self, start_y, end_y):
        self._clear_rect(0, start_y, DISPLAY_WIDTH, end_y)

    def _rail_service(self, service, color, x_offset, y, right_edge, ordinal=1):
        ordinal_text, time_text, destination, platform, status = _rail_columns(service, ordinal)
        status_x = _right_aligned_x(status, right_edge) if status else int(right_edge)
        platform_width = min(RAIL_PLATFORM_WIDTH, len(platform) * WEATHER_FONT_WIDTH)
        platform_x = RAIL_PLATFORM_X
        if status and status_x < platform_x + platform_width + HEADER_GAP:
            platform_x = max(RAIL_DESTINATION_X, status_x - platform_width - HEADER_GAP)
        destination_width = max(0, platform_x - HEADER_GAP - RAIL_DESTINATION_X)
        self._text(ordinal_text, RAIL_ORDINAL_X + x_offset, y, color)
        self._text(time_text, RAIL_TIME_X + x_offset, y, color)
        self._text(_fit_text_pixels(destination, destination_width), RAIL_DESTINATION_X + x_offset, y, color)
        self._text(platform, platform_x + x_offset, y, color)
        if status:
            self._text(status, status_x + x_offset, y, color)

    def _draw_screen(self, screen, phase, clock_date=""):
        kind = screen.get("kind")
        if kind == "rail_combined":
            services = screen.get("services") or []
            primary = services[0] if services else {"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting"}
            rail_right_edge = _header_content_right(screen)
            primary_slide = row_slide_phase(phase, 0)
            primary_x = -int((1 - primary_slide) * 220)
            primary_color = (255, 20, 0) if primary.get("cancelled") and int(phase * 2) % 2 else (255, 255, 255)
            self._rail_service(primary, primary_color, primary_x, 0, rail_right_edge, 1)
            text = calling_text(primary)
            scroll_speed, scroll_gap = _station_scroll_settings(screen)
            calling_x = calling_marquee_x(
                text,
                phase,
                display_width=DISPLAY_WIDTH,
                font_width=WEATHER_FONT_WIDTH,
                speed=scroll_speed,
                gap=scroll_gap,
            )
            if calling_x is not None:
                self._text(text, calling_x, 8, (255, 100, 0))
            upcoming = services[1:]
            if not upcoming:
                self._text("No upcoming services", 0, 16, (255, 255, 255))
            start, progress, reset_progress = departure_scroll_state(
                phase, len(upcoming), screen.get("upcoming_train_pause_seconds")
            )
            if reset_progress > 0:
                for slot in range(min(2, len(upcoming))):
                    service = upcoming[slot]
                    entry = max(0.0, min(1.0, (reset_progress - slot * 0.15) / 0.4))
                    x = -int((1.0 - entry) * 220)
                    color = (255, 20, 0) if service.get("cancelled") and int(phase * 2) % 2 else (255, 255, 255)
                    self._rail_service(service, color, x, 16 + slot * 8, rail_right_edge, slot + 2)
            else:
                for slot in range(3 if progress > 0 else 2):
                    index = start + slot
                    if index >= len(upcoming):
                        break
                    service = upcoming[index]
                    color = (255, 20, 0) if service.get("cancelled") and int(phase * 2) % 2 else (255, 255, 255)
                    y = 16 + slot * 8 - int(progress * 8)
                    self._rail_service(service, color, 0, y, rail_right_edge, index + 2)
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
                    name, state = _queue_parts(ride)
                    state_x = _right_aligned_x(state, DISPLAY_WIDTH)
                    y = 8 + slot * QUEUE_ROW_HEIGHT - y_offset
                    color = (255, 255, 255) if ride.get("open") else (255, 20, 0)
                    self._text(_left_text(name, max(0, state_x - HEADER_GAP)), 0, y, color)
                    self._text(state, state_x, y, color)
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
                    when, title = calendar_row_parts(events[event_index])
                    y = 8 + slot * AGENDA_ROW_HEIGHT - y_offset
                    due = todoist_due_label(events[event_index], clock_date) if screen.get("source") == "todoist" else ""
                    if due:
                        due_x = _right_aligned_x(due, DISPLAY_WIDTH)
                        title_width = max(0, due_x - HEADER_GAP - AGENDA_TITLE_X)
                        self._text(_fit_text_pixels(title, title_width), AGENDA_TITLE_X, y, (255, 255, 255))
                    else:
                        self._text(title, agenda_title_marquee_x(title, phase), y, (255, 255, 255))
                    self._clear_rect(0, y, AGENDA_TITLE_X, y + AGENDA_ROW_HEIGHT)
                    self._text(when, 0, y, (255, 255, 255))
                    if due:
                        progress = row_slide_phase(phase, slot)
                        due_offset = int((1.0 - progress) * DISPLAY_WIDTH)
                        self._text(due, due_x + due_offset, y, (255, 255, 255))
            self._clear_rows(0, 8)
            self._text(_clip(screen.get("title") or "UPCOMING", 30), 0, 0, (255, 100, 0))
        else:
            self._text(_clip(screen.get("title") or "Display unavailable", 30), 0, 0, (255, 255, 255))

    def _header_weather(self, weather, offset=0):
        if not isinstance(weather, dict) or self.pixels is None:
            return
        text, icon_x, text_x = _weather_group_layout(weather, offset)
        icon_name, rows = _weather_icon(weather)
        stale = bool(weather.get("stale"))
        color = _rgb_tuple(_weather_rgb(icon_name, stale))
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                if pixel == "#":
                    self._pixel(icon_x + x, y, color)
        self._text(text, text_x, 0, (170, 170, 170) if stale else (255, 255, 255))

    def show(self, screen, clock_time="--:--", clock_date="", phase=2):
        due_text, due_x = _calendar_due_layout(screen, clock_date, clock_time)
        if self.pixels is not None:
            self.pixels.fill((0, 0, 0))
            self._draw_screen(screen, phase, clock_date)
            if due_text:
                self._text(due_text, due_x, 0, (255, 255, 255))
            if screen.get("stale"):
                self._text("STALE", STALE_X, 0, (255, 20, 0))
            self._clear_rect(HEADER_SLOT_X, 0, DISPLAY_WIDTH, 8)
            item, offset = _header_item_state(time.monotonic(), screen.get("weather"))
            if item == "weather":
                self._header_weather(screen.get("weather"), offset)
            else:
                self._text(clock_time, CLOCK_X + offset, 0, (255, 100, 0))
            self.pixels.show()

        print("\n[{}] {}".format(clock_time, screen.get("title") or screen.get("kind") or "screen"))
        if due_text:
            print(due_text)
        kind = screen.get("kind")
        if kind == "rail_combined":
            services = screen.get("services") or []
            if services:
                print(format_row(services[0]).rstrip())
                print(calling_text(services[0]))
                start, _, reset_progress = departure_scroll_state(
                    phase, len(services[1:]), screen.get("upcoming_train_pause_seconds")
                )
                if reset_progress > 0:
                    start = 0
                for index, service in enumerate(services[1 + start:3 + start], start=start + 2):
                    print("{} {}".format(ordinal_label(index), format_row(service).rstrip()))
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
                print(calendar_row_text(event).rstrip())
        weather = screen.get("weather")
        if isinstance(weather, dict):
            print("WEATHER {} {}".format(weather.get("icon") or "unknown", _weather_text(weather) or "--C"))
        if screen.get("stale"):
            print("STALE")


def create(settings):
    return MatrixDisplay() if settings.DISPLAY_BACKEND == "matrix" else FixtureDisplay()
