"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

import time

import board

from matrix_config import (
    MATRIX_ANIMATION_PROFILE,
    MATRIX_ANIMATION_PROFILES,
    MATRIX_BIT_DEPTH,
    MATRIX_EXPERIMENT_PRESET,
    CALLING_SCROLL_SPEED_OVERRIDE,
    MATRIX_PRESENTATION_MODE,
    MATRIX_RAIL_ROWS_SCROLL,
    MATRIX_REFRESH_FPS,
    MATRIX_STATS_INTERVAL_SECONDS,
    TODOIST_MARQUEE_PAUSE_SECONDS,
    TODOIST_MARQUEE_SPEED,
)

from brightness import BrightnessState, pixel_is_blocked

from formatting import (
    AGENDA_SLIDE_SECONDS,
    AGENDA_TITLE_X,
    AGENDA_VISIBLE_ROWS,
    QUEUE_VISIBLE_ROWS,
    agenda_scroll_state,
    agenda_marquee_x,
    agenda_title_marquee_x,
    calendar_due_text,
    todoist_due_label,
    calendar_row_parts,
    calendar_row_text,
    CALLING_LABEL,
    RAIL_MARQUEE_DELAY_SECONDS,
    CALLING_MARQUEE_PAUSE_SECONDS,
    calling_marquee_x,
    calling_color_segments,
    calling_text,
    rail_calling_timing,
    departure_scroll_state,
    DEPARTURE_SLIDE_SECONDS,
    DEPARTURE_RESET_GAP_SECONDS,
    DEPARTURE_RESET_SLIDE_SECONDS,
    RAIL_ROW_Y,
    RAIL_CALLING_SECONDS,
    RAIL_SUMMARY_SECONDS,
    rail_marquee_elapsed,
    rail_phase,
    rail_rows,
    ordinal_label,
    format_row,
    queue_scroll_state,
    row_slide_phase,
    service_status_text,
)


DISPLAY_WIDTH = 256
STEAM_TRAIN_WIDTH = 52
STEAM_TRAIN_HEIGHT = 26
STEAM_TRAIN_TEXT_GAP = 8
CLOCK_X = 226
HEADER_SLOT_X = 224
STALE_X = 190
QUEUE_FIRST_Y = 11
QUEUE_ROW_HEIGHT = 8
# The font label coordinate is a baseline. Start the three agenda rows lower
# so the final row uses the bottom of the 32px panel instead of leaving a
# visible unused band below it.
AGENDA_FIRST_Y = 11
AGENDA_ROW_HEIGHT = 8
WEATHER_ICON_WIDTH = 7
WEEKLY_WEATHER_ICON_SCALE = 2
TODAY_WEATHER_ICON_SCALE = 2
SUN_WEATHER_ICON_SCALE = 2
# MatrixDisplay labels use font baselines, while the fixture renderer uses
# top-left pixel coordinates. Keep fullscreen weather headers clear of the
# panel edge and align the forecast rows below them.
WEATHER_HEADING_BASELINE_Y = 9
WEATHER_HEADING_PIXEL_Y = 2
WEEKLY_WEATHER_ICON_Y = 10
WEEKLY_WEATHER_TEMPERATURE_Y = 25
TODAY_WEATHER_ICON_Y = 10
TODAY_WEATHER_TEMPERATURE_Y = 26
WEATHER_FULLSCREEN_KINDS = ("weather_weekly", "weather_today", "weather_sun")
WEEKLY_WEATHER_TEXT_SCALE = 1
WEEKLY_WEATHER_GLYPH_WIDTH = 3
WEEKLY_WEATHER_GLYPHS = {
    "0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7),
    "2": (7, 1, 7, 4, 7), "3": (7, 1, 7, 1, 7),
    "4": (5, 5, 7, 1, 1), "5": (7, 4, 7, 1, 7),
    "6": (7, 4, 7, 5, 7), "7": (7, 1, 2, 2, 2),
    "8": (7, 5, 7, 5, 7), "9": (7, 5, 7, 1, 7),
    "C": (3, 4, 4, 4, 3), "-": (0, 0, 7, 0, 0),
}
WEATHER_FONT_WIDTH = 5
WEATHER_GAP = 1
HEADER_GAP = 4
HEADER_HOLD_SECONDS = 7.0
HEADER_SLOT_WIDTH = DISPLAY_WIDTH - HEADER_SLOT_X
CALLING_SCROLL_SPEED = 20.0
CALLING_SCROLL_GAP = 28
MIN_CALLING_SCROLL_SPEED = 10.0
MAX_CALLING_SCROLL_SPEED = 80.0
MIN_CALLING_SCROLL_GAP = 8
MAX_CALLING_SCROLL_GAP = 80
RAIL_ORDINAL_X = 0
RAIL_TIME_X = 24
RAIL_DESTINATION_X = 60
RAIL_PLATFORM_X = 152
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
    name = _clip(name, 24)
    name = name + (" " * max(0, 24 - len(name)))
    state = (" " * max(0, 8 - len(state))) + state
    return (name + state)[-32:]


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


def _rail_weather_key(weather):
    """Return only weather fields that affect visible rail pixels."""
    if not isinstance(weather, dict):
        return None
    icon_name, _ = _weather_icon(weather)
    return (_weather_text(weather), icon_name, bool(weather.get("stale")))


def _next_periodic_boundary(elapsed, boundaries, cycle):
    """Seconds to the next state edge in a repeating animation cycle."""
    cycle = max(0.001, float(cycle))
    within = max(0.0, float(elapsed or 0)) % cycle
    candidates = []
    for boundary in boundaries:
        edge = float(boundary) % cycle
        delta = edge - within
        if delta <= 1e-6:
            delta += cycle
        candidates.append(delta)
    return min(candidates) if candidates else cycle


def _header_content_right(screen):
    return max(0, (STALE_X if screen.get("stale") else HEADER_SLOT_X) - HEADER_GAP)


def _right_aligned_x(text, right_edge):
    return max(0, int(right_edge) - len(str(text or "")) * WEATHER_FONT_WIDTH)


