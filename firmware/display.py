"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

import time

import board

from matrix_config import (
    MATRIX_BIT_DEPTH,
    MATRIX_EXPERIMENT_PRESET,
    MATRIX_PRESENTATION_MODE,
    MATRIX_REFRESH_FPS,
    MATRIX_STATS_INTERVAL_SECONDS,
    TODOIST_MARQUEE_PAUSE_SECONDS,
    TODOIST_MARQUEE_SPEED,
)

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
    calling_marquee_x,
    calling_text,
    departure_scroll_state,
    RAIL_ROW_Y,
    rail_phase,
    rail_phase_elapsed,
    rail_rows,
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
AGENDA_FIRST_Y = 8
AGENDA_ROW_HEIGHT = 8
WEATHER_ICON_WIDTH = 7
WEATHER_FONT_WIDTH = 5
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


def _header_content_right(screen):
    return max(0, (STALE_X if screen.get("stale") else HEADER_SLOT_X) - HEADER_GAP)


def _right_aligned_x(text, right_edge):
    return max(0, int(right_edge) - len(str(text or "")) * WEATHER_FONT_WIDTH)


def _left_text(text, right_edge):
    return _clip(text, max(0, int(right_edge) // WEATHER_FONT_WIDTH))


def _fit_text_pixels(text, width):
    return _clip(text, max(0, int(width) // WEATHER_FONT_WIDTH))


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
        print(
            "MATRIX PRESENTATION preset={} mode={} target_fps={} marquee_px_s={} auto_refresh={}".format(
                MATRIX_EXPERIMENT_PRESET,
                self.presentation_mode,
                MATRIX_REFRESH_FPS,
                TODOIST_MARQUEE_SPEED,
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
        self._todoist_page_seconds = None
        self._todoist_weather_icon = None
        self._todoist_weather_temp = None
        self._todoist_weather_stale = None
        self._todoist_clock_group = None
        self._todoist_clock_label = None
        self._todoist_weather_group = None

        # Departures use the same persistent-scene approach as Todoist.  Only
        # the calling-at labels move between frames; rebuilding the complete
        # four-panel scene is deliberately avoided.
        self._rail_group = None
        self._rail_services = None
        self._rail_title = None
        self._rail_stale = None
        self._rail_weather = None
        self._rail_calling_labels = []
        self._rail_phase = None
        self._rail_clock_group = None
        self._rail_clock_label = None
        self._rail_weather_group = None

    def _label(self, group, text, color, x, y):
        item = self.label_type(self.font, text=str(text), color=color, x=int(x), y=int(y))
        group.append(item)
        return item

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
            "heap_start={} heap_end={}".format(
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
            )
        )
        self._stats_last_report = now

    def _refresh(self):
        """Present one changed scene according to the issue #70 test mode."""
        self._stats_changes += 1

        # With auto-refresh enabled, mutating displayio objects is sufficient.
        # Calling refresh() here would make this mode no longer a clean test.
        if self.presentation_mode == "auto_refresh":
            self._maybe_report_stats()
            return True

        self._stats_refresh_attempts += 1
        target = None if self.presentation_mode == "immediate" else MATRIX_REFRESH_FPS
        refreshed = self.display.refresh(target_frames_per_second=target)
        now = time.monotonic()
        if refreshed:
            self._stats_refresh_successes += 1
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
        state = rail_phase(phase)
        rows = rail_rows(services, phase)
        self._rail_calling_labels = []
        for row_index, (row_kind, service) in enumerate(rows):
            y = RAIL_ROW_Y[row_index]
            if row_kind == "header":
                self._label(group, "DEPARTURES", 0xFFAA00, 0, y)
            elif row_kind == "service" and service is not None:
                ordinal = (1 if state == "calling" and row_index == 0 else
                            row_index + 1 if state == "summary" else
                            1 if row_index == 0 else 2)
                color = 0xFF3300 if service.get("cancelled") else 0xFFFFFF
                self._rail_service(group, service, color, 0, y, rail_right_edge, ordinal)
            elif row_kind == "calling":
                calling_group = displayio.Group()
                labels = [
                    self._label(calling_group, "", 0xFFAA00, 0, y),
                    self._label(calling_group, "", 0xFFAA00, 0, y),
                    self._label(calling_group, "", 0xFFAA00, 0, y),
                ]
                group.append(calling_group)
                self._rail_calling_labels.append(labels)
        self._rail_phase = state

    def _rail_cache_matches(self, screen):
        return (
            self._rail_group is not None
            and self._rail_services is screen.get("services")
            and self._rail_title == screen.get("title")
            and self._rail_stale == bool(screen.get("stale"))
            and self._rail_weather == screen.get("weather")
        )

    def _build_rail_scene(self, screen, clock_time, phase):
        """Build a departures scene once; animation mutates only child labels."""
        import displayio

        root = displayio.Group()
        self._rail(root, screen, phase)

        # Departures owns all four physical rows.  The generic header mask and
        # clock/weather overlay used by other screens would cover row 1.
        clock_group = displayio.Group()
        clock_label = self._label(clock_group, "", 0xFFAA00, CLOCK_X, 3)
        weather_group = displayio.Group()

        self._rail_group = root
        self._rail_services = screen.get("services")
        self._rail_title = screen.get("title")
        self._rail_stale = bool(screen.get("stale"))
        self._rail_weather = screen.get("weather")
        self._rail_clock_group = clock_group
        self._rail_clock_label = clock_label
        self._rail_weather_group = weather_group

    def _update_rail_scene(self, screen, clock_time, phase):
        """Update only the calling-at marquee and rotating header item."""
        changed = False
        scroll_speed, scroll_gap = _station_scroll_settings(screen)
        services = screen.get("services") or []
        for calling_index, labels in enumerate(self._rail_calling_labels):
            service = services[calling_index] if calling_index < len(services) else {}
            calling = calling_text(service)
            calling_x = calling_marquee_x(
                calling,
                rail_phase_elapsed(phase),
                display_width=DISPLAY_WIDTH,
                font_width=WEATHER_FONT_WIDTH,
                speed=scroll_speed,
                gap=scroll_gap,
            )
            segments = _calling_segments(calling, calling_x, scroll_gap) if calling_x is not None else ()
            values = [(0, CALLING_LABEL if calling_x is not None else "")]
            values.extend(segments)
            while len(values) < 3:
                values.append((0, ""))
            for label_item, (x, text) in zip(labels, values[:3]):
                if label_item.x != int(x):
                    label_item.x = int(x)
                    changed = True
                if label_item.text != str(text):
                    label_item.text = str(text)
                    changed = True

        if self._rail_clock_label.text != clock_time:
            self._rail_clock_label.text = clock_time
            changed = True
        item, offset = _header_item_state(time.monotonic(), screen.get("weather"))
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
        state = rail_phase(phase)
        if not self._rail_cache_matches(screen) or self._rail_phase != state:
            self._build_rail_scene(screen, clock_time, phase)
        changed = self._update_rail_scene(screen, clock_time, phase)
        if self.display.root_group is not self._rail_group:
            self.display.root_group = self._rail_group
            changed = True
        if changed:
            self._refresh()

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
            and self._todoist_events is screen.get("events")
            and self._todoist_clock_date == clock_date
            and self._todoist_title == screen.get("title")
            and self._todoist_stale == bool(screen.get("stale"))
            and self._todoist_viewport_size == max(1, int(screen.get("viewport_size") or AGENDA_VISIBLE_ROWS))
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

                self._label(title_group, title, 0xFFFFFF, 0, 0)
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
        self._todoist_page_seconds = screen.get("page_seconds") or 5
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

    def _todoist_page_transition_at(self, visible):
        """Delay page 2 until page-1 marquees finish and visibly settle."""
        try:
            minimum_page_seconds = max(0.0, float(self._todoist_page_seconds or 0))
        except (TypeError, ValueError):
            minimum_page_seconds = 0.0
        longest_scroll = 0.0
        for row in self._todoist_rows[:visible]:
            longest_scroll = max(
                longest_scroll,
                self._todoist_title_scroll_seconds(row[2], row[3]),
            )
        return (
            longest_scroll
            + (TODOIST_MARQUEE_PAUSE_SECONDS if longest_scroll else 0.0)
            + minimum_page_seconds
        )

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
        transition_at = None

        if event_count > visible:
            transition_at = self._todoist_page_transition_at(visible)
            if phase > transition_at:
                slide_elapsed = phase - transition_at
                if slide_elapsed + 1e-9 < AGENDA_SLIDE_SECONDS:
                    progress = min(1.0, slide_elapsed / AGENDA_SLIDE_SECONDS)
                    # During the slide, page 1 remains fully scrolled while
                    # page 2 enters at its initial, unscrolled title position.
                    page_phase = None
                else:
                    start = visible
                    page_phase = max(0.0, slide_elapsed - AGENDA_SLIDE_SECONDS)

        y_offset = int(progress * visible * AGENDA_ROW_HEIGHT + 1e-9)

        for index, row in enumerate(self._todoist_rows):
            row_group, title_group, title, visible_chars = row
            if progress > 0 and start <= index < start + visible * 2:
                y = AGENDA_FIRST_Y + (index - start) * AGENDA_ROW_HEIGHT - y_offset
            elif progress <= 0 and start <= index < start + visible:
                y = AGENDA_FIRST_Y + (index - start) * AGENDA_ROW_HEIGHT
            else:
                y = 64
            if row_group.y != y:
                row_group.y = y
                changed = True

            if progress > 0:
                if index < visible:
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

        item, offset = _header_item_state(time.monotonic(), screen.get("weather"))
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

        changed = self._update_todoist_scene(screen, clock_time, phase)
        if self.display.root_group is not self._todoist_group:
            self.display.root_group = self._todoist_group
            changed = True
        if changed:
            self._refresh()

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
        item, offset = _header_item_state(time.monotonic(), screen.get("weather"))
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
            rail_right_edge = _header_content_right(screen)
            state = rail_phase(phase)
            calling_number = 0
            for row_index, (row_kind, service) in enumerate(rail_rows(services, phase)):
                y = RAIL_ROW_Y[row_index]
                if row_kind == "header":
                    self._text("DEPARTURES", 0, y, (255, 170, 0))
                elif row_kind == "service" and service is not None:
                    ordinal = (1 if row_index == 0 else 2) if state == "calling" else row_index + 1
                    color = (255, 20, 0) if service.get("cancelled") else (255, 255, 255)
                    self._rail_service(service, color, 0, y, rail_right_edge, ordinal)
                elif row_kind == "calling" and service is not None:
                    text = calling_text(service)
                    scroll_speed, scroll_gap = _station_scroll_settings(screen)
                    calling_x = calling_marquee_x(text, rail_phase_elapsed(phase), display_width=DISPLAY_WIDTH,
                                                  font_width=WEATHER_FONT_WIDTH, speed=scroll_speed, gap=scroll_gap)
                    if calling_x is not None:
                        self._text(CALLING_LABEL, 0, y, (255, 170, 0))
                        for segment_x, segment in _calling_segments(text, calling_x, scroll_gap):
                            self._text(segment, segment_x, y, (255, 170, 0))
                    calling_number += 1
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
        if isinstance(weather, dict):
            print("WEATHER {} {}".format(weather.get("icon") or "unknown", _weather_text(weather) or "--C"))
        if screen.get("stale"):
            print("STALE")

    def show_diagnostic(self, color):
        """Keep fixture mode observable when the hardware path is unavailable."""
        if self.pixels is not None:
            self.pixels.fill(_rgb_tuple(int(color)))
            self.pixels.show()
        print("DIAGNOSTIC 0x{:06X}".format(int(color)))


def create(settings):
    return MatrixDisplay() if settings.DISPLAY_BACKEND == "matrix" else FixtureDisplay()