def _left_text(text, right_edge):
    return _clip(text, max(0, int(right_edge) // WEATHER_FONT_WIDTH))


def _fit_text_pixels(text, width):
    return _clip(text, max(0, int(width) // WEATHER_FONT_WIDTH))


def _weather_column_bounds(index, display_width=DISPLAY_WIDTH):
    """Return integer seven-column bounds without accumulating rounding error."""
    left = (int(index) * int(display_width)) // 7
    right = ((int(index) + 1) * int(display_width)) // 7
    return left, right


def _weekly_temperature_text(value):
    try:
        rounded = int(round(float(value)))
    except (TypeError, ValueError):
        return "--C"
    return "{}C".format(rounded)


def _weekly_weather_layout(days, display_width=DISPLAY_WIDTH):
    """Build renderer-neutral positions for up to seven forecast days."""
    if not isinstance(days, (list, tuple)):
        return []
    layout = []
    for index, raw_day in enumerate(days[:7]):
        day = raw_day if isinstance(raw_day, dict) else {}
        left, right = _weather_column_bounds(index, display_width)
        width = right - left
        weekday = _fit_text_pixels(str(day.get("weekday") or "").upper()[:3], width)
        maximum = _weekly_temperature_text(day.get("temperature_max_c"))
        icon_width = WEATHER_ICON_WIDTH * WEEKLY_WEATHER_ICON_SCALE
        maximum_width = len(maximum) * (WEEKLY_WEATHER_GLYPH_WIDTH + 1) * WEEKLY_WEATHER_TEXT_SCALE
        icon_name, rows = _weather_icon(day)

        def centered_x(text, pixel_width):
            return left + max(0, (width - pixel_width) // 2)

        layout.append({
            "index": index,
            "left": left,
            "right": right,
            "weekday": weekday,
            "weekday_x": centered_x(weekday, len(weekday) * WEATHER_FONT_WIDTH),
            "icon_name": icon_name,
            "icon_rows": rows,
            "icon_x": centered_x("", icon_width),
            "max_text": maximum,
            "max_x": left + max(0, (width - maximum_width) // 2),
            "icon_width": icon_width,
        })
    return layout


def _today_weather_layout(blocks, display_width=DISPLAY_WIDTH):
    """Build six fixed four-hour Weather columns for today."""
    if not isinstance(blocks, (list, tuple)):
        return []
    layout = []
    for index, raw_block in enumerate(blocks[:6]):
        block = raw_block if isinstance(raw_block, dict) else {}
        left = (index * int(display_width)) // 6
        right = ((index + 1) * int(display_width)) // 6
        width = right - left
        label = str(block.get("label") or "")[:5]
        temperature = _weekly_temperature_text(block.get("temperature_c"))
        icon_name, rows = _weather_icon(block)
        icon_width = WEATHER_ICON_WIDTH * TODAY_WEATHER_ICON_SCALE
        temp_width = len(temperature) * (WEEKLY_WEATHER_GLYPH_WIDTH + 1)
        layout.append({
            "left": left,
            "right": right,
            "label": label,
            "label_x": left + max(0, (width - len(label) * WEATHER_FONT_WIDTH) // 2),
            "icon_name": icon_name,
            "icon_rows": rows,
            "icon_x": left + max(0, (width - icon_width) // 2),
            "icon_width": icon_width,
            "temp_text": temperature,
            "temp_x": left + max(0, (width - temp_width) // 2),
        })
    return layout


def _calling_segments(text, x, gap):
    """Return clipped station-label segments that cannot overwrite the prefix."""
    text = str(text or "")
    stations = text[len(CALLING_LABEL):] if text.startswith(CALLING_LABEL) else text
    station_width = len(stations) * WEATHER_FONT_WIDTH
    prefix_width = len(CALLING_LABEL) * WEATHER_FONT_WIDTH
    segments = []
    for candidate_x in (int(x), int(x) + station_width + int(gap)):
        if candidate_x >= DISPLAY_WIDTH or candidate_x + station_width <= prefix_width:
            continue
        drop = max(0, (prefix_width - candidate_x + WEATHER_FONT_WIDTH - 1) // WEATHER_FONT_WIDTH)
        visible_x = candidate_x + drop * WEATHER_FONT_WIDTH
        visible = stations[drop:]
        visible = visible[:max(0, (DISPLAY_WIDTH - visible_x) // WEATHER_FONT_WIDTH)]
        if visible:
            segments.append((visible_x, visible))
    return segments


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
    gap = int(round(_bounded_number(
        screen.get("station_list_spacing"),
        CALLING_SCROLL_GAP,
        MIN_CALLING_SCROLL_GAP,
        MAX_CALLING_SCROLL_GAP,
    )))
    return speed, gap


def _weather_group_layout(weather, offset=0):
    text = _weather_text(weather) or "--C"
    width = WEATHER_ICON_WIDTH + WEATHER_GAP + len(text) * WEATHER_FONT_WIDTH
    group_x = max(0, DISPLAY_WIDTH - width) + int(offset)
    return text, group_x, group_x + WEATHER_ICON_WIDTH + WEATHER_GAP


def _header_item_state(phase, weather):
    """Return the stationary clock or weather item for the top-right slot."""
    if not isinstance(weather, dict):
        return "clock", 0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0
    within = phase % (HEADER_HOLD_SECONDS * 2)
    return ("clock", 0) if within < HEADER_HOLD_SECONDS else ("weather", 0)


def _header_slide_active(phase, weather):
    """The clock/weather slot switches at rest and has no moving interval."""
    return False


def _header_next_boundary_seconds(phase, weather):
    if not isinstance(weather, dict):
        return 60.0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0
    cycle = HEADER_HOLD_SECONDS * 2
    within = phase % cycle
    for boundary in (HEADER_HOLD_SECONDS, cycle):
        if boundary > within + 1e-9:
            return max(0.05, boundary - within)
    return max(0.05, cycle - within)


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
    def __init__(self, brightness_percent=100):
        import displayio
        import framebufferio
        import rgbmatrix
        from adafruit_bitmap_font import bitmap_font
        from adafruit_display_text import label

        displayio.release_displays()
        matrix = rgbmatrix.RGBMatrix(
            width=DISPLAY_WIDTH,
            height=32,
            # Four chained 64x32 panels need refresh headroom. Two bits per
            # channel retain the board's text/status colours while matching
            # the MatrixPortal helper's flicker-resistant default.
            bit_depth=MATRIX_BIT_DEPTH,
            doublebuffer=True,
            addr_pins=board.MTX_ADDRESS[:4],
            **board.MTX_COMMON,
        )
        # Keep scene construction identical while issue #70 varies only the
        # framebuffer presentation strategy.
        if MATRIX_PRESENTATION_MODE not in ("target_fps", "immediate", "auto_refresh"):
            raise ValueError(
                "MATRIX_PRESENTATION_MODE must be target_fps, immediate, or auto_refresh"
            )
        self.presentation_mode = MATRIX_PRESENTATION_MODE
        self.display = framebufferio.FramebufferDisplay(
            matrix,
            auto_refresh=self.presentation_mode == "auto_refresh",
        )
        self.display.root_group = displayio.Group()
        self._refresh_misses = 0

        self._brightness = BrightnessState(brightness_percent)
        self._brightness_bitmap = displayio.Bitmap(DISPLAY_WIDTH, 32, 2)
        self._brightness_palette = displayio.Palette(2)
        self._brightness_palette[0] = 0x000000
        self._brightness_palette.make_transparent(0)
        self._brightness_palette[1] = 0x000000
        self._brightness_overlay = displayio.TileGrid(
            self._brightness_bitmap,
            pixel_shader=self._brightness_palette,
        )
        self._brightness_overlay_parent = None
        self._render_brightness_overlay()

        self.label_type = label.Label
        self.font = bitmap_font.load_font("/font5x7.pcf")

        # Low-overhead aggregate metrics for the physical-board comparison.
        now = time.monotonic()
        self._stats_started = now
        self._stats_last_report = now
        self._stats_heap_start = self._heap_free()
        self._stats_changes = 0
        self._stats_refresh_attempts = 0
        self._stats_refresh_successes = 0
        self._stats_refresh_failures = 0
        self._stats_last_success = None
        self._stats_interval_min = None
        self._stats_interval_max = None
        self._stats_interval_total = 0.0
        self._stats_interval_count = 0
        self._stats_animation_ticks = 0
        self._stats_todoist_ticks = 0
        self._stats_todoist_changed = 0
        self._stats_rail_ticks = 0
        self._stats_rail_changed = 0
        self._stats_update_total = 0.0
        self._stats_update_max = 0.0
        self._stats_refresh_total = 0.0
        self._stats_refresh_max = 0.0
        self._stats_rail_update_heap_gain_max = 0
        self._stats_rail_refresh_heap_gain_max = 0
        self._stats_fetch_overlap = 0
        self._stats_cadence_switches = 0
        self._stats_animation_classes = {
            name: {
                "ticks": 0,
                "changed": 0,
                "update_total": 0.0,
                "update_max": 0.0,
                "refresh_total": 0.0,
                "refresh_max": 0.0,
            }
            for name in (
                "todoist_marquee",
                "todoist_page_slide",
                "header_slide",
                "departures_calling",
            )
        }
        print(
            "MATRIX PRESENTATION preset={} animation_profile={} rail_rows_scroll={} mode={} target_fps={} marquee_px_s={} calling_px_s={} auto_refresh={}".format(
                MATRIX_EXPERIMENT_PRESET,
                MATRIX_ANIMATION_PROFILE,
                MATRIX_RAIL_ROWS_SCROLL,
                self.presentation_mode,
                MATRIX_REFRESH_FPS,
                TODOIST_MARQUEE_SPEED,
                CALLING_SCROLL_SPEED_OVERRIDE,
                self.display.auto_refresh,
            )
        )

        # Todoist is the only Matrix page that continuously animates while the
        # rest of the board is in static mode. Keep its display tree alive and
        # mutate group coordinates instead of rebuilding labels, bitmaps and
        # masks for every frame.
        self._todoist_group = None
        self._todoist_rows = []
        self._todoist_events = None
        self._todoist_clock_date = None
        self._todoist_title = None
        self._todoist_stale = None
        self._todoist_viewport_size = None
        self._todoist_page_step = 1
        self._todoist_page_seconds = None
        self._todoist_page_starts = ()
        self._todoist_page_durations = ()
        self._todoist_weather_icon = None
        self._todoist_weather_temp = None
        self._todoist_weather_stale = None
        self._todoist_clock_group = None
        self._todoist_clock_label = None
        self._todoist_weather_group = None

        # Departures use the same persistent-scene approach as Todoist.  Only
        # the calling-at labels move between frames; rebuilding the complete
        # four-panel scene is deliberately avoided.
        self._rail_scenes = {}
        self._rail_group = None
        self._rail_services = None
        self._rail_title = None
        self._rail_stale = None
        self._rail_weather = None
        self._rail_calling_labels = []
        self._rail_departure_rows = []
        self._rail_phase = None
        self._rail_clock_group = None
        self._rail_clock_label = None
        self._rail_weather_group = None

        # The departures intro is a full-screen persistent scene. The train,
        # wheels and trailing text are constructed once; animation only moves
        # the containing group horizontally.
        self._steam_train_group = None
        self._steam_train_motion_group = None
        self._steam_train_words = None
        self._steam_train_speed = None

    @property
    def brightness_percent(self):
        return self._brightness.percent

    def _render_brightness_overlay(self):
        percent = self._brightness.percent
        if percent >= 100:
            self._brightness_bitmap.fill(0)
            return
        for y in range(32):
            for x in range(DISPLAY_WIDTH):
                self._brightness_bitmap[x, y] = 1 if pixel_is_blocked(x, y, percent) else 0

    def _attach_brightness_overlay(self, group, bring_to_front=False):
        parent = self._brightness_overlay_parent
        if parent is group:
            if bring_to_front:
                try:
                    group.remove(self._brightness_overlay)
                except ValueError:
                    pass
                group.append(self._brightness_overlay)
            return

        if parent is not None:
            try:
                parent.remove(self._brightness_overlay)
            except ValueError:
                pass
        group.append(self._brightness_overlay)
        self._brightness_overlay_parent = group

    def adjust_brightness(self, direction):
        """Adjust apparent brightness without changing HUB75 scan timing."""
        percent, changed = self._brightness.adjust(direction)
        if not changed:
            return percent
        self._render_brightness_overlay()
        if self._brightness_overlay_parent is not None:
            self._refresh()
        print("BRIGHTNESS {}%".format(percent))
        return percent

    def _label(self, group, text, color, x, y):
        item = self.label_type(self.font, text=str(text), color=color, x=int(x), y=int(y))
        group.append(item)
        return item

    def _temperature_label(self, group, text, color, x, y):
        import displayio

        scale = WEEKLY_WEATHER_TEXT_SCALE
        bitmap = displayio.Bitmap(len(text) * (WEEKLY_WEATHER_GLYPH_WIDTH + 1) * scale, 5 * scale, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = color
        for index, char in enumerate(str(text)):
            rows = WEEKLY_WEATHER_GLYPHS.get(char, (0, 0, 0, 0, 0))
            for row_index, row_bits in enumerate(rows):
                for column in range(WEEKLY_WEATHER_GLYPH_WIDTH):
                    if row_bits & (1 << (WEEKLY_WEATHER_GLYPH_WIDTH - column - 1)):
                        for dx in range(scale):
                            for dy in range(scale):
                                bitmap[index * (WEEKLY_WEATHER_GLYPH_WIDTH + 1) * scale + column * scale + dx,
                                       row_index * scale + dy] = 1
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=int(x), y=int(y)))

    def _chunked_label_group(self, text, color, y, chunk_chars=24):
        """Build fixed text chunks so scrolling moves groups without reflowing labels."""
        import displayio

        group = displayio.Group()
        text = str(text or "")
        if not text:
            self._label(group, "", color, 0, y)
            return group
        for start in range(0, len(text), chunk_chars):
            self._label(
                group,
                text[start:start + chunk_chars],
                color,
                start * WEATHER_FONT_WIDTH,
                y,
            )
        return group

    def _calling_label_group(self, service, y, prepared_segments=None):
        import displayio

        group = displayio.Group()
        if prepared_segments:
            segments = [
                (
                    segment.get("text", ""),
                    0xFFFFFF if segment.get("role") == "station" else 0xFFAA00,
                )
                for segment in prepared_segments
                if isinstance(segment, dict)
            ]
        else:
            segments = calling_color_segments(service)
        if not segments:
            return group

        # Lightweight host fixtures use a label-only fake font. The real
        # MatrixPortal bitmap font exposes glyph metrics and takes the compact
        # single-bitmap path below.
        if not hasattr(self.font, "get_glyph"):
            cursor = 0
            for text, color in segments:
                self._label(group, text, color, cursor, y)
                cursor += len(text) * WEATHER_FONT_WIDTH
            return group

        characters = set()
        for text, _ in segments:
            for character in text:
                characters.add(ord(character))
        if hasattr(self.font, "load_glyphs"):
            self.font.load_glyphs(characters)

        ascent = getattr(self.font, "ascent", None)
        if ascent is None:
            ascent = self.font.get_bounding_box()[1]
        y_offset = ascent // 2
        glyphs = []
        cursor_x = 0
        min_x = 0
        max_x = 0
        min_y = 0
        max_y = 0
        for text, color in segments:
            color_index = 1 if color == 0xFFFFFF else 2
            for character in text:
                glyph = self.font.get_glyph(ord(character))
                if glyph is None:
                    continue
                glyph_x = cursor_x + glyph.dx
                glyph_y = -glyph.height - glyph.dy + y_offset
                glyphs.append((glyph, glyph_x, glyph_y, color_index))
                min_x = min(min_x, glyph_x)
                max_x = max(max_x, glyph_x + glyph.width)
                min_y = min(min_y, glyph_y)
                max_y = max(max_y, glyph_y + glyph.height)
                cursor_x += glyph.shift_x

        width = max(1, max(max_x, cursor_x) - min_x)
        height = max(1, max_y - min_y)
        bitmap = displayio.Bitmap(width, height, 3)
        palette = displayio.Palette(3)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = 0xFFFFFF
        palette[2] = 0xFFAA00
        for glyph, glyph_x, glyph_y, color_index in glyphs:
            for glyph_y_offset in range(glyph.height):
                for glyph_x_offset in range(glyph.width):
                    if glyph.bitmap[glyph_x_offset, glyph_y_offset]:
                        bitmap[
                            glyph_x + glyph_x_offset - min_x,
                            glyph_y + glyph_y_offset - min_y,
                        ] = color_index

        group.append(
            displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                x=min_x,
                y=y + min_y,
            )
        )
        return group

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

    def _heap_free(self):
        try:
            import gc
            return gc.mem_free() if hasattr(gc, "mem_free") else None
        except (ImportError, AttributeError):
            return None

    def _record_success_interval(self, now):
        if self._stats_last_success is not None:
            interval = max(0.0, now - self._stats_last_success)
            if self._stats_interval_min is None or interval < self._stats_interval_min:
                self._stats_interval_min = interval
            if self._stats_interval_max is None or interval > self._stats_interval_max:
                self._stats_interval_max = interval
            self._stats_interval_total += interval
            self._stats_interval_count += 1
        self._stats_last_success = now

    def _maybe_report_stats(self):
        now = time.monotonic()
        if now - self._stats_last_report < MATRIX_STATS_INTERVAL_SECONDS:
            return
        elapsed = max(0.001, now - self._stats_started)
        if self.presentation_mode == "auto_refresh":
            presented_fps = "n/a"
        else:
            presented_fps = "{:.2f}".format(self._stats_refresh_successes / elapsed)
        interval_avg = (
            self._stats_interval_total / self._stats_interval_count
            if self._stats_interval_count
            else None
        )
        print(
            "MATRIX STATS mode={} target_fps={} elapsed={:.1f} changes={} "
            "refresh_attempts={} refresh_successes={} refresh_failures={} "
            "presented_fps={} interval_min={} interval_max={} interval_avg={} "
            "heap_start={} heap_end={} animation_ticks={} todoist_ticks={} "
            "todoist_changed={} rail_ticks={} rail_changed={} "
            "update_avg={} update_max={} refresh_avg={} refresh_max={} "
            "fetch_overlap={} cadence_switches={} "
            "todoist_marquee_ticks={} todoist_marquee_changed={} "
                "todoist_page_slide_ticks={} todoist_page_slide_changed={} "
                "todoist_marquee_update_max={} todoist_marquee_refresh_max={} "
                "todoist_page_update_max={} todoist_page_refresh_max={} "
                "header_slide_ticks={} header_slide_changed={} "
                "header_slide_update_max={} header_slide_refresh_max={} "
                "departures_calling_ticks={} departures_calling_changed={} "
                "departures_calling_update_max={} departures_calling_refresh_max={} "
                "departures_update_heap_gain={} departures_refresh_heap_gain={}".format(
                self.presentation_mode,
                MATRIX_REFRESH_FPS,
                elapsed,
                self._stats_changes,
                self._stats_refresh_attempts,
                self._stats_refresh_successes,
                self._stats_refresh_failures,
                presented_fps,
                "{:.4f}".format(self._stats_interval_min)
                if self._stats_interval_min is not None
                else "n/a",
                "{:.4f}".format(self._stats_interval_max)
                if self._stats_interval_max is not None
                else "n/a",
                "{:.4f}".format(interval_avg) if interval_avg is not None else "n/a",
                self._stats_heap_start,
                self._heap_free(),
                self._stats_animation_ticks,
                self._stats_todoist_ticks,
                self._stats_todoist_changed,
                self._stats_rail_ticks,
                self._stats_rail_changed,
                "{:.4f}".format(self._stats_update_total / self._stats_animation_ticks)
                if self._stats_animation_ticks else "n/a",
                "{:.4f}".format(self._stats_update_max),
                "{:.4f}".format(self._stats_refresh_total / self._stats_refresh_successes)
                if self._stats_refresh_successes else "n/a",
                "{:.4f}".format(self._stats_refresh_max),
                self._stats_fetch_overlap,
                self._stats_cadence_switches,
                self._stats_animation_classes["todoist_marquee"]["ticks"],
                self._stats_animation_classes["todoist_marquee"]["changed"],
                self._stats_animation_classes["todoist_page_slide"]["ticks"],
                self._stats_animation_classes["todoist_page_slide"]["changed"],
                "{:.4f}".format(self._stats_animation_classes["todoist_marquee"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["todoist_marquee"]["refresh_max"]),
                "{:.4f}".format(self._stats_animation_classes["todoist_page_slide"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["todoist_page_slide"]["refresh_max"]),
                self._stats_animation_classes["header_slide"]["ticks"],
                self._stats_animation_classes["header_slide"]["changed"],
                "{:.4f}".format(self._stats_animation_classes["header_slide"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["header_slide"]["refresh_max"]),
                self._stats_animation_classes["departures_calling"]["ticks"],
                self._stats_animation_classes["departures_calling"]["changed"],
                "{:.4f}".format(self._stats_animation_classes["departures_calling"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["departures_calling"]["refresh_max"]),
                self._stats_rail_update_heap_gain_max,
                self._stats_rail_refresh_heap_gain_max,
            )
        )
        self._stats_last_report = now

    def note_fetch_overlap(self):
        """Record a blocking fetch that occurred while animation was active."""
        self._stats_fetch_overlap += 1

    def note_cadence_switch(self):
        self._stats_cadence_switches += 1

    def _animation_class(self, screen, phase):
        """Return the active animation class without changing its cadence."""
        if not isinstance(screen, dict):
            return None
        kind = screen.get("kind")
        if kind == "calendar_agenda" and screen.get("source") == "todoist":
            if self._todoist_rows and self._todoist_page_slide_active(phase):
                return "todoist_page_slide"
            if _header_slide_active(phase, screen.get("weather")):
                return "header_slide"
            if self._todoist_rows and self._todoist_titles_moving(phase):
                return "todoist_marquee"
            return None
        if kind == "steam_train_intro":
            return "queue_rows"
        if kind == "rail_combined":
            calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
            summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
            if _header_slide_active(phase, screen.get("weather")):
                return "header_slide"
            if self._departures_rows_moving(screen, phase, calling_seconds, summary_seconds):
                return "departures_calling"
            if self._departures_calling_moving(screen, phase, calling_seconds, summary_seconds):
                return "departures_calling"
        if kind == "theme_park_queues":
            parks = screen.get("parks") or (screen,)
            if screen.get("splash_enabled") or len(parks) > 1:
                return "queue_rows"
            for park in parks:
                if len(park.get("rides") or ()) > QUEUE_VISIBLE_ROWS:
                    return "queue_rows"
        return None

    def animation_cadence(self, screen, phase):
        """Return the desired update cadence for the active partial scene."""
        if MATRIX_ANIMATION_PROFILE == "baseline":
            return MATRIX_REFRESH_FPS
        animation_class = self._animation_class(screen, phase)
        if animation_class is None:
            return 0
        return MATRIX_ANIMATION_PROFILES[MATRIX_ANIMATION_PROFILE][animation_class]

    def animation_active(self, screen, phase):
        """Return whether the screen has pixels moving at this phase."""
        return self._animation_class(screen, phase) is not None

    def animation_sleep_seconds(self, screen, phase):
        """Return a conservative sleep until the next known animation boundary."""
        if not isinstance(screen, dict):
            return None
        kind = screen.get("kind")
        if kind == "calendar_agenda" and screen.get("source") == "todoist":
            if self._todoist_rows:
                try:
                    phase = max(0.0, float(phase or 0))
                except (TypeError, ValueError):
                    phase = 0.0
                if self._todoist_page_slide_active(phase):
                    return 0.0
                visible = self._todoist_viewport_size
                longest_scroll = 0.0
                for row in self._todoist_rows[:visible]:
                    longest_scroll = max(
                        longest_scroll,
                        self._todoist_title_scroll_seconds(row[2], row[3]),
                    )
                transition_at = self._todoist_page_transition_at(0)
                boundaries = []
                if phase < longest_scroll:
                    boundaries.append(longest_scroll - phase)
                if phase < transition_at:
                    boundaries.append(transition_at - phase)
                boundaries.append(_header_next_boundary_seconds(phase, screen.get("weather")))
                return max(0.05, min(boundaries))
        if kind == "rail_combined":
            calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
            summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
            boundaries = [_header_next_boundary_seconds(phase, screen.get("weather"))]
            try:
                value = max(0.0, float(phase or 0))
            except (TypeError, ValueError):
                value = 0.0
            cycle = summary_seconds + calling_seconds
            within = value % cycle
            if rail_phase(phase, summary_seconds, calling_seconds) == "summary":
                boundaries.append(summary_seconds - within)
            else:
                boundaries.append(cycle - within)
                calling_elapsed = rail_marquee_elapsed(phase, summary_seconds, calling_seconds)
                services = screen.get("services") or ()
                upcoming_count = max(0, len(services) - 1)
                pause = max(0.0, float(screen.get("upcoming_train_pause_seconds", 2) or 0))
                max_start = max(0, upcoming_count - 2)
                if max_start and MATRIX_RAIL_ROWS_SCROLL:
                    step = pause + DEPARTURE_SLIDE_SECONDS
                    normal = (max_start + 1) * step
                    row_cycle = normal + DEPARTURE_RESET_GAP_SECONDS + DEPARTURE_RESET_SLIDE_SECONDS
                    row_edges = [0.0, normal, normal + DEPARTURE_RESET_GAP_SECONDS,
                                 row_cycle]
                    for index in range(max_start + 1):
                        start = index * step + pause
                        row_edges.extend((start, start + DEPARTURE_SLIDE_SECONDS))
                    boundaries.append(_next_periodic_boundary(calling_elapsed, row_edges, row_cycle))
                if services:
                    speed, _ = _station_scroll_settings(screen)
                    prepared = screen.get("rail_presentation") or {}
                    travel = prepared.get("calling_travel_seconds", screen.get("_calling_travel_seconds"))
                    if travel is None:
                        travel = rail_calling_timing(
                            services, speed, font_width=WEATHER_FONT_WIDTH
                        )[0]
                    marquee_cycle = travel + CALLING_MARQUEE_PAUSE_SECONDS
                    boundaries.append(_next_periodic_boundary(
                        calling_elapsed, (0.0, travel, marquee_cycle), marquee_cycle
                    ))
            return max(0.05, min(boundaries))
        return _header_next_boundary_seconds(phase, screen.get("weather"))

    def _departures_calling_moving(self, screen, phase, calling_seconds=RAIL_CALLING_SECONDS,
                                   summary_seconds=RAIL_SUMMARY_SECONDS):
        if rail_phase(phase, summary_seconds, calling_seconds) != "calling":
            return False
        services = screen.get("services") or ()
        scroll_speed, _ = _station_scroll_settings(screen)
        for service_index in (0,):
            if service_index >= len(services):
                continue
            prepared = screen.get("rail_presentation") or {}
            travel_seconds = prepared.get("calling_travel_seconds", screen.get("_calling_travel_seconds"))
            if travel_seconds is None:
                travel_seconds = rail_calling_timing(
                    (services[service_index],),
                    scroll_speed,
                    font_width=WEATHER_FONT_WIDTH,
                )[0]
            cycle_seconds = travel_seconds + CALLING_MARQUEE_PAUSE_SECONDS
            within_cycle = rail_marquee_elapsed(phase, summary_seconds, calling_seconds) % cycle_seconds
            if within_cycle < travel_seconds:
                return True
        return False

    def _departures_rows_moving(self, screen, phase, calling_seconds=RAIL_CALLING_SECONDS,
                                summary_seconds=RAIL_SUMMARY_SECONDS):
        if not MATRIX_RAIL_ROWS_SCROLL:
            return False
        if rail_phase(phase, summary_seconds, calling_seconds) != "calling":
            return False
        services = screen.get("services") or ()
        start, progress, reset_progress = departure_scroll_state(
            rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
            max(0, len(services) - 1),
            screen.get("upcoming_train_pause_seconds", 2),
            visible_rows=2,
        )
        return progress > 0 or (reset_progress is not None and reset_progress > 0)

    def _record_animation_update(self, scene, changed, duration, animation_class=None):
        self._stats_animation_ticks += 1
        self._stats_update_total += duration
        self._stats_update_max = max(self._stats_update_max, duration)
        if scene == "todoist":
            self._stats_todoist_ticks += 1
            if changed:
                self._stats_todoist_changed += 1
        elif scene == "rail":
            self._stats_rail_ticks += 1
            if changed:
                self._stats_rail_changed += 1
        if animation_class in self._stats_animation_classes:
            counters = self._stats_animation_classes[animation_class]
            counters["ticks"] += 1
            counters["update_total"] += duration
            counters["update_max"] = max(counters["update_max"], duration)
            if changed:
                counters["changed"] += 1

    def _refresh(self, animation_class=None):
        """Present one changed scene according to the issue #70 test mode."""
        self._stats_changes += 1

        # With auto-refresh enabled, mutating displayio objects is sufficient.
        # Calling refresh() here would make this mode no longer a clean test.
        if self.presentation_mode == "auto_refresh":
            self._maybe_report_stats()
            return True

        self._stats_refresh_attempts += 1
        target = None if self.presentation_mode == "immediate" else MATRIX_REFRESH_FPS
        heap_before = (
            self._heap_free() if animation_class == "departures_calling" else None
        )
        refresh_started = time.monotonic()
        refreshed = self.display.refresh(target_frames_per_second=target)
        now = time.monotonic()
        if heap_before is not None:
            heap_after = self._heap_free()
            if heap_after is not None:
                self._stats_rail_refresh_heap_gain_max = max(
                    self._stats_rail_refresh_heap_gain_max,
                    heap_after - heap_before,
                )
        if animation_class in self._stats_animation_classes:
            counters = self._stats_animation_classes[animation_class]
            refresh_duration = now - refresh_started
            counters["refresh_total"] += refresh_duration
            counters["refresh_max"] = max(counters["refresh_max"], refresh_duration)
        if refreshed:
            self._stats_refresh_successes += 1
            refresh_duration = now - refresh_started
            self._stats_refresh_total += refresh_duration
            self._stats_refresh_max = max(self._stats_refresh_max, refresh_duration)
            self._record_success_interval(now)
        else:
            self._stats_refresh_failures += 1
            self._refresh_misses += 1
            if self._refresh_misses % 20 == 0:
                print("DISPLAY REFRESH DEADLINE MISSED count={}".format(self._refresh_misses))
        self._maybe_report_stats()
        return refreshed

    def _present(self, group):
        """Publish one fully-built frame to the matrix."""
        self._attach_brightness_overlay(group, bring_to_front=True)
        self.display.root_group = group
        # Pace frame publication through framebufferio. This waits for the
        # display refresh scheduler rather than swapping a frame mid-cycle.
        self._refresh()

    def show_diagnostic(self, color):
        """Fill the complete physical matrix with one moderate test colour."""
        import displayio

        bitmap = displayio.Bitmap(DISPLAY_WIDTH, 32, 1)
        palette = displayio.Palette(1)
        palette[0] = int(color)
        group = displayio.Group()
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette))
        self._present(group)
        print("DIAGNOSTIC 0x{:06X}".format(int(color)))

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
        import displayio

        services = screen.get("services") or []
        rail_right_edge = _header_content_right(screen)
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        state = rail_phase(phase, summary_seconds, calling_seconds)
        rows = rail_rows(services, phase, calling_seconds, summary_seconds)
        self._rail_calling_labels = []
        self._rail_departure_rows = []
        calling_group = None
        calling_label_state = None
        fixed_group = displayio.Group() if state == "calling" else group
        for row_index, (row_kind, service) in enumerate(rows):
            y = RAIL_ROW_Y[row_index]
            if row_kind == "header":
                self._label(group, "DEPARTURES", 0xFFAA00, 0, y)
            elif row_kind == "service" and service is not None:
                if state == "calling" and row_index >= 2:
                    continue
                if state == "calling":
                    ordinal = 1 if row_index == 0 else row_index
                else:
                    first_service_row = 0 if rows and rows[0][0] == "service" else 1
                    ordinal = row_index - first_service_row + 1
                color = 0xFF3300 if service.get("cancelled") else 0xFFFFFF
                self._rail_service(fixed_group, service, color, 0, y, rail_right_edge, ordinal)
            elif row_kind == "calling":
                calling_group = displayio.Group()
                presentation = screen.get("rail_presentation") or {}
                calling = presentation.get("calling_text") or calling_text(service)
                stations = calling[len(CALLING_LABEL):] if calling.startswith(CALLING_LABEL) else calling
                first = self._calling_label_group(
                    service, y, presentation.get("calling_segments")
                )
                calling_group.append(first)
                self._mask(calling_group, 0, y - 3, len(CALLING_LABEL) * WEATHER_FONT_WIDTH, 8)
                prefix = self._label(calling_group, CALLING_LABEL, 0xFFAA00, 0, y)
                calling_label_state = {
                    "prefix": prefix,
                    "first": first,
                    "text": calling,
                    "station_width": presentation.get(
                        "calling_station_width_px", len(stations) * WEATHER_FONT_WIDTH
                    ),
                }
        if state == "calling":
            # The top service and its calling row remain fixed. Cycle all
            # later services through the two lower physical rows.
            for index, service in enumerate(services[1:]):
                row_group = displayio.Group()
                color = 0xFF3300 if service.get("cancelled") else 0xFFFFFF
                self._rail_service(row_group, service, color, 0, 0, rail_right_edge, index + 2)
                row_group.y = RAIL_ROW_Y[-1] + 8
                group.append(row_group)
                self._rail_departure_rows.append(row_group)
            # Label coordinates are baselines: glyphs start three pixels
            # above them. Hide moving rows above the lower viewport, then
            # draw both fixed rows on top so outgoing glyphs cannot overlap.
            self._mask(
                group,
                0,
                0,
                DISPLAY_WIDTH,
                RAIL_ROW_Y[2] - 3,
            )
            if calling_group is not None:
                fixed_group.append(calling_group)
                self._rail_calling_labels.append(calling_label_state)
            group.append(fixed_group)
        self._rail_phase = state

    def _rail_cache_matches(self, screen):
        return (
            self._rail_group is not None
            and self._rail_services == screen.get("services")
            and self._rail_title == screen.get("title")
            and self._rail_stale == bool(screen.get("stale"))
            and _rail_weather_key(self._rail_weather) == _rail_weather_key(screen.get("weather"))
        )

    def _build_rail_scene(self, screen, clock_time, phase):
        """Build both departures layouts once; phase changes only swap roots."""
        import displayio

        scenes = {}
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        scene_phases = (0,) if summary_seconds <= 0 else (0, summary_seconds)
        for scene_phase in scene_phases:
            root = displayio.Group()
            self._rail(root, screen, scene_phase)
            calling_labels = self._rail_calling_labels
            departure_rows = self._rail_departure_rows

            # Departures owns all four physical rows. The generic header mask
            # used by other screens would cover row 1.
            clock_group = displayio.Group()
            clock_label = self._label(clock_group, "", 0xFFAA00, CLOCK_X, 3)
            weather_group = displayio.Group()
            if isinstance(screen.get("weather"), dict):
                self._header_weather(weather_group, screen.get("weather"), 0)
            root.append(clock_group)
            root.append(weather_group)
            scenes[rail_phase(scene_phase, summary_seconds, calling_seconds)] = {
                "group": root,
                "calling_labels": calling_labels,
                "departure_rows": departure_rows,
                "clock_group": clock_group,
                "clock_label": clock_label,
                "weather_group": weather_group,
            }

        self._rail_scenes = scenes
        self._rail_services = screen.get("services")
        self._rail_title = screen.get("title")
        self._rail_stale = bool(screen.get("stale"))
        self._rail_weather = screen.get("weather")
        self._select_rail_scene(phase, calling_seconds, summary_seconds)

    def _select_rail_scene(self, phase, calling_seconds=RAIL_CALLING_SECONDS,
                           summary_seconds=RAIL_SUMMARY_SECONDS):
        """Select a cached summary/calling layout without rebuilding labels."""
        state = rail_phase(phase, summary_seconds, calling_seconds)
        scene = self._rail_scenes[state]
        self._rail_group = scene["group"]
        self._rail_calling_labels = scene["calling_labels"]
        self._rail_departure_rows = scene["departure_rows"]
        self._rail_clock_group = scene["clock_group"]
        self._rail_clock_label = scene["clock_label"]
        self._rail_weather_group = scene["weather_group"]
        self._rail_phase = state

    def _update_rail_scene(self, screen, clock_time, phase):
        """Update only the calling-at marquee and rotating header item."""
        changed = False
        scroll_speed, scroll_gap = _station_scroll_settings(screen)
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        for labels in self._rail_calling_labels:
            calling_x = calling_marquee_x(
                labels["text"],
                rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                display_width=DISPLAY_WIDTH,
                font_width=WEATHER_FONT_WIDTH,
                speed=scroll_speed,
                gap=scroll_gap,
                stop_at_end=True,
                station_width=labels["station_width"],
            )
            first_x = int(calling_x)
            if labels["first"].x != first_x:
                labels["first"].x = first_x
                changed = True

        services = screen.get("services") or ()
        hidden_y = RAIL_ROW_Y[-1] + 8
        row_step = RAIL_ROW_Y[3] - RAIL_ROW_Y[2]
        if MATRIX_RAIL_ROWS_SCROLL:
            start, progress, reset_progress = departure_scroll_state(
                rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                max(0, len(services) - 1),
                screen.get("upcoming_train_pause_seconds", 2),
                visible_rows=2,
            )
            for index, row_group in enumerate(self._rail_departure_rows):
                if reset_progress is None:
                    row_y = hidden_y + index * row_step
                elif reset_progress > 0:
                    if index < 2:
                        row_y = RAIL_ROW_Y[2] + 2 * row_step - int(
                            reset_progress * 2 * row_step
                        ) + index * row_step
                    else:
                        row_y = hidden_y + index * row_step
                elif start <= index <= start + 2:
                    row_y = RAIL_ROW_Y[2] + (index - start) * row_step - int(
                        progress * row_step
                    )
                else:
                    row_y = hidden_y + index * row_step
                if row_group.y != row_y:
                    row_group.y = row_y
                    changed = True
        else:
            for index, row_group in enumerate(self._rail_departure_rows):
                row_y = (
                    RAIL_ROW_Y[2] + index * row_step
                    if index < 2
                    else hidden_y + index * row_step
                )
                if row_group.y != row_y:
                    row_group.y = row_y
                    changed = True

        if self._rail_clock_label.text != clock_time:
            self._rail_clock_label.text = clock_time
            changed = True
        item, offset = _header_item_state(phase, screen.get("weather"))
        clock_x = offset if item == "clock" else DISPLAY_WIDTH
        weather_x = offset if item == "weather" else DISPLAY_WIDTH
        if self._rail_clock_group.x != clock_x:
            self._rail_clock_group.x = clock_x
            changed = True
        if self._rail_weather_group.x != weather_x:
            self._rail_weather_group.x = weather_x
            changed = True
        return changed

    def _show_rail(self, screen, clock_time, phase):
        """Render departures with a persistent scene and live calling marquee."""
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        state = rail_phase(phase, summary_seconds, calling_seconds)
        if not self._rail_cache_matches(screen):
            self._build_rail_scene(screen, clock_time, phase)
        elif self._rail_phase != state:
            self._select_rail_scene(phase, calling_seconds, summary_seconds)
        update_heap_before = self._heap_free()
        update_started = time.monotonic()
        changed = self._update_rail_scene(screen, clock_time, phase)
        update_duration = time.monotonic() - update_started
        if update_duration > 0.1 and update_heap_before is not None:
            update_heap_after = self._heap_free()
            if update_heap_after is not None:
                self._stats_rail_update_heap_gain_max = max(
                    self._stats_rail_update_heap_gain_max,
                    update_heap_after - update_heap_before,
                )
        self._attach_brightness_overlay(self._rail_group)
        if self.display.root_group is not self._rail_group:
            self.display.root_group = self._rail_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "rail",
            changed,
            update_duration,
            animation_class,
        )
        if changed:
            self._refresh(animation_class)

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
                    title_chars = max(1, title_width // 5)
                    title_x = AGENDA_TITLE_X + agenda_marquee_x(
                        title,
                        phase,
                        visible_chars=title_chars,
                        font_width=5,
                        speed=TODOIST_MARQUEE_SPEED,
                        pause_seconds=TODOIST_MARQUEE_PAUSE_SECONDS,
                    )
                    self._label(group, title, 0xFFFFFF, title_x, y)
                    # Clip the moving title before the fixed due/event label
                    # is painted, so long text cannot overlap it.
                    self._mask(
                        group,
                        due_x - HEADER_GAP,
                        y - 3,
                        DISPLAY_WIDTH - due_x + HEADER_GAP,
                        AGENDA_ROW_HEIGHT,
                    )
                else:
                    self._label(group, title, 0xFFFFFF, agenda_title_marquee_x(title, phase), y)
                self._mask(group, 0, y - 3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)
                self._label(group, when, 0xFFFFFF, 0, y)
                if due:
                    self._label(group, due, 0xFFFFFF, due_x, y)
        self._header_mask(group)
        self._label(group, _clip(screen.get("title") or "UPCOMING", 30), 0xFFAA00, 0, 3)

    def _flash(self, group, screen):
        """Render a generic transient event without provider-specific logic."""
        import displayio
        del displayio
        self._label(group, _clip(screen.get("title") or "FLASH", 30), 0xFFAA00, 0, 3)
        label = str(screen.get("label") or "")
        first, second = label[:42], label[42:84]
        self._label(group, first, 0xFFFFFF, 0, 12)
        if second:
            self._label(group, second, 0xFFFFFF, 0, 20)
        due = str(screen.get("due_at") or "")
        if len(due) >= 16:
            self._label(group, due[11:16], 0xAAAAAA, 226, 3)

    def _todoist_cache_matches(self, screen, clock_date):
        weather = screen.get("weather")
        weather_icon = weather.get("icon") if isinstance(weather, dict) else None
        weather_temp = weather.get("temperature_c") if isinstance(weather, dict) else None
        weather_stale = bool(weather.get("stale")) if isinstance(weather, dict) else False
        return (
            self._todoist_group is not None
            and self._todoist_events == screen.get("events")
            and self._todoist_clock_date == clock_date
            and self._todoist_title == screen.get("title")
            and self._todoist_stale == bool(screen.get("stale"))
            and self._todoist_viewport_size == max(1, int(screen.get("viewport_size") or AGENDA_VISIBLE_ROWS))
            and self._todoist_page_step == max(1, int(screen.get("page_step") or 1))
            and self._todoist_page_seconds == (screen.get("page_seconds") or 5)
            and self._todoist_weather_icon == weather_icon
            and self._todoist_weather_temp == weather_temp
            and self._todoist_weather_stale == weather_stale
        )

    def _build_todoist_scene(self, screen, clock_time, clock_date):
        """Build the Todoist scene once; animation mutates only child positions."""
        import displayio

        root = displayio.Group()
        events = screen.get("events") or ()
        rows = []

        if not events:
            self._label(root, "No upcoming events", 0xFFFFFF, 0, AGENDA_FIRST_Y)
        else:
            for event in events:
                row_group = displayio.Group()
                title_group = displayio.Group()
                when, title = calendar_row_parts(event)
                due = todoist_due_label(event, clock_date)
                due_x = _right_aligned_x(due, DISPLAY_WIDTH) if due else DISPLAY_WIDTH
                title_width = max(0, due_x - HEADER_GAP - AGENDA_TITLE_X) if due else DISPLAY_WIDTH - AGENDA_TITLE_X
                visible_chars = max(1, title_width // WEATHER_FONT_WIDTH)

                for chunk_start in range(0, max(1, len(title)), 24):
                    self._label(
                        title_group,
                        title[chunk_start:chunk_start + 24],
                        0xFFFFFF,
                        chunk_start * WEATHER_FONT_WIDTH,
                        0,
                    )
                row_group.append(title_group)

                # Masks are fixed children of the row. Only title_group.x and
                # row_group.y change while scrolling, so no per-frame Bitmap,
                # Palette, Label or Group allocation is needed.
                if due:
                    self._mask(
                        row_group,
                        due_x - HEADER_GAP,
                        -3,
                        DISPLAY_WIDTH - due_x + HEADER_GAP,
                        AGENDA_ROW_HEIGHT,
                    )
                self._mask(row_group, 0, -3, AGENDA_TITLE_X, AGENDA_ROW_HEIGHT)
                self._label(row_group, when, 0xFFFFFF, 0, 0)
                if due:
                    due_color = 0xFF3300 if due == "OVERDUE" else 0xFFFFFF
                    self._label(row_group, due, due_color, due_x, 0)

                row_group.y = 64
                root.append(row_group)
                rows.append((row_group, title_group, title, visible_chars))

        self._header_mask(root)
        self._label(root, _clip(screen.get("title") or "UPCOMING", 30), 0xFFAA00, 0, 3)
        if screen.get("stale"):
            self._label(root, "STALE", 0xFF3300, STALE_X, 3)

        self._mask(root, HEADER_SLOT_X, 0, HEADER_SLOT_WIDTH, 8)
        clock_group = displayio.Group()
        clock_label = self._label(clock_group, clock_time, 0xFFAA00, CLOCK_X, 3)
        root.append(clock_group)

        weather_group = displayio.Group()
        if isinstance(screen.get("weather"), dict):
            self._header_weather(weather_group, screen.get("weather"), 0)
        root.append(weather_group)

        weather = screen.get("weather")
        self._todoist_group = root
        self._todoist_rows = rows
        self._todoist_events = screen.get("events")
        self._todoist_clock_date = clock_date
        self._todoist_title = screen.get("title")
        self._todoist_stale = bool(screen.get("stale"))
        self._todoist_viewport_size = max(1, int(screen.get("viewport_size") or AGENDA_VISIBLE_ROWS))
        self._todoist_page_step = max(1, int(screen.get("page_step") or 1))
        self._todoist_page_seconds = screen.get("page_seconds") or 5
        last_start = max(0, len(rows) - self._todoist_viewport_size)
        page_starts = list(range(0, last_start + 1, self._todoist_page_step))
        if page_starts[-1] != last_start:
            page_starts.append(last_start)
        page_durations = []
        for start in page_starts:
            longest_scroll = 0.0
            stop = min(len(rows), start + self._todoist_viewport_size)
            for row_index in range(start, stop):
                row = rows[row_index]
                longest_scroll = max(
                    longest_scroll,
                    self._todoist_title_scroll_seconds(row[2], row[3]),
                )
            page_durations.append(
                longest_scroll
                + (TODOIST_MARQUEE_PAUSE_SECONDS if longest_scroll else 0.0)
                + max(0.0, float(self._todoist_page_seconds or 0))
            )
        self._todoist_page_starts = tuple(page_starts)
        self._todoist_page_durations = tuple(page_durations)
        self._todoist_weather_icon = weather.get("icon") if isinstance(weather, dict) else None
        self._todoist_weather_temp = weather.get("temperature_c") if isinstance(weather, dict) else None
        self._todoist_weather_stale = bool(weather.get("stale")) if isinstance(weather, dict) else False
        self._todoist_clock_group = clock_group
        self._todoist_clock_label = clock_label
        self._todoist_weather_group = weather_group

    def _todoist_title_scroll_seconds(self, title, visible_chars):
        """Return the one-way scroll time needed to reveal a Todoist title."""
        visible_chars = max(1, int(visible_chars or 1))
        overflow = max(0, (len(str(title or "")) - visible_chars) * WEATHER_FONT_WIDTH)
        return overflow / max(1.0, float(TODOIST_MARQUEE_SPEED))

    def _todoist_page_transition_at(self, start):
        """Return the dwell time for the Todoist window at ``start``."""
        for index in range(len(self._todoist_page_starts)):
            if self._todoist_page_starts[index] == start:
                return self._todoist_page_durations[index]

        try:
            minimum_page_seconds = max(0.0, float(self._todoist_page_seconds or 0))
        except (TypeError, ValueError):
            minimum_page_seconds = 0.0
        longest_scroll = 0.0
        stop = min(len(self._todoist_rows), max(0, start) + self._todoist_viewport_size)
        for row_index in range(max(0, start), stop):
            row = self._todoist_rows[row_index]
            longest_scroll = max(
                longest_scroll,
                self._todoist_title_scroll_seconds(row[2], row[3]),
            )
        return (
            longest_scroll
            + (TODOIST_MARQUEE_PAUSE_SECONDS if longest_scroll else 0.0)
            + minimum_page_seconds
        )

    def _todoist_page_slide_active(self, phase):
        if len(self._todoist_rows) <= self._todoist_viewport_size:
            return False
        try:
            remaining = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            return False
        starts = self._todoist_page_starts
        for index in range(max(0, len(starts) - 1)):
            start = starts[index]
            remaining -= self._todoist_page_transition_at(start)
            if remaining < AGENDA_SLIDE_SECONDS:
                return remaining > 0.0
            remaining -= AGENDA_SLIDE_SECONDS
        return False

    def _todoist_titles_moving(self, phase):
        try:
            phase = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            phase = 0.0
        visible = self._todoist_viewport_size
        if not visible:
            return False
        remaining = phase
        starts = self._todoist_page_starts
        for index in range(len(starts)):
            start = starts[index]
            duration = self._todoist_page_transition_at(start)
            if remaining <= duration or index == len(starts) - 1:
                stop = min(len(self._todoist_rows), start + visible)
                for row_index in range(start, stop):
                    row = self._todoist_rows[row_index]
                    if remaining < self._todoist_title_scroll_seconds(row[2], row[3]):
                        return True
                return False
            remaining -= duration
            if remaining < AGENDA_SLIDE_SECONDS:
                return False
            remaining -= AGENDA_SLIDE_SECONDS
        return False

    def _todoist_title_x(self, title, phase, visible_chars):
        """Scroll once to the final title position instead of looping."""
        visible_chars = max(1, int(visible_chars or 1))
        overflow = max(0, (len(str(title or "")) - visible_chars) * WEATHER_FONT_WIDTH)
        if overflow <= 0:
            return AGENDA_TITLE_X
        try:
            phase = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            phase = 0.0
        offset = min(
            overflow,
            int(phase * max(1.0, float(TODOIST_MARQUEE_SPEED)) + 1e-9),
        )
        return AGENDA_TITLE_X - offset

    def _update_todoist_scene(self, screen, clock_time, phase):
        """Move cached Todoist groups using page-local animation phases."""
        changed = False
        visible = self._todoist_viewport_size
        event_count = len(self._todoist_rows)
        try:
            phase = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            phase = 0.0

        start = 0
        progress = 0.0
        page_phase = phase
        sliding_from = None

        if event_count > visible:
            remaining = phase
            starts = self._todoist_page_starts
            for index in range(len(starts)):
                candidate = starts[index]
                window_duration = self._todoist_page_transition_at(candidate)
                if remaining <= window_duration or index == len(starts) - 1:
                    start = candidate
                    page_phase = remaining
                    break
                remaining -= window_duration
                if remaining <= AGENDA_SLIDE_SECONDS + 1e-9:
                    if remaining >= AGENDA_SLIDE_SECONDS - 1e-9:
                        remaining = AGENDA_SLIDE_SECONDS
                    else:
                        start = candidate
                        progress = max(0.0, remaining / AGENDA_SLIDE_SECONDS)
                        page_phase = None
                        sliding_from = candidate
                        break
                remaining -= AGENDA_SLIDE_SECONDS

        y_offset = int(progress * self._todoist_page_step * AGENDA_ROW_HEIGHT + 1e-9)

        for index in range(event_count):
            row = self._todoist_rows[index]
            row_group, title_group, title, visible_chars = row
            if progress > 0 and start <= index < start + visible + self._todoist_page_step:
                y = AGENDA_FIRST_Y + (index - start) * AGENDA_ROW_HEIGHT - y_offset
            elif progress <= 0 and start <= index < start + visible:
                y = AGENDA_FIRST_Y + (index - start) * AGENDA_ROW_HEIGHT
            else:
                y = 64
            if row_group.y != y:
                row_group.y = y
                changed = True

            if progress > 0:
                if sliding_from is not None and index < sliding_from + visible:
                    title_phase = self._todoist_title_scroll_seconds(title, visible_chars)
                else:
                    title_phase = 0.0
            elif start <= index < start + visible:
                title_phase = page_phase
            else:
                title_phase = 0.0

            title_x = self._todoist_title_x(title, title_phase, visible_chars)
            if title_group.x != title_x:
                title_group.x = title_x
                changed = True

        if self._todoist_clock_label.text != clock_time:
            self._todoist_clock_label.text = clock_time
            changed = True

        item, offset = _header_item_state(phase, screen.get("weather"))
        clock_x = offset if item == "clock" else DISPLAY_WIDTH
        weather_x = offset if item == "weather" else DISPLAY_WIDTH
        if self._todoist_clock_group.x != clock_x:
            self._todoist_clock_group.x = clock_x
            changed = True
        if self._todoist_weather_group.x != weather_x:
            self._todoist_weather_group.x = weather_x
            changed = True
        return changed

    def _show_todoist(self, screen, clock_time, clock_date, phase):
        """Render Todoist with a persistent scene graph and coordinate-only animation."""
        if not self._todoist_cache_matches(screen, clock_date):
            self._build_todoist_scene(screen, clock_time, clock_date)

        update_started = time.monotonic()
        changed = self._update_todoist_scene(screen, clock_time, phase)
        self._attach_brightness_overlay(self._todoist_group)
        if self.display.root_group is not self._todoist_group:
            self.display.root_group = self._todoist_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "todoist",
            changed,
            time.monotonic() - update_started,
            animation_class,
        )
        if changed:
            self._refresh(animation_class)

    def _steam_train_cache_matches(self, screen):
        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        return (
            self._steam_train_group is not None
            and self._steam_train_words == str(screen.get("words") or "")
            and self._steam_train_speed == speed
        )

    def _build_steam_train_scene(self, screen):
        import displayio

        root = displayio.Group()
        motion = displayio.Group()
        bitmap = displayio.Bitmap(STEAM_TRAIN_WIDTH, STEAM_TRAIN_HEIGHT, 4)
        palette = displayio.Palette(4)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = 0xFFFFFF
        palette[2] = 0xFFAA00
        palette[3] = 0xAAAAAA

        def fill_rect(x, y, width, height, color):
            for py in range(max(0, y), min(STEAM_TRAIN_HEIGHT, y + height)):
                for px in range(max(0, x), min(STEAM_TRAIN_WIDTH, x + width)):
                    bitmap[px, py] = color

        fill_rect(4, 9, 29, 9, 1)
        fill_rect(30, 4, 16, 14, 1)
        fill_rect(8, 2, 7, 7, 3)
        fill_rect(6, 1, 11, 2, 3)
        fill_rect(28, 2, 20, 3, 2)
        fill_rect(0, 14, 6, 3, 2)
        fill_rect(16, 6, 16, 3, 1)
        # Cab window stays transparent/black.
        fill_rect(34, 6, 7, 6, 0)

        wheel_points = (
            (-2, -3), (-1, -3), (0, -3), (1, -3), (2, -3),
            (-3, -2), (3, -2), (-3, -1), (3, -1),
            (-3, 0), (0, 0), (3, 0),
            (-3, 1), (3, 1), (-3, 2), (3, 2),
            (-2, 3), (-1, 3), (0, 3), (1, 3), (2, 3),
        )
        for center_x in (11, 34, 43):
            for dx, dy in wheel_points:
                px = center_x + dx
                py = 20 + dy
                if 0 <= px < STEAM_TRAIN_WIDTH and 0 <= py < STEAM_TRAIN_HEIGHT:
                    bitmap[px, py] = 2

        motion.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=3))
        words = str(screen.get("words") or "")
        if words:
            self._label(
                motion,
                words,
                0xFFAA00,
                STEAM_TRAIN_WIDTH + STEAM_TRAIN_TEXT_GAP,
                18,
            )
        root.append(motion)

        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        self._steam_train_group = root
        self._steam_train_motion_group = motion
        self._steam_train_words = words
        self._steam_train_speed = speed

    def _update_steam_train_scene(self, phase):
        if self._steam_train_motion_group is None:
            return False
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        next_x = DISPLAY_WIDTH - int(elapsed * self._steam_train_speed)
        if self._steam_train_motion_group.x == next_x:
            return False
        self._steam_train_motion_group.x = next_x
        return True

    def _show_steam_train(self, screen, phase):
        if not self._steam_train_cache_matches(screen):
            self._build_steam_train_scene(screen)
        update_started = time.monotonic()
        changed = self._update_steam_train_scene(phase)
        self._attach_brightness_overlay(self._steam_train_group)
        if self.display.root_group is not self._steam_train_group:
            self.display.root_group = self._steam_train_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "steam_train",
            changed,
            time.monotonic() - update_started,
            animation_class,
        )
        if changed:
            self._refresh(animation_class)

    def _weekly_weather(self, group, screen):
        import displayio

        layout = _weekly_weather_layout(screen.get("days") or [])
        if not layout:
            text = "Weather unavailable"
            x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
            self._label(group, text, 0xAAAAAA, x, 18)
            return

        stale = bool(screen.get("stale"))
        text_color = 0xAAAAAA if stale else 0xFFFFFF
        weekday_color = 0x777777 if stale else 0xFFAA00
        for item in layout:
            self._label(group, item["weekday"], weekday_color, item["weekday_x"], WEATHER_HEADING_BASELINE_Y)
            bitmap = displayio.Bitmap(item["icon_width"], 14, 2)
            palette = displayio.Palette(2)
            palette[0] = 0x000000
            palette.make_transparent(0)
            palette[1] = _weather_rgb(item["icon_name"], stale)
            for y, row in enumerate(item["icon_rows"]):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(WEEKLY_WEATHER_ICON_SCALE):
                            for dy in range(WEEKLY_WEATHER_ICON_SCALE):
                                bitmap[x * WEEKLY_WEATHER_ICON_SCALE + dx, y * WEEKLY_WEATHER_ICON_SCALE + dy] = 1
            group.append(displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                x=item["icon_x"],
                y=WEEKLY_WEATHER_ICON_Y,
            ))
            self._temperature_label(
                group, item["max_text"], text_color, item["max_x"], WEEKLY_WEATHER_TEMPERATURE_Y
            )

    def _today_weather(self, group, screen):
        import displayio

        layout = _today_weather_layout(screen.get("blocks") or [])
        if not layout:
            text = "Weather unavailable"
            x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
            self._label(group, text, 0xAAAAAA, x, 18)
            return
        stale = bool(screen.get("stale"))
        text_color = 0xAAAAAA if stale else 0xFFFFFF
        label_color = 0x777777 if stale else 0xFFAA00
        for item in layout:
            self._label(group, item["label"], label_color, item["label_x"], WEATHER_HEADING_BASELINE_Y)
            bitmap = displayio.Bitmap(item["icon_width"], item["icon_width"], 2)
            palette = displayio.Palette(2)
            palette[0] = 0x000000
            palette.make_transparent(0)
            palette[1] = _weather_rgb(item["icon_name"], stale)
            for y, row in enumerate(item["icon_rows"]):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(TODAY_WEATHER_ICON_SCALE):
                            for dy in range(TODAY_WEATHER_ICON_SCALE):
                                bitmap[x * TODAY_WEATHER_ICON_SCALE + dx,
                                       y * TODAY_WEATHER_ICON_SCALE + dy] = 1
            group.append(displayio.TileGrid(
                bitmap, pixel_shader=palette, x=item["icon_x"], y=TODAY_WEATHER_ICON_Y
            ))
            self._temperature_label(
                group, item["temp_text"], text_color, item["temp_x"], TODAY_WEATHER_TEMPERATURE_Y
            )

    def _sun_weather(self, group, screen):
        import displayio

        stale = bool(screen.get("stale"))
        text_color = 0xAAAAAA if stale else 0xFFFFFF
        label_color = 0x777777 if stale else 0xFFAA00
        values = (
            ("SUNRISE", screen.get("sunrise_time") or "--:--", "clear_day", 0, DISPLAY_WIDTH // 2),
            ("SUNSET", screen.get("sunset_time") or "--:--", "clear_night", DISPLAY_WIDTH // 2, DISPLAY_WIDTH),
        )
        for label, value, icon_name, left, right in values:
            width = right - left
            self._label(group, label, label_color,
                        left + max(0, (width - len(label) * WEATHER_FONT_WIDTH) // 2),
                        WEATHER_HEADING_BASELINE_Y)
            rows = WEATHER_ICONS[icon_name]
            icon_width = WEATHER_ICON_WIDTH * SUN_WEATHER_ICON_SCALE
            bitmap = displayio.Bitmap(icon_width, icon_width, 2)
            palette = displayio.Palette(2)
            palette[0] = 0x000000
            palette.make_transparent(0)
            palette[1] = _weather_rgb(icon_name, stale)
            for y, row in enumerate(rows):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(SUN_WEATHER_ICON_SCALE):
                            for dy in range(SUN_WEATHER_ICON_SCALE):
                                bitmap[x * SUN_WEATHER_ICON_SCALE + dx, y * SUN_WEATHER_ICON_SCALE + dy] = 1
            group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=left + 20, y=10))
            self._label(group, value, text_color, left + 52, 15)

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

        empty_state = screen.get("empty_state")
        kind = screen.get("kind")
        if not empty_state and kind == "steam_train_intro":
            self._show_steam_train(screen, phase)
            return

        if (
            not empty_state
            and kind == "calendar_agenda"
            and screen.get("source") == "todoist"
        ):
            self._show_todoist(screen, clock_time, clock_date, phase)
            return

        if not empty_state and kind == "rail_combined":
            self._show_rail(screen, clock_time, phase)
            return

        if not empty_state and kind in WEATHER_FULLSCREEN_KINDS:
            group = displayio.Group()
            if kind == "weather_weekly":
                self._weekly_weather(group, screen)
            elif kind == "weather_today":
                self._today_weather(group, screen)
            else:
                self._sun_weather(group, screen)
            self._present(group)
            return

        group = displayio.Group()
        if empty_state:
            text = _clip(empty_state, 30)
            x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
            self._label(group, text, 0xFFFFFF, x, 18)
            self._present(group)
            return
        if kind == "rail_combined":
            self._rail(group, screen, phase)
        elif kind == "theme_park_queues":
            self._queues(group, screen, phase)
        elif kind == "calendar_agenda":
            self._calendar(group, screen, phase, clock_date)
        elif kind == "flash":
            self._flash(group, screen)
        else:
            self._label(group, _clip(screen.get("title") or "Display unavailable", 30), 0xFFFFFF, 0, 3)
        due_text, due_x = _calendar_due_layout(screen, clock_date, clock_time)
        if due_text:
            self._label(group, due_text, 0xFFFFFF, due_x, 3)
        if screen.get("stale"):
            self._label(group, "STALE", 0xFF3300, STALE_X, 3)
        self._mask(group, HEADER_SLOT_X, 0, HEADER_SLOT_WIDTH, 8)
        item, offset = _header_item_state(phase, screen.get("weather"))
        if item == "weather":
            self._header_weather(group, screen.get("weather"), offset)
        else:
            self._label(group, clock_time, 0xFFAA00, CLOCK_X + offset, 3)
        self._present(group)


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

    def _text_scaled(self, value, x, y, color):
        scale = WEEKLY_WEATHER_TEXT_SCALE
        for index, char in enumerate(str(value)):
            rows = WEEKLY_WEATHER_GLYPHS.get(char, (0, 0, 0, 0, 0))
            for row_index, row_bits in enumerate(rows):
                for column in range(WEEKLY_WEATHER_GLYPH_WIDTH):
                    if row_bits & (1 << (WEEKLY_WEATHER_GLYPH_WIDTH - column - 1)):
                        for dx in range(scale):
                            for dy in range(scale):
                                self._pixel(x + index * (WEEKLY_WEATHER_GLYPH_WIDTH + 1) * scale + column * scale + dx,
                                            y + row_index * scale + dy, color)

    def _clear_rect(self, start_x, start_y, end_x, end_y):
        if self.pixels is None:
            return
        for y in range(max(0, int(start_y)), min(32, int(end_y))):
            for x in range(max(0, int(start_x)), min(DISPLAY_WIDTH, int(end_x))):
                self._pixel(x, y, (0, 0, 0))

    def _clear_rows(self, start_y, end_y):
        self._clear_rect(0, start_y, DISPLAY_WIDTH, end_y)

    def _fill_rect(self, x, y, width, height, color):
        for py in range(max(0, int(y)), min(32, int(y + height))):
            for px in range(max(0, int(x)), min(DISPLAY_WIDTH, int(x + width))):
                self._pixel(px, py, color)

    def _steam_train(self, screen, phase):
        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        x = DISPLAY_WIDTH - int(elapsed * speed)
        self._fill_rect(x + 4, 12, 29, 9, (255, 255, 255))
        self._fill_rect(x + 30, 7, 16, 14, (255, 255, 255))
        self._fill_rect(x + 8, 5, 7, 7, (170, 170, 170))
        self._fill_rect(x + 6, 4, 11, 2, (170, 170, 170))
        self._fill_rect(x + 28, 5, 20, 3, (255, 170, 0))
        self._fill_rect(x, 17, 6, 3, (255, 170, 0))
        self._fill_rect(x + 16, 9, 16, 3, (255, 255, 255))
        self._fill_rect(x + 34, 9, 7, 6, (0, 0, 0))
        wheel_points = (
            (-2, -3), (-1, -3), (0, -3), (1, -3), (2, -3),
            (-3, -2), (3, -2), (-3, -1), (3, -1),
            (-3, 0), (0, 0), (3, 0),
            (-3, 1), (3, 1), (-3, 2), (3, 2),
            (-2, 3), (-1, 3), (0, 3), (1, 3), (2, 3),
        )
        for center_x in (11, 34, 43):
            for dx, dy in wheel_points:
                self._pixel(x + center_x + dx, 23 + dy, (255, 51, 0))
        words = str(screen.get("words") or "")
        if words:
            self._text(words, x + STEAM_TRAIN_WIDTH + STEAM_TRAIN_TEXT_GAP, 12, (255, 170, 0))

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

    def _weekly_weather(self, screen):
        layout = _weekly_weather_layout(screen.get("days") or [])
        if not layout:
            text = "Weather unavailable"
            x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
            self._text(text, x, 13, (170, 170, 170))
            return

        stale = bool(screen.get("stale"))
        text_color = (170, 170, 170) if stale else (255, 255, 255)
        weekday_color = (119, 119, 119) if stale else (255, 170, 0)
        for item in layout:
            self._text(item["weekday"], item["weekday_x"], WEATHER_HEADING_PIXEL_Y, weekday_color)
            icon_color = _rgb_tuple(_weather_rgb(item["icon_name"], stale))
            for y, row in enumerate(item["icon_rows"]):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(WEEKLY_WEATHER_ICON_SCALE):
                            for dy in range(WEEKLY_WEATHER_ICON_SCALE):
                                self._pixel(item["icon_x"] + x * WEEKLY_WEATHER_ICON_SCALE + dx,
                                            WEEKLY_WEATHER_ICON_Y + y * WEEKLY_WEATHER_ICON_SCALE + dy,
                                            icon_color)
            self._text_scaled(
                item["max_text"], item["max_x"], WEEKLY_WEATHER_TEMPERATURE_Y, text_color
            )

    def _today_weather(self, screen):
        layout = _today_weather_layout(screen.get("blocks") or [])
        if not layout:
            text = "Weather unavailable"
            x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
            self._text(text, x, 13, (170, 170, 170))
            return
        stale = bool(screen.get("stale"))
        text_color = (170, 170, 170) if stale else (255, 255, 255)
        label_color = (119, 119, 119) if stale else (255, 170, 0)
        for item in layout:
            self._text(item["label"], item["label_x"], WEATHER_HEADING_PIXEL_Y, label_color)
            icon_color = _rgb_tuple(_weather_rgb(item["icon_name"], stale))
            for y, row in enumerate(item["icon_rows"]):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(TODAY_WEATHER_ICON_SCALE):
                            for dy in range(TODAY_WEATHER_ICON_SCALE):
                                self._pixel(item["icon_x"] + x * TODAY_WEATHER_ICON_SCALE + dx,
                                            TODAY_WEATHER_ICON_Y + y * TODAY_WEATHER_ICON_SCALE + dy,
                                            icon_color)
            self._text_scaled(
                item["temp_text"], item["temp_x"], TODAY_WEATHER_TEMPERATURE_Y, text_color
            )

    def _sun_weather(self, screen):
        stale = bool(screen.get("stale"))
        text_color = (170, 170, 170) if stale else (255, 255, 255)
        label_color = (119, 119, 119) if stale else (255, 170, 0)
        values = (
            ("SUNRISE", screen.get("sunrise_time") or "--:--", "clear_day", 0, DISPLAY_WIDTH // 2),
            ("SUNSET", screen.get("sunset_time") or "--:--", "clear_night", DISPLAY_WIDTH // 2, DISPLAY_WIDTH),
        )
        for label, value, icon_name, left, right in values:
            width = right - left
            self._text(
                label,
                left + max(0, (width - len(label) * WEATHER_FONT_WIDTH) // 2),
                WEATHER_HEADING_PIXEL_Y,
                label_color,
            )
            icon_color = _rgb_tuple(_weather_rgb(icon_name, stale))
            for y, row in enumerate(WEATHER_ICONS[icon_name]):
                for x, pixel in enumerate(row):
                    if pixel == "#":
                        for dx in range(SUN_WEATHER_ICON_SCALE):
                            for dy in range(SUN_WEATHER_ICON_SCALE):
                                self._pixel(left + 20 + x * SUN_WEATHER_ICON_SCALE + dx,
                                            10 + y * SUN_WEATHER_ICON_SCALE + dy, icon_color)
            self._text(value, left + 52, 15, text_color)

    def _draw_screen(self, screen, phase, clock_date=""):
        kind = screen.get("kind")
        if kind == "steam_train_intro":
            self._steam_train(screen, phase)
        elif kind == "weather_weekly":
            self._weekly_weather(screen)
        elif kind == "weather_today":
            self._today_weather(screen)
        elif kind == "weather_sun":
            self._sun_weather(screen)
        elif kind == "rail_combined":
            services = screen.get("services") or []
            rail_right_edge = _header_content_right(screen)
            calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
            summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
            state = rail_phase(phase, summary_seconds, calling_seconds)
            rows = rail_rows(services, phase, calling_seconds, summary_seconds)
            calling_service = None
            for row_index, (row_kind, service) in enumerate(rows[:2] if state == "calling" else rows):
                y = RAIL_ROW_Y[row_index]
                if row_kind == "header":
                    self._text("DEPARTURES", 0, y, (255, 170, 0))
                elif row_kind == "service" and service is not None:
                    if state == "calling":
                        ordinal = 1 if row_index == 0 else row_index
                    else:
                        first_service_row = 0 if services and len(services) >= 4 else 1
                        ordinal = row_index - first_service_row + 1
                    color = (255, 20, 0) if service.get("cancelled") else (255, 255, 255)
                    self._rail_service(service, color, 0, y, rail_right_edge, ordinal)
                elif row_kind == "calling" and service is not None:
                    calling_service = service
            if state == "calling":
                upcoming = services[1:]
                start, progress, reset_progress = departure_scroll_state(
                    rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                    len(upcoming),
                    screen.get("upcoming_train_pause_seconds", 2),
                    visible_rows=2,
                )
                row_step = RAIL_ROW_Y[3] - RAIL_ROW_Y[2]
                if reset_progress is None:
                    visible = ()
                elif reset_progress > 0:
                    visible = ((i, RAIL_ROW_Y[2] + 2 * row_step - int(reset_progress * 2 * row_step) + i * row_step)
                               for i in range(min(2, len(upcoming)))
                               if RAIL_ROW_Y[2] + 2 * row_step - int(reset_progress * 2 * row_step) + i * row_step <= RAIL_ROW_Y[-1])
                else:
                    visible = ((i, RAIL_ROW_Y[2] + (i - start) * row_step - int(progress * row_step))
                               for i in range(start, min(len(upcoming), start + 3)))
                for service_index, y in visible:
                    service = upcoming[service_index]
                    color = (255, 20, 0) if service.get("cancelled") else (255, 255, 255)
                    self._rail_service(service, color, 0, y, rail_right_edge, service_index + 2)
                if calling_service is not None:
                    y = RAIL_ROW_Y[1]
                    self._clear_rect(0, y, DISPLAY_WIDTH, RAIL_ROW_Y[2])
                    text = calling_text(calling_service)
                    scroll_speed, scroll_gap = _station_scroll_settings(screen)
                    calling_x = calling_marquee_x(
                        text,
                        rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                        display_width=DISPLAY_WIDTH,
                        font_width=WEATHER_FONT_WIDTH,
                        speed=scroll_speed,
                        gap=scroll_gap,
                        stop_at_end=True,
                    )
                    self._text(CALLING_LABEL, 0, y, (255, 170, 0))
                    if calling_x is not None:
                        for segment_x, segment in _calling_segments(text, calling_x, scroll_gap):
                            self._text(segment, segment_x, y, (255, 170, 0))
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
                self._text("No upcoming events", 0, AGENDA_FIRST_Y, (255, 255, 255))
            else:
                row_count = min(len(events) - start, visible * 2 if progress > 0 else visible)
                y_offset = int(progress * visible * AGENDA_ROW_HEIGHT)
                for slot in range(max(0, row_count)):
                    event_index = start + slot
                    if event_index >= len(events):
                        break
                    when, title = calendar_row_parts(events[event_index])
                    y = AGENDA_FIRST_Y + slot * AGENDA_ROW_HEIGHT - y_offset
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
                        due_color = (255, 51, 0) if due == "OVERDUE" else (255, 255, 255)
                        self._text(due, due_x + due_offset, y, due_color)
            self._clear_rows(0, 8)
            self._text(_clip(screen.get("title") or "UPCOMING", 30), 0, 0, (255, 100, 0))
        elif kind == "flash":
            self._clear_rows(0, 32)
            self._text(_clip(screen.get("title") or "FLASH", 30), 0, 0, (255, 170, 0))
            label = str(screen.get("label") or "")
            self._text(label[:42], 0, 11, (255, 255, 255))
            if len(label) > 42:
                self._text(label[42:84], 0, 19, (255, 255, 255))
            due = str(screen.get("due_at") or "")
            if len(due) >= 16:
                self._text(due[11:16], 226, 0, (170, 170, 170))
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
        empty_state = screen.get("empty_state")
        kind = screen.get("kind")
        if empty_state:
            if self.pixels is not None:
                self.pixels.fill((0, 0, 0))
                text = _clip(empty_state, 30)
                x = max(0, (DISPLAY_WIDTH - len(text) * WEATHER_FONT_WIDTH) // 2)
                self._text(text, x, 13, (255, 255, 255))
                self.pixels.show()
            print("\n{}".format(empty_state))
            return
        due_text, due_x = _calendar_due_layout(screen, clock_date, clock_time)
        if self.pixels is not None:
            self.pixels.fill((0, 0, 0))
            self._draw_screen(screen, phase, clock_date)
            if kind not in WEATHER_FULLSCREEN_KINDS and kind != "steam_train_intro":
                if due_text:
                    self._text(due_text, due_x, 0, (255, 255, 255))
                if screen.get("stale"):
                    self._text("STALE", STALE_X, 0, (255, 20, 0))
                self._clear_rect(HEADER_SLOT_X, 0, DISPLAY_WIDTH, 8)
                item, offset = _header_item_state(phase, screen.get("weather"))
                if item == "weather":
                    self._header_weather(screen.get("weather"), offset)
                else:
                    self._text(clock_time, CLOCK_X + offset, 0, (255, 100, 0))
            self.pixels.show()

        print("\n[{}] {}".format(clock_time, screen.get("title") or screen.get("kind") or "screen"))
        if due_text:
            print(due_text)
        if kind == "steam_train_intro":
            print("STEAM TRAIN {}".format(screen.get("words") or ""))
        elif kind == "weather_weekly":
            days = screen.get("days") or []
            if not days:
                print("Weather unavailable")
            for day in days[:7]:
                print("{} {} {}".format(
                    str(day.get("weekday") or "---")[:3].upper(),
                    day.get("icon") or "unknown",
                    _weekly_temperature_text(day.get("temperature_max_c")),
                ))
        elif kind == "weather_today":
            for block in screen.get("blocks") or []:
                print("{} {} {}".format(
                    block.get("label") or "--",
                    block.get("icon") or "unknown",
                    _weekly_temperature_text(block.get("temperature_c")),
                ))
        elif kind == "weather_sun":
            print("SUNRISE {} SUNSET {}".format(
                screen.get("sunrise_time") or "--:--",
                screen.get("sunset_time") or "--:--",
            ))
        elif kind == "rail_combined":
            services = screen.get("services") or []
            if services:
                print(format_row(services[0]).rstrip())
                print(calling_text(services[0]))
                start, _, reset_progress = departure_scroll_state(
                    phase, len(services[1:]), screen.get("upcoming_train_pause_seconds")
                )
                if reset_progress is not None:
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
        elif kind == "flash":
            print(str(screen.get("label") or ""))
        weather = screen.get("weather")
        if kind not in WEATHER_FULLSCREEN_KINDS and isinstance(weather, dict):
            print("WEATHER {} {}".format(weather.get("icon") or "unknown", _weather_text(weather) or "--C"))
        if kind not in WEATHER_FULLSCREEN_KINDS and screen.get("stale"):
            print("STALE")

    def show_diagnostic(self, color):
        """Keep fixture mode observable when the hardware path is unavailable."""
        if self.pixels is not None:
            self.pixels.fill(_rgb_tuple(int(color)))
            self.pixels.show()
        print("DIAGNOSTIC 0x{:06X}".format(int(color)))


def create(settings):
    if settings.DISPLAY_BACKEND == "matrix":
        return MatrixDisplay(getattr(settings, "MATRIX_BRIGHTNESS_PERCENT", 100))
    return FixtureDisplay()
