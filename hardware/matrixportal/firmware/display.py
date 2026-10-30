"""Display backends: MatrixPortal S3 hardware and Wokwi visual fixture."""

from monotonic_clock import elapsed_seconds, ticks_ms

import board

from matrix_config import (
    MATRIX_ANIMATION_PROFILE,
    MATRIX_ANIMATION_PROFILES,
    MATRIX_BIT_DEPTH,
    MATRIX_EXPERIMENT_PRESET,
    MATRIX_RAIL_AUTO_REFRESH_EXPERIMENT,
    MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT,
    MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES,
    MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES,
    MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT,
    CALLING_SCROLL_SPEED_OVERRIDE,
    MATRIX_PRESENTATION_MODE,
    MATRIX_RAIL_ROWS_SCROLL,
    MATRIX_REFRESH_FPS,
    MATRIX_STATS_INTERVAL_SECONDS,
    MATRIX_TELEMETRY_ENABLED,
    STEAM_TRAIN_TEST_FPS,
    TODOIST_MARQUEE_PAUSE_SECONDS,
    TODOIST_MARQUEE_SPEED,
)

from brightness import BrightnessState, pixel_is_blocked
from bus_departures import normalise_bus_screen
from flash_events import assistant_message_page
from mqtt_screens import _epoch
from christmas_tracker import (
    SLEIGH_SLIDE_SECONDS, SLEIGH_START_X, SNOW_FLAKE_X,
    SNOW_FLAKE_SPEED, SNOW_FLAKE_START_Y, days_until_christmas,
)
from christmas_sleigh import HEIGHT as CHRISTMAS_SLEIGH_HEIGHT
from christmas_sleigh import PALETTE as CHRISTMAS_SLEIGH_PALETTE
from christmas_sleigh import PALETTE_INDEX as CHRISTMAS_SLEIGH_PALETTE_INDEX
from christmas_sleigh import WIDTH as CHRISTMAS_SLEIGH_WIDTH
from christmas_sleigh import draw as draw_christmas_sleigh
from christmas_sleigh import draw_indexed as draw_christmas_sleigh_indexed
from double_decker_bus import PALETTE as DOUBLE_DECKER_BUS_PALETTE
from double_decker_bus import PALETTE_8 as DOUBLE_DECKER_BUS_PALETTE_8
from double_decker_bus import PALETTE_INDEX as DOUBLE_DECKER_BUS_PALETTE_INDEX
from double_decker_bus import WIDTH as BUS_WIDTH
from double_decker_bus import HEIGHT as BUS_HEIGHT
from double_decker_bus import draw_indexed as draw_double_decker_bus_indexed
from double_decker_bus import draw as draw_double_decker_bus
from football_ball import (
    HEIGHT as FOOTBALL_BALL_HEIGHT,
    PALETTE as FOOTBALL_BALL_PALETTE,
    PALETTE_INDEX as FOOTBALL_BALL_PALETTE_INDEX,
    WIDTH as FOOTBALL_BALL_WIDTH,
    draw_indexed as draw_football_ball_indexed,
    draw_rolling_indexed as draw_football_rolling_indexed,
)
from football_screens import (
    FOOTBALL_END_X as FOOTBALL_RENDER_END_X,
    FOOTBALL_START_X,
    FOOTBALL_TEXT_X,
    football_presentation_position,
    football_slide_offset,
    football_roll_frame,
    football_due_in,
    football_countdown_x,
    football_screen_lines,
    football_team_name_span,
    football_team_name_color,
    FOOTBALL_TEAM_COLORS,
    FOOTBALL_FIXTURE_TEXT_COLOR,
)
from weather_sprites import PALETTE_8 as WEATHER_SPRITE_PALETTE_8
from weather_sprites import PALETTE_RGB as WEATHER_SPRITE_PALETTE_RGB
from weather_sprites import WEATHER_14 as WEATHER_SPRITES_14
from weather_sprites import CELESTIAL_21 as WEATHER_CELESTIAL_21

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
REMINDER_CLOCK_SIZE = 29
REMINDER_TEXT_X = 37
REMINDER_TEXT_SCALE = 3
REMINDER_SCROLL_SPEED = 64.0
REMINDER_SCROLL_GAP = 24
ASSISTANT_MESSAGE_TEXT_SCALE = 1
ASSISTANT_MESSAGE_TEXT_Y = 9
ASSISTANT_MESSAGE_CHAR_ADVANCE = 6  # font5x7 glyphs advance by five pixels plus one gap


def reminder_scroll_x(screen, phase):
    """Continuously move the clock/text train from right to left and wrap it."""
    label = str(screen.get("label") or "")
    if screen.get("title") == "ASSISTANT":
        label = "ASSISTANT: " + label
    width = REMINDER_TEXT_X + len(label) * WEATHER_FONT_WIDTH * REMINDER_TEXT_SCALE
    travel = DISPLAY_WIDTH + width + REMINDER_SCROLL_GAP
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    distance = int(elapsed * REMINDER_SCROLL_SPEED) % max(1, travel)
    return DISPLAY_WIDTH - distance


def reminder_clock_pixel(x, y):
    dx, dy = x - 14, y - 14
    return (156 <= dx * dx + dy * dy <= 205
            or (13 <= x <= 15 and 5 <= y <= 15)
            or (14 <= x <= 22 and 13 <= y <= 15))


def _bus_time(value):
    return value[11:16] if isinstance(value, str) and len(value) >= 16 else "--:--"


def _bus_minutes(planned, estimated):
    value = estimated or planned
    try:
        return max(0, int((_epoch(value) - _epoch(planned)) / 60000))
    except Exception:
        return None


def bus_due_label(item, now_epoch=None):
    """Rolling due-in countdown from the synced board clock, or feed fallback."""
    if item.get("cancelled"):
        return "CXL"
    if now_epoch is not None:
        try:
            remaining_ms = _epoch(item.get("estimated") or item.get("planned")) - int(now_epoch) * 1000
            if remaining_ms <= 60000:
                return "Due" if remaining_ms >= -60000 else "--"
            return "{}m".format(min(999, (remaining_ms + 59999) // 60000))
        except (ValueError, TypeError, OverflowError):
            pass
    return str(item.get("due_text") or "--")


def split_sl7_due_text(due):
    """Fit the explicit 'Due in' countdown inside a 128px SL7 column."""
    if due == "CXL":
        return "CXL"
    return "Due in {}".format("0m" if due == "Due" else str(due or "--")[:5])


def split_sl7_due_parts(due):
    """Separate the yellow countdown label from its white wait value."""
    if due == "CXL":
        return "CXL", ""
    return "Due in", "0m" if due == "Due" else str(due or "--")[:5]


def split_sl7_rows(screen, now_epoch=None):
    """Common compact layout contract for MatrixPortal and software tests."""
    data = screen.get("directions") or {}
    columns = []
    for stop, title, x in (("new-malden", "SL7 to Heathrow", 0),
                           ("heathrow", "SL7 to New Malden", 128)):
        direction = data.get(stop) or {}
        rows = []
        for item in direction.get("departures") or []:
            due = bus_due_label(item, now_epoch)
            # A fresh API snapshot can become old while the board is between
            # polls. Never leave a departure on screen once it is over a
            # minute past due; continue to the next upcoming row instead.
            if due == "--":
                continue
            rows.append((due, item.get("local_time") or "--:--",
                         bool(item.get("cancelled")),
                         bool(item.get("estimated") and item.get("estimated") != item.get("planned"))))
            if len(rows) >= 3:
                break
        columns.append((x, title, direction.get("status") or "unavailable",
                        bool(direction.get("stale")), rows))
    return columns


STEAM_TRAIN_WIDTH = 52
STEAM_TRAIN_HEIGHT = 26
STEAM_TRAIN_VERTICAL_OFFSET = 1
STEAM_TRAIN_TEXT_GAP = 8
BUS_PALETTE = (
    DOUBLE_DECKER_BUS_PALETTE_8 if MATRIX_BIT_DEPTH == 1
    else DOUBLE_DECKER_BUS_PALETTE
)
BUS_VERTICAL_OFFSET = 1
BUS_TEXT_GAP = 8
SL7_TIME_COLUMN_X = 2
SL7_DUE_COLUMN_X = 42
CLOCK_X = 231
HEADER_SLOT_X = 224
STALE_X = 190
QUEUE_FIRST_Y = 11
QUEUE_ROW_HEIGHT = 8
# The font label coordinate is a baseline. Start the three agenda rows lower
# so the final row uses the bottom of the 32px panel instead of leaving a
# visible unused band below it.
AGENDA_FIRST_Y = 11
AGENDA_ROW_HEIGHT = 8
WEATHER_FORECAST_ICON_SIZE = 14
TODAY_HEADER_ICON_SIZE = 22
TODAY_DATE_SCALE = 2
TODAY_DATE_CHAR_ADVANCE = 11
TODAY_DATE_COLOR_CYCLE_SECONDS = 5.0
TODAY_DATE_ANIMATION_FPS = 8
TODAY_DATE_BLEND_WIDTH = 24
TODAY_DATE_COLORS = (0x00D7FF, 0xD957FF, 0xFF9F43, 0x4BE0A2, 0x536DFF)
TODAY_DATE_DITHER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
TODAY_TIME_SCALE = 2
SUN_WEATHER_TIME_SCALE = 2
SUN_WEATHER_ICON_Y = 5
SUN_WEATHER_ANIMATION_SECONDS = 4.0
SUN_WEATHER_COLOR_SECONDS = 4.0
SUN_WEATHER_TOTAL_ANIMATION_SECONDS = SUN_WEATHER_ANIMATION_SECONDS * 2
# Begin the solar transition fully inside the 32px panel. Starting entirely
# offscreen made the values render alone for the first phase of the screen.
SUN_WEATHER_RISE_START_Y = 10
SUN_WEATHER_SET_START_Y = 0
# MatrixDisplay labels use font baselines, while the fixture renderer uses
# top-left pixel coordinates. Keep fullscreen weather headers clear of the
# panel edge and align the forecast rows below them.
WEATHER_HEADING_BASELINE_Y = 9
WEATHER_HEADING_PIXEL_Y = 2
WEEKLY_WEATHER_ICON_Y = 10
WEEKLY_WEATHER_TEMPERATURE_Y = 25
TODAY_WEATHER_ICON_Y = 11
TODAY_WEATHER_TEMPERATURE_Y = 27
TODAY_HEADER_ICON_X = 0
TODAY_HEADER_ICON_Y = 5
TODAY_DATE_Y = 10
TODAY_TIME_Y = 2
TODAY_TEMPERATURE_Y = 18
WEATHER_FULLSCREEN_KINDS = ("weather_weekly", "weather_today", "weather_sun")
NOVELTY_HEADING_Y = 3
NOVELTY_FIRST_LINE_Y = 12


def _novelty_lines(screen):
    """Wrap cached content without scrolling or clipping long words."""
    kind = screen.get("kind")
    message = str(screen.get("joke") if kind == "dad_joke" else screen.get("fact") if kind == "random_fact" else screen.get("insult") or "")
    lines, current = [], ""
    for word in message.split():
        # Split unusually long uninterrupted words rather than silently clipping.
        while len(word) > 42:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:42])
            word = word[42:]
        if not word:
            continue
        candidate = (current + " " + word).strip()
        if len(candidate) > 42 and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _novelty_page(screen, phase):
    """Advance longer facts across static pages during their reading slot."""
    lines = _novelty_lines(screen)
    if not lines:
        return []
    pages = (len(lines) + 2) // 3
    duration = max(1.0, float(screen.get("duration_seconds") or 15))
    page = min(pages - 1, int(max(0.0, float(phase)) * pages / duration))
    return lines[page * 3:page * 3 + 3]

def _quote_lines(screen):
    """Keep attribution only when quote and author fit on one three-line page."""
    quote = _novelty_lines({"kind": "dad_joke", "joke": screen.get("quote") or ""})
    author = _novelty_lines({"kind": "dad_joke", "joke": "- " + str(screen.get("author") or "")})
    return quote + author if len(quote) + len(author) <= 3 else quote


def _quote_page(screen, phase):
    lines = _quote_lines(screen)
    if not lines:
        return []
    pages = (len(lines) + 2) // 3
    duration = max(1.0, float(screen.get("duration_seconds") or 30))
    page = min(pages - 1, int(max(0.0, float(phase)) * pages / duration))
    return lines[page * 3:page * 3 + 3]


WEEKLY_WEATHER_TEXT_SCALE = 1
WEEKLY_WEATHER_GLYPH_WIDTH = 3
WEEKLY_WEATHER_GLYPHS = {
    "0": (7, 5, 5, 5, 7), "1": (2, 6, 2, 2, 7),
    "2": (7, 1, 7, 4, 7), "3": (7, 1, 7, 1, 7),
    "4": (5, 5, 7, 1, 1), "5": (7, 4, 7, 1, 7),
    "6": (7, 4, 7, 5, 7), "7": (7, 1, 2, 2, 2),
    "8": (7, 5, 7, 5, 7), "9": (7, 5, 7, 1, 7),
    "S": (7, 4, 7, 1, 7), "U": (5, 5, 5, 5, 7),
    "N": (5, 7, 7, 7, 5), "R": (6, 5, 6, 5, 5),
    "I": (7, 2, 2, 2, 7), "E": (7, 4, 6, 4, 7),
    "T": (7, 2, 2, 2, 2), ":": (0, 4, 0, 4, 0),
    "C": (3, 4, 4, 4, 3), "-": (0, 0, 7, 0, 0),
}
WEATHER_FONT_WIDTH = 5
WEATHER_GAP = 1
HEADER_GAP = 4
HEADER_SLOT_WIDTH = DISPLAY_WIDTH - HEADER_SLOT_X
CALLING_SCROLL_SPEED = 20.0
CALLING_SCROLL_GAP = 28
MIN_CALLING_SCROLL_SPEED = 10.0
MAX_CALLING_SCROLL_SPEED = 80.0
MIN_CALLING_SCROLL_GAP = 8
MAX_CALLING_SCROLL_GAP = 80
BIN_LORRY_SECONDS = 4.0
BIN_LORRY_SPEED = 64.0
BIN_LORRY_WIDTH = 84
BIN_LORRY_HEIGHT = 28
BIN_LORRY_Y = 4
RAIL_ORDINAL_X = 0
RAIL_TIME_X = 24
RAIL_DESTINATION_X = 63
RAIL_DESTINATION_TRACKING = 1
RAIL_PLATFORM_X = 154
RAIL_PLATFORM_WIDTH = 3 * WEATHER_FONT_WIDTH

WEATHER_SPRITE_ALIASES = {
    "clear_day": "sunny",
    "partly_cloudy_day": "partly_cloudy",
    "cloudy": "overcast",
    "storm": "thunderstorm",
}
WEATHER_SPRITE_PALETTE = (
    WEATHER_SPRITE_PALETTE_8 if MATRIX_BIT_DEPTH == 1 else WEATHER_SPRITE_PALETTE_RGB
)
WEATHER_SPRITE_CHAR_INDEX = {".": 0, "Y": 1, "O": 2, "W": 3, "C": 4, "B": 5, "D": 6, "R": 7, "M": 8}


def _weather_sprite_rows(icon_name):
    name = WEATHER_SPRITE_ALIASES.get(icon_name, icon_name)
    name = name if name in WEATHER_SPRITES_14 else "cloudy"
    return WEATHER_SPRITES_14[name]


def _celestial_sprite_rows(icon_name):
    return WEATHER_CELESTIAL_21["moon" if icon_name == "clear_night" else "sun"]


def _weather_sprite_color(symbol, stale=False):
    if symbol == ".":
        return 0x000000
    return 0x0000FF if stale else WEATHER_SPRITE_PALETTE[symbol]


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
        return None, None
    return str(weather.get("icon") or "unknown"), None


def _rail_weather_key(weather):
    """Return only weather fields that affect visible rail pixels."""
    if not isinstance(weather, dict):
        return None
    icon_name, _ = _weather_icon(weather)
    return (_weather_text(weather), icon_name, bool(weather.get("stale")))


def _periodic_boundary_delta(within, boundary, cycle):
    """Return the positive delta to one edge in a repeating cycle."""
    delta = (float(boundary) % cycle) - within
    if delta <= 1e-6:
        delta += cycle
    return delta


def _next_departure_rows_boundary(elapsed, max_start, pause_seconds):
    """Find the next lower-row motion edge without allocating edge lists."""
    step = pause_seconds + DEPARTURE_SLIDE_SECONDS
    normal = (max_start + 1) * step
    reset_start = normal + DEPARTURE_RESET_GAP_SECONDS
    cycle = reset_start + DEPARTURE_RESET_SLIDE_SECONDS
    within = max(0.0, float(elapsed or 0)) % cycle
    nearest = cycle - within
    delta = _periodic_boundary_delta(within, normal, cycle)
    if delta < nearest:
        nearest = delta
    delta = _periodic_boundary_delta(within, reset_start, cycle)
    if delta < nearest:
        nearest = delta
    for index in range(max_start + 1):
        edge = index * step + pause_seconds
        delta = _periodic_boundary_delta(within, edge, cycle)
        if delta < nearest:
            nearest = delta
        delta = _periodic_boundary_delta(
            within, edge + DEPARTURE_SLIDE_SECONDS, cycle
        )
        if delta < nearest:
            nearest = delta
    return nearest


def _next_calling_marquee_boundary(elapsed, travel, cycle):
    """Find the next marquee edge without allocating a boundary collection."""
    within = max(0.0, float(elapsed or 0)) % cycle
    nearest = cycle - within
    delta = _periodic_boundary_delta(within, travel, cycle)
    if delta < nearest:
        nearest = delta
    return nearest


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
        icon_width = WEATHER_FORECAST_ICON_SIZE
        maximum_width = len(maximum) * (WEEKLY_WEATHER_GLYPH_WIDTH + 1) * WEEKLY_WEATHER_TEXT_SCALE
        icon_name, _ = _weather_icon(day)

        def centered_x(text, pixel_width):
            return left + max(0, (width - pixel_width) // 2)

        layout.append({
            "index": index,
            "left": left,
            "right": right,
            "weekday": weekday,
            "weekday_x": centered_x(weekday, len(weekday) * WEATHER_FONT_WIDTH),
            "icon_name": icon_name,
            "sprite_rows": _weather_sprite_rows(icon_name),
            "icon_x": centered_x("", icon_width),
            "max_text": maximum,
            "max_x": left + max(0, (width - maximum_width) // 2),
            "icon_width": icon_width,
        })
    return layout


def _sun_weather_progress(phase):
    """Return the bounded entry-animation progress for the solar icons."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    return min(1.0, elapsed / SUN_WEATHER_ANIMATION_SECONDS)


def _sun_weather_animation_active(phase):
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    return elapsed < SUN_WEATHER_TOTAL_ANIMATION_SECONDS


def _sun_weather_local_phase(icon_name, phase):
    """Return the phase for one solar event in the sequential animation."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    if icon_name == "clear_night":
        elapsed -= SUN_WEATHER_ANIMATION_SECONDS
    return min(SUN_WEATHER_ANIMATION_SECONDS, max(0.0, elapsed))


def _bin_collection_footer_x(screen, phase, clock_date=""):
    """Slide the lorry in, then keep the lorry and clipped footer parked."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    if elapsed < BIN_LORRY_SECONDS:
        return _bin_lorry_x(elapsed)
    return 0


def _bin_collection_motion_state(screen, phase):
    """Report only the lorry entrance as animation; the completed footer parks."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    if elapsed < BIN_LORRY_SECONDS:
        return True, max(0.05, BIN_LORRY_SECONDS - elapsed)
    return False, None


def _bin_collection_lorry_kind(screen):
    """Choose the matching recycling lorry for the next collection."""
    items = screen.get("collections") or []
    ids = " ".join(str(item.get("id") or "").lower() for item in items)
    labels = " ".join(str(item.get("label") or "").lower() for item in items)
    return "paper" if "paper" in ids or "paper" in labels else "plastic_glass"


def _date_ordinal(value):
    """Convert a strict YYYY-MM-DD date to a Gregorian day number."""
    if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
        return None
    if not (value[:4].isdigit() and value[5:7].isdigit() and value[8:10].isdigit()):
        return None
    try:
        year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
    except ValueError:
        return None
    if year < 1 or not 1 <= month <= 12:
        return None
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    month_lengths = (31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    if not 1 <= day <= month_lengths[month - 1]:
        return None
    previous_year = year - 1
    days = previous_year * 365 + previous_year // 4 - previous_year // 100 + previous_year // 400
    days += sum(month_lengths[:month - 1]) + day - 1
    return days


def _bin_collection_due_label(collection_date, today):
    due_day = _date_ordinal(collection_date)
    today_day = _date_ordinal(today)
    if due_day is None or today_day is None:
        return "DUE DATE UNKNOWN"
    days_until = due_day - today_day
    if days_until < 0:
        return "OVERDUE"
    if days_until == 0:
        return "DUE TODAY"
    if days_until == 1:
        return "DUE IN 1 DAY"
    return "DUE IN {} DAYS".format(days_until)


def _bin_lorry_x(phase):
    """Slide a compact refuse lorry across the board from right to left."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    return int(round(DISPLAY_WIDTH - elapsed * BIN_LORRY_SPEED))


def _format_sun_time(value):
    """Keep the time separator visible and normalize compact HHMM values."""
    text = str(value or "--:--")
    if len(text) == 4 and text.isdigit():
        return text[:2] + ":" + text[2:]
    return text


def _sun_weather_icon_y(icon_name, phase):
    """Slide sunrise upward and sunset downward to their shared resting row."""
    progress = _sun_weather_progress(_sun_weather_local_phase(icon_name, phase))
    # Smoothstep eases the icons into their final row instead of moving at a
    # constant speed and stopping abruptly. The clamped endpoint remains on
    # the panel for the rest of this screen's duration.
    progress = progress * progress * (3.0 - 2.0 * progress)
    if icon_name == "clear_day":
        start_y = SUN_WEATHER_RISE_START_Y
    elif icon_name == "clear_night":
        start_y = SUN_WEATHER_SET_START_Y
    else:
        return SUN_WEATHER_ICON_Y
    rest_y = SUN_WEATHER_ICON_Y
    return int(round(start_y + (rest_y - start_y) * progress))


def _sun_weather_color_progress(phase):
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    progress = min(1.0, elapsed / SUN_WEATHER_COLOR_SECONDS)
    return progress * progress * (3.0 - 2.0 * progress)


def _sun_weather_rise_label_color(index, phase, stale=False):
    if stale:
        return 0x777777
    progress = _sun_weather_color_progress(_sun_weather_local_phase("clear_day", phase))
    yellow_letters = min(7, int(progress * 8))
    return 0xFFFF00 if index < yellow_letters else 0x0000FF


def _sun_weather_set_label_color(index, phase, stale=False):
    progress = _sun_weather_color_progress(_sun_weather_local_phase("clear_night", phase))
    # Reveal one additional sunset letter at a time from yellow to blue.
    blue_letters = min(6, int(progress * 7))
    if index < blue_letters:
        return 0x777777 if stale else 0x0000FF
    return 0x777777 if stale else 0xFFAA00


def _today_weather_layout(blocks, display_width=DISPLAY_WIDTH):
    """Build six rolling four-hour Weather columns beginning with Now."""
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
        icon_name, _ = _weather_icon(block)
        icon_width = WEATHER_FORECAST_ICON_SIZE
        temp_width = len(temperature) * (WEEKLY_WEATHER_GLYPH_WIDTH + 1)
        layout.append({
            "left": left,
            "right": right,
            "label": label,
            "label_x": left + max(0, (width - len(label) * WEATHER_FONT_WIDTH) // 2),
            "icon_name": icon_name,
            "sprite_rows": _weather_sprite_rows(icon_name),
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
    if CALLING_SCROLL_SPEED_OVERRIDE is not None:
        try:
            # The board-local experiment intentionally sits outside the
            # admin-configured minimum, so do not clamp it back to 10 px/s.
            speed = max(1.0, float(CALLING_SCROLL_SPEED_OVERRIDE))
        except (TypeError, ValueError):
            speed = CALLING_SCROLL_SPEED
    else:
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


def _cached_calling_x(phase, station_width, speed, calling_seconds):
    """Calculate the production calling position with integer timing math."""
    try:
        speed_int = int(speed)
        phase_ms = int(max(0.0, float(phase or 0)) * 1000.0)
        calling_ms = int(max(0.1, float(calling_seconds)) * 1000.0)
    except (TypeError, ValueError):
        return None
    if speed_int <= 0 or speed_int != speed or calling_ms <= 0:
        return None
    prefix_width = len(CALLING_LABEL) * WEATHER_FONT_WIDTH
    travel_ms = ((DISPLAY_WIDTH - prefix_width + int(station_width)) * 1000 + speed_int - 1) // speed_int
    within_ms = (phase_ms % calling_ms) % (travel_ms + int(CALLING_MARQUEE_PAUSE_SECONDS * 1000))
    if within_ms >= travel_ms:
        return prefix_width - int(station_width)
    return DISPLAY_WIDTH - (within_ms * speed_int) // 1000


def _header_item_state(phase, weather):
    """Keep the clock in the header; weather is shown on forecast screens."""
    return "clock", 0


def _header_slide_active(phase, weather):
    """The clock/weather slot switches at rest and has no moving interval."""
    return False


def _header_next_boundary_seconds(phase, weather):
    return 60.0


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


def _today_lines(screen, clock_time, clock_date):
    weather = screen.get("weather") or {}
    temperature = weather.get("temperature_c")
    temperature = "--C" if temperature is None else "{}C".format(int(round(temperature)))
    return ["{}   {}".format(clock_time, temperature), _today_date_label(clock_date)]


def _today_date_label(clock_date):
    """Format an ISO date as a UK weekday and day/month/year label."""
    value = str(clock_date or "")
    try:
        year, month, day = [int(part) for part in value[:10].split("-")]
        # Gregorian weekday calculation; 0 is Sunday.
        offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
        adjusted_year = year - (1 if month < 3 else 0)
        weekday = (adjusted_year + adjusted_year // 4 - adjusted_year // 100
                   + adjusted_year // 400 + offsets[month - 1] + day) % 7
        names = ("SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY")
        return "{} {:02d}/{:02d}/{:04d}".format(names[weekday], day, month, year)
    except (ValueError, IndexError, TypeError):
        return value[:42]


def _today_compact_date_label(clock_date):
    """Return a compact UK date with the full weekday name."""
    full_label = _today_date_label(clock_date)
    parts = full_label.split()
    if len(parts) != 2 or "/" not in parts[1]:
        return full_label[:10]
    try:
        day, month, _year = parts[1].split("/")
        month_name = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                      "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")[int(month) - 1]
        return "{} {} {}".format(parts[0], day, month_name)
    except (ValueError, IndexError):
        return full_label[:10]


def _today_date_position(date_label, clock_time):
    date_width = _today_date_width(len(date_label))
    left = TODAY_HEADER_ICON_X + TODAY_HEADER_ICON_SIZE + 1
    right = max(0, DISPLAY_WIDTH - len(clock_time) * 6 * TODAY_TIME_SCALE + 10)
    return left + max(0, (right - left - date_width) // 2)


def _today_date_width(character_count):
    return max(1, (character_count - 1) * TODAY_DATE_CHAR_ADVANCE + 6 * TODAY_DATE_SCALE)


def _today_date_sweep_position(phase, width):
    """A constant-speed front; consecutive sweeps overlap at the date edges."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    return elapsed * width / TODAY_DATE_COLOR_CYCLE_SECONDS


def _today_date_column_state(position, width, x):
    distance = position - x
    if distance < 0:
        return 0  # Initial white, before the first front arrives.
    cycle = int(distance // width)
    blend = min(TODAY_DATE_BLEND_WIDTH, int(distance - cycle * width))
    return 1 + cycle * (TODAY_DATE_BLEND_WIDTH + 1) + blend


def _today_date_blend_color(state):
    if state == 0:
        return 0xFFFFFF
    cycle, blend = divmod(state - 1, TODAY_DATE_BLEND_WIDTH + 1)
    old = 0xFFFFFF if cycle == 0 else TODAY_DATE_COLORS[(cycle - 1) % len(TODAY_DATE_COLORS)]
    new = TODAY_DATE_COLORS[cycle % len(TODAY_DATE_COLORS)]
    color = 0
    for shift in (16, 8, 0):
        first, last = (old >> shift) & 255, (new >> shift) & 255
        channel = (first * (TODAY_DATE_BLEND_WIDTH - blend) + last * blend) // TODAY_DATE_BLEND_WIDTH
        color |= channel << shift
    return color


def _today_date_pixel_color(color, x, y):
    """Fixed ordered dithering, expressed in the panel's one-bit RGB gamut."""
    threshold = (TODAY_DATE_DITHER[(y & 3) * 4 + (x & 3)] * 2 + 1) * 255
    return ((0xFF0000 if ((color >> 16) & 255) * 32 > threshold else 0)
            | (0x00FF00 if ((color >> 8) & 255) * 32 > threshold else 0)
            | (0x0000FF if (color & 255) * 32 > threshold else 0))


class MatrixDisplay:
    def __init__(self, brightness_percent=100, steam_train_test=False):
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
        self._rail_auto_refresh_override = False
        self.telemetry_enabled = MATRIX_TELEMETRY_ENABLED
        self.display = framebufferio.FramebufferDisplay(
            matrix,
            auto_refresh=self.presentation_mode == "auto_refresh",
        )
        self.steam_train_test = bool(steam_train_test)
        self.display.root_group = displayio.Group()
        self._last_present_refresh = None
        self._refresh_misses = 0
        self._rail_first_refresh_pending = False
        self._rail_build_started_ms = None

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
        now = ticks_ms()
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
        self._stats_rail_slow_updates = 0
        self._stats_rail_gc_events = 0
        self._stats_rail_refresh_heap_gain_max = 0
        self._last_rail_update_seconds = 0.0
        self._last_rail_refresh_seconds = 0.0
        self._last_rail_heap_gain = None
        self._stats_fetch_on_animation_capable_screen = 0
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
                "steam_train",
                "weather_sun_slide",
                "today_date",
                "football_goal",
                "football_entry",
                "football_team_color",
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
        self._novelty_key = None
        self._novelty_group = None
        self._novelty_clock_group = None
        self._novelty_clock_label = None
        self._novelty_weather_group = None
        self._football_group = None
        self._football_labels = []
        self._football_pregame_tiles = []
        self._football_pregame_palettes = []
        self._football_key = None
        self._football_info_group = None
        self._football_ball_grid = None
        self._football_slots = None
        self._football_rotation_bitmaps = None
        self._football_current = None
        self._football_outgoing = None
        self._football_screen_id = None
        self._football_previous_phase = None
        self._football_previous_animation_speed = None

        # Weather pages are static while visible. Keep their displayio trees
        # alive instead of allocating new icon bitmaps and palettes on every
        # scheduler tick; repeated scene construction can starve the heap and
        # leave text visible while tile art fails to refresh reliably.
        self._weather_groups = {}
        self._weather_keys = {}

        # Departures use the same persistent-scene approach as Todoist.  Only
        # the calling-at labels move between frames; rebuilding the complete
        # four-panel scene is deliberately avoided.
        self._rail_scenes = {}
        self._rail_group = None
        self._rail_services = None
        self._rail_title = None
        self._rail_stale = None
        self._rail_weather = None
        self._rail_presentation = None
        self._rail_calling_seconds_cached = None
        self._rail_summary_seconds_cached = None
        self._rail_station_speed_cached = None
        self._rail_station_spacing_cached = None
        self._rail_rows_scroll_cached = None
        self._rail_pause_seconds_cached = None
        self._rail_static_rows_bitmap_cached = None
        self._rail_prebuilt_pending = False
        self._rail_static_row_bitmap_count = 0
        self._rail_retained_heap_cost = None
        self._rail_calling_labels = []
        self._rail_departure_rows = []
        self._rail_summary_header_group = None
        self._rail_top_service_group = None
        self._rail_calling_group = None
        self._rail_departure_active_start = None
        self._rail_departure_active_count = 0
        self._rail_scroll_speed = CALLING_SCROLL_SPEED
        self._rail_scroll_gap = CALLING_SCROLL_GAP
        self._rail_calling_seconds = RAIL_CALLING_SECONDS
        self._rail_summary_seconds = RAIL_SUMMARY_SECONDS
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
        self._bus_intro_group = None
        self._bus_intro_motion_group = None
        self._bus_intro_words = None
        self._bus_intro_speed = None
        self._christmas_intro_group = None
        self._christmas_intro_motion = None
        self._christmas_group = None
        self._christmas_snow_grid = None
        self._christmas_snow_bitmap = None
        self._christmas_countdown = None
        self._christmas_days = None
        self._christmas_flakes = None
        self._christmas_snow_visible = False

        # The solar-times screen only animates its two icon TileGrids. Keep
        # the scene alive during the short entry transition so the physical
        # board does not rebuild the complete display tree every frame.
        self._sun_group = None
        self._sun_key = None
        self._sun_icon_grids = ()
        self._sun_label_grids = ()

        # MQTT collection labels can scroll for the full screen duration.
        # Keep their labels and header scene persistent across frames.
        self._bin_group = None
        self._bin_key = None
        self._bin_weather = None
        self._bin_header_kind = None
        self._bin_label = None
        self._bin_title = None
        self._bin_date_group = None
        self._bin_date = None
        self._bin_footer_group = None
        self._bin_stale = None
        self._bin_clock_label = None
        self._bin_header_group = None
        self._bin_content_group = None
        self._bin_lorry_group = None
        self._bin_lorry_grid = None
        self._bin_lorry_label = None
        self._today_date_palette = None
        self._today_date_column_states = []

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

    def set_brightness_percent(self, percent):
        """Apply the persisted display brightness received from the screen API."""
        next_percent, changed = self._brightness.set(percent)
        if not changed:
            return next_percent
        self._render_brightness_overlay()
        if self._brightness_overlay_parent is not None:
            self._refresh()
        print("BRIGHTNESS {}% (admin)".format(next_percent))
        return next_percent

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

    def _scaled_label(self, group, text, color, x, y, scale=3):
        """Draw font glyphs into a scaled bitmap for the compact train intro."""
        import displayio

        if not hasattr(self.font, "get_glyph"):
            return self._label(group, text, color, x, y + 9)
        text = str(text)
        if hasattr(self.font, "load_glyphs"):
            self.font.load_glyphs(set(ord(character) for character in text))
        ascent = getattr(self.font, "ascent", None)
        if ascent is None:
            ascent = self.font.get_bounding_box()[1]
        y_offset = ascent // 2
        glyphs = []
        cursor_x = min_x = min_y = 0
        max_x = max_y = 0
        for character in text:
            glyph = self.font.get_glyph(ord(character))
            if glyph is None:
                continue
            glyph_x = cursor_x + glyph.dx
            glyph_y = -glyph.height - glyph.dy + y_offset
            glyphs.append((glyph, glyph_x, glyph_y))
            min_x = min(min_x, glyph_x)
            max_x = max(max_x, glyph_x + glyph.width)
            min_y = min(min_y, glyph_y)
            max_y = max(max_y, glyph_y + glyph.height)
            cursor_x += glyph.shift_x
        width = max(1, max(max_x, cursor_x) - min_x)
        height = max(1, max_y - min_y)
        bitmap = displayio.Bitmap(width * scale, height * scale, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = color
        for glyph, glyph_x, glyph_y in glyphs:
            for gy in range(glyph.height):
                for gx in range(glyph.width):
                    if glyph.bitmap[gx, gy]:
                        for dy in range(scale):
                            for dx in range(scale):
                                bitmap[(glyph_x - min_x + gx) * scale + dx,
                                       (glyph_y - min_y + gy) * scale + dy] = 1
        tile = displayio.TileGrid(bitmap, pixel_shader=palette,
                                  x=int(x), y=int(y))
        group.append(tile)
        return tile

    def _today_date_bitmap(self, group, text, x):
        """Cache the existing glyph geometry with one palette index per column/row phase."""
        import displayio

        self.font.load_glyphs(set(ord(character) for character in text))
        ascent = getattr(self.font, "ascent", None)
        if ascent is None:
            ascent = self.font.get_bounding_box()[1]
        glyphs = []
        height = 1
        for index, character in enumerate(text):
            glyph = self.font.get_glyph(ord(character))
            if glyph is None:
                continue
            # Match _scaled_label's per-character normalization exactly.
            gx = glyph.dx - min(0, glyph.dx)
            gy = -glyph.height - glyph.dy + ascent // 2
            gy -= min(0, gy)
            glyphs.append((glyph, index * TODAY_DATE_CHAR_ADVANCE + gx * TODAY_DATE_SCALE,
                           gy * TODAY_DATE_SCALE))
            height = max(height, (gy + glyph.height) * TODAY_DATE_SCALE)
        width = _today_date_width(len(text))
        palette = displayio.Palette(1 + width * 4)
        palette.make_transparent(0)
        bitmap = displayio.Bitmap(width, height, len(palette))
        for glyph, start_x, start_y in glyphs:
            for gy in range(glyph.height):
                for gx in range(glyph.width):
                    if not glyph.bitmap[gx, gy]:
                        continue
                    for dy in range(TODAY_DATE_SCALE):
                        for dx in range(TODAY_DATE_SCALE):
                            px = start_x + gx * TODAY_DATE_SCALE + dx
                            py = start_y + gy * TODAY_DATE_SCALE + dy
                            bitmap[px, py] = 1 + px * 4 + (py & 3)
        group.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=TODAY_DATE_Y))
        self._today_date_palette = palette
        self._today_date_column_states = [-1] * width

    def _update_today_date_colors(self, phase):
        """Mutate only columns whose quantized blend changed; never redraw glyphs."""
        states = self._today_date_column_states
        width = len(states)
        position = _today_date_sweep_position(phase, width)
        changed = False
        palette = self._today_date_palette
        for x in range(width):
            state = _today_date_column_state(position, width, x)
            if state == states[x]:
                continue
            states[x] = state
            color = _today_date_blend_color(state)
            for row in range(4):
                index = 1 + x * 4 + row
                value = _today_date_pixel_color(color, x, row)
                if palette[index] != value:
                    palette[index] = value
                    changed = True
        return changed

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
        glyph_cache = {}
        cursor_x = 0
        min_x = 0
        max_x = 0
        min_y = 0
        max_y = 0
        for text, color in segments:
            color_index = 1 if color == 0xFFFFFF else 2
            for character in text:
                codepoint = ord(character)
                if codepoint not in glyph_cache:
                    glyph_cache[codepoint] = self.font.get_glyph(codepoint)
                glyph = glyph_cache[codepoint]
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
            interval = max(0.0, elapsed_seconds(self._stats_last_success, now))
            if self._stats_interval_min is None or interval < self._stats_interval_min:
                self._stats_interval_min = interval
            if self._stats_interval_max is None or interval > self._stats_interval_max:
                self._stats_interval_max = interval
            self._stats_interval_total += interval
            self._stats_interval_count += 1
        self._stats_last_success = now

    def _maybe_report_stats(self):
        if not self.telemetry_enabled:
            return
        now = ticks_ms()
        if elapsed_seconds(self._stats_last_report, now) < MATRIX_STATS_INTERVAL_SECONDS:
            return
        elapsed = max(0.001, elapsed_seconds(self._stats_started, now))
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
            "fetch_on_animation_capable_screen={} cadence_switches={} "
            "todoist_marquee_ticks={} todoist_marquee_changed={} "
                "todoist_page_slide_ticks={} todoist_page_slide_changed={} "
                "todoist_marquee_update_max={} todoist_marquee_refresh_max={} "
                "todoist_page_update_max={} todoist_page_refresh_max={} "
                "header_slide_ticks={} header_slide_changed={} "
                "header_slide_update_max={} header_slide_refresh_max={} "
                "departures_calling_ticks={} departures_calling_changed={} "
                "departures_calling_update_max={} departures_calling_refresh_max={} "
                "steam_train_ticks={} steam_train_changed={} "
                "steam_train_update_max={} steam_train_refresh_max={} "
                "departures_update_heap_gain={} departures_refresh_heap_gain={} "
                "rail_slow_updates={} rail_gc_events={} "
                "today_date_ticks={} today_date_changed={} "
                "today_date_update_max={} today_date_refresh_max={}".format(
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
                self._stats_fetch_on_animation_capable_screen,
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
                self._stats_animation_classes["steam_train"]["ticks"],
                self._stats_animation_classes["steam_train"]["changed"],
                "{:.4f}".format(self._stats_animation_classes["steam_train"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["steam_train"]["refresh_max"]),
                self._stats_rail_update_heap_gain_max,
                self._stats_rail_refresh_heap_gain_max,
                self._stats_rail_slow_updates,
                self._stats_rail_gc_events,
                self._stats_animation_classes["today_date"]["ticks"],
                self._stats_animation_classes["today_date"]["changed"],
                "{:.4f}".format(self._stats_animation_classes["today_date"]["update_max"]),
                "{:.4f}".format(self._stats_animation_classes["today_date"]["refresh_max"]),
            )
        )
        self._stats_last_report = now

    def note_fetch_on_animation_capable_screen(self):
        """Record a fetch on a screen that supports animation, not overlap."""
        self._stats_fetch_on_animation_capable_screen += 1

    def note_fetch_overlap(self):
        """Preserve compatibility with the previous internal adapter method."""
        self.note_fetch_on_animation_capable_screen()

    def note_cadence_switch(self):
        self._stats_cadence_switches += 1

    def _animation_class(self, screen, phase):
        """Return the active animation class without changing its cadence."""
        if not isinstance(screen, dict):
            return None
        kind = screen.get("kind")
        if kind == "football_score":
            x, _ = football_presentation_position(
                phase, animate=screen.get("status") != "IN",
                animation_speed=screen.get("animation_speed")
            )
            if x > FOOTBALL_RENDER_END_X:
                return "football_entry"
            if screen.get("goal_flash_active") and screen.get("status") == "IN":
                return "football_goal"
            if screen.get("status") == "IN":
                return "football_team_color"
        if kind == "flash":
            return "queue_rows"
        if kind == "today":
            return "today_date"
        if kind == "calendar_agenda" and screen.get("source") == "todoist":
            if self._todoist_rows and self._todoist_page_slide_active(phase):
                return "todoist_page_slide"
            if _header_slide_active(phase, screen.get("weather")):
                return "header_slide"
            if self._todoist_rows and self._todoist_titles_moving(phase):
                return "todoist_marquee"
            return None
        if kind == "steam_train_intro":
            return "steam_train"
        if kind == "bus_intro":
            return "steam_train"
        if kind == "christmas_tracker":
            return "christmas_tracker"
        if kind == "christmas_tracker_intro":
            return "steam_train"
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
        if kind == "weather_sun" and _sun_weather_animation_active(phase):
            return "weather_sun_slide"
        if kind == "bin_collection":
            moving, _ = _bin_collection_motion_state(screen, phase)
            if moving:
                return "todoist_marquee"
            if _header_slide_active(phase, screen.get("weather")):
                return "header_slide"
        return None

    def animation_cadence(self, screen, phase):
        """Return the desired update cadence for the active partial scene."""
        if screen.get("kind") == "today":
            return min(TODAY_DATE_ANIMATION_FPS, MATRIX_REFRESH_FPS)
        if screen.get("kind") == "christmas_tracker":
            return MATRIX_ANIMATION_PROFILES[MATRIX_ANIMATION_PROFILE]["christmas_tracker"]
        if screen.get("kind") in ("dad_joke", "random_fact", "insult_of_hour", "quotes"):
            return 0
        if (
            isinstance(screen, dict)
            and screen.get("kind") == "steam_train_intro"
            and getattr(self, "steam_train_test", False)
        ):
            return STEAM_TRAIN_TEST_FPS
        if (
            isinstance(screen, dict)
            and screen.get("kind") == "bin_collection"
            and self._animation_class(screen, phase) is None
        ):
            return 0
        if (
            isinstance(screen, dict)
            and screen.get("kind") == "rail_combined"
            and self._animation_class(screen, phase) is None
        ):
            return 0
        animation_class = self._animation_class(screen, phase)
        if animation_class == "football_team_color":
            return 1
        if MATRIX_ANIMATION_PROFILE == "baseline":
            return MATRIX_REFRESH_FPS
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
        if kind == "today":
            return 1.0  # Update the clock without animating or rebuilding unchanged text.
        if kind == "football_score" and screen.get("status") == "PRE":
            return 1.0  # Wake for the next real-second countdown tick after arrival.
        if kind == "football_score" and screen.get("status") == "IN":
            return 1.0  # Keep the live clock and slow team-colour cycle current.
        if kind in ("dad_joke", "random_fact", "insult_of_hour", "quotes"):
            lines = _quote_lines(screen) if kind == "quotes" else _novelty_lines(screen)
            pages = max(1, (len(lines) + 2) // 3)
            duration = max(1.0, float(screen.get("duration_seconds") or 15))
            page_seconds = duration / pages
            return max(0.05, page_seconds - (max(0.0, phase) % page_seconds))
        if kind == "bin_collection":
            moving, gap_remaining = _bin_collection_motion_state(screen, phase)
            if not moving and gap_remaining is not None:
                return gap_remaining
            if gap_remaining is None:
                return max(0.05, _header_next_boundary_seconds(phase, screen.get("weather")))
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
            nearest = _header_next_boundary_seconds(phase, screen.get("weather"))
            try:
                value = max(0.0, float(phase or 0))
            except (TypeError, ValueError):
                value = 0.0
            cycle = summary_seconds + calling_seconds
            within = value % cycle
            if rail_phase(phase, summary_seconds, calling_seconds) == "summary":
                delta = summary_seconds - within
                if delta < nearest:
                    nearest = delta
            else:
                delta = cycle - within
                if delta < nearest:
                    nearest = delta
                calling_elapsed = rail_marquee_elapsed(phase, summary_seconds, calling_seconds)
                services = screen.get("services") or ()
                upcoming_count = max(0, len(services) - 1)
                pause = max(0.0, float(screen.get("upcoming_train_pause_seconds", 2) or 0))
                max_start = max(0, upcoming_count - 2)
                if max_start and MATRIX_RAIL_ROWS_SCROLL:
                    delta = _next_departure_rows_boundary(
                        calling_elapsed, max_start, pause
                    )
                    if delta < nearest:
                        nearest = delta
                if services:
                    speed, _ = _station_scroll_settings(screen)
                    prepared = screen.get("rail_presentation") or {}
                    travel = prepared.get("calling_travel_seconds", screen.get("_calling_travel_seconds"))
                    if travel is None:
                        travel = rail_calling_timing(
                            services, speed, font_width=WEATHER_FONT_WIDTH
                        )[0]
                    marquee_cycle = travel + CALLING_MARQUEE_PAUSE_SECONDS
                    delta = _next_calling_marquee_boundary(
                        calling_elapsed, travel, marquee_cycle
                    )
                    if delta < nearest:
                        nearest = delta
            return max(0.05, nearest)
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
        if not self.telemetry_enabled:
            return
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
        if not self.telemetry_enabled:
            if self.presentation_mode == "auto_refresh" or self.display.auto_refresh:
                if animation_class == "departures_calling":
                    self._last_rail_refresh_seconds = 0.0
                    if self._rail_first_refresh_pending:
                        print("RAIL FIRST REFRESH AUTO heap_free={}".format(self._heap_free()))
                        self._rail_first_refresh_pending = False
                return True
            target = None if self.presentation_mode == "immediate" else MATRIX_REFRESH_FPS
            if animation_class == "departures_calling":
                probe_first_refresh = self._rail_first_refresh_pending
                if probe_first_refresh:
                    print(
                        "RAIL FIRST REFRESH START mode={} scene_ready_to_present_ms={} heap_free={}".format(
                            self.presentation_mode,
                            ticks_ms() - self._rail_build_started_ms
                            if self._rail_build_started_ms is not None else None,
                            self._heap_free()
                        )
                    )
                refresh_started = ticks_ms()
                refreshed = self.display.refresh(target_frames_per_second=target)
                refresh_duration = elapsed_seconds(refresh_started)
                self._last_rail_refresh_seconds = refresh_duration
                if probe_first_refresh:
                    print(
                        "RAIL FIRST REFRESH OK duration={:.3f}s refreshed={} heap_free={}".format(
                            refresh_duration, refreshed, self._heap_free()
                        )
                    )
                    self._rail_first_refresh_pending = False
                if refresh_duration > 0.2:
                    print(
                        "RAIL REFRESH SLOW duration={:.3f}s refreshed={}".format(
                            refresh_duration,
                            refreshed,
                        )
                    )
                return refreshed
            return self.display.refresh(target_frames_per_second=target)

        self._stats_changes += 1

        # With auto-refresh enabled, mutating displayio objects is sufficient.
        # Calling refresh() here would make this mode no longer a clean test.
        if self.presentation_mode == "auto_refresh" or self.display.auto_refresh:
            self._maybe_report_stats()
            return True

        self._stats_refresh_attempts += 1
        target = None if self.presentation_mode == "immediate" else MATRIX_REFRESH_FPS
        heap_before = (
            self._heap_free() if animation_class == "departures_calling" else None
        )
        probe_first_refresh = (
            animation_class == "departures_calling"
            and self._rail_first_refresh_pending
        )
        if probe_first_refresh:
            print(
                "RAIL FIRST REFRESH START mode={} scene_ready_to_present_ms={} heap_free={}".format(
                    self.presentation_mode,
                    ticks_ms() - self._rail_build_started_ms
                    if self._rail_build_started_ms is not None else None,
                    heap_before
                )
            )
        refresh_started = ticks_ms()
        refreshed = self.display.refresh(target_frames_per_second=target)
        now = ticks_ms()
        refresh_duration = elapsed_seconds(refresh_started, now)
        if animation_class == "departures_calling":
            self._last_rail_refresh_seconds = refresh_duration
            if probe_first_refresh:
                print(
                    "RAIL FIRST REFRESH OK duration={:.3f}s scene_ready_to_present_ms={} refreshed={} heap_free={}".format(
                        refresh_duration,
                        ticks_ms() - self._rail_build_started_ms
                        if self._rail_build_started_ms is not None else None,
                        refreshed, self._heap_free()
                    )
                )
                self._rail_first_refresh_pending = False
        if heap_before is not None:
            heap_after = self._heap_free()
            if heap_after is not None:
                self._stats_rail_refresh_heap_gain_max = max(
                    self._stats_rail_refresh_heap_gain_max,
                    heap_after - heap_before,
                )
        if animation_class in self._stats_animation_classes:
            counters = self._stats_animation_classes[animation_class]
            counters["refresh_total"] += refresh_duration
            counters["refresh_max"] = max(counters["refresh_max"], refresh_duration)
        if refreshed:
            self._stats_refresh_successes += 1
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
        self._last_present_refresh = self._refresh()

    def _new_football_scene(self):
        """Allocate one persistent scene; two scenes support an in-place push."""
        import displayio

        group = displayio.Group()
        # All eight indexed poses are precomputed once and shared across both
        # scenes. Switching TileGrid.bitmap avoids 256 pixel writes and the
        # resulting temporary integer objects during every moving frame.
        palette = displayio.Palette(len(FOOTBALL_BALL_PALETTE_INDEX))
        palette[0] = 0
        palette.make_transparent(0)
        for name, index in FOOTBALL_BALL_PALETTE_INDEX.items():
            if name != ".":
                red, green, blue = FOOTBALL_BALL_PALETTE[name]
                palette[index] = (red << 16) | (green << 8) | blue
        ball_grid = displayio.TileGrid(
            self._football_rotation_bitmaps[0],
            pixel_shader=palette, x=FOOTBALL_RENDER_END_X, y=8,
        )
        group.append(ball_grid)
        text_group = displayio.Group(x=FOOTBALL_TEXT_X, y=0)
        labels = [
            self._label(text_group, "", 0xFFFFFF, 0, index * 8)
            for index in range(4)
        ]
        fixture_bitmap = displayio.Bitmap(DISPLAY_WIDTH - FOOTBALL_TEXT_X, 11, 3)
        fixture_palette = displayio.Palette(3)
        fixture_palette[0] = 0x000000
        fixture_palette.make_transparent(0)
        fixture_palette[1] = 0xFFFFFF
        fixture_palette[2] = 0xFFFFFF
        fixture_grid = displayio.TileGrid(
            fixture_bitmap, pixel_shader=fixture_palette
        )
        text_group.append(fixture_grid)
        group.append(text_group)
        due_group = displayio.Group()
        heading = self._label(due_group, "KICK-OFF IN", 0xFFAA00, 190, 18)
        countdown = self._label(due_group, "", 0xFFFFFF, 256, 25)
        group.append(due_group)
        return {
            "group": group, "ball_grid": ball_grid, "frame": 0,
            "labels": labels,
            "fixture_bitmap": fixture_bitmap,
            "fixture_palette": fixture_palette,
            "text_group": text_group,
            "due_group": due_group, "heading": heading,
            "countdown": countdown, "countdown_text": None,
            "key": None, "content_signature": None,
        }

    def _set_football_content(self, scene, screen, rows, colors, phase=0):
        """Update labels only when their source data changes (not on each tick)."""
        status = screen.get("status")
        team_color = (
            football_team_name_color(screen, phase)
            if status == "IN" else FOOTBALL_TEAM_COLORS.get(screen.get("team_key"))
        )
        key = (status, tuple(rows), tuple(colors), team_color)
        if scene["key"] == key:
            return False
        labels = scene["labels"]
        if status == "PRE":
            scene["text_group"].y = 5
            # Enlarge the full fixture vertically while retaining its compact
            # six-pixel character advance. The date sits lower on row two.
            fixture_chars = (DISPLAY_WIDTH - FOOTBALL_TEXT_X) // 6
            titles = (_clip(str(rows[0]), fixture_chars), _clip(str(rows[1]), 22), "", "")
            for index, label in enumerate(labels):
                label.y = 17 if index == 1 else 0
                label.text = "" if index == 0 else titles[index]
                label.color = colors[index]
        else:
            scene["text_group"].y = 0
            for index, label in enumerate(labels):
                label.y = 8 * index
                label.text = _clip(str(rows[index]), 38) if index < len(rows) else ""
                label.color = colors[index]
        fixture_color = (FOOTBALL_FIXTURE_TEXT_COLOR[0] << 16
                         | FOOTBALL_FIXTURE_TEXT_COLOR[1] << 8
                         | FOOTBALL_FIXTURE_TEXT_COLOR[2])
        span = football_team_name_span(screen, rows[0]) if rows else None
        fixture_bitmap = scene["fixture_bitmap"]
        fixture_bitmap.fill(0)
        if status == "PRE":
            fixture = _clip(str(rows[0]), (DISPLAY_WIDTH - FOOTBALL_TEXT_X) // 6) if rows else ""
            load_glyphs = getattr(self.font, "load_glyphs", None)
            if load_glyphs is not None:
                load_glyphs(fixture)
            team_start, team_name, fixture_team_color = span if span else (-1, "", None)
            fixture_team_color = fixture_team_color or team_color
            scene["fixture_palette"][1] = fixture_color & 0xFFFFFF
            scene["fixture_palette"][2] = (
                ((fixture_team_color[0] << 16) | (fixture_team_color[1] << 8) | fixture_team_color[2])
                if fixture_team_color else fixture_color
            )
            for char_index, character in enumerate(fixture):
                glyph = self.font.get_glyph(ord(character))
                if glyph is None:
                    continue
                color_index = (
                    2 if fixture_team_color and team_start <= char_index < team_start + len(team_name)
                    and character != " " else 1
                )
                for glyph_y in range(glyph.height):
                    scaled_top = glyph_y * 11 // glyph.height
                    scaled_bottom = (glyph_y + 1) * 11 // glyph.height
                    for glyph_x in range(min(glyph.width, 5)):
                        if glyph.bitmap[glyph_x, glyph_y] <= 0:
                            continue
                        target_x = char_index * 6 + glyph_x
                        for target_y in range(scaled_top, max(scaled_top + 1, scaled_bottom)):
                            if 0 <= target_y < 11:
                                fixture_bitmap[target_x, target_y] = color_index
        if status == "PRE":
            labels[0].color = fixture_color
        else:
            labels[0].color = (
                (team_color[0] << 16) | (team_color[1] << 8) | team_color[2]
                if team_color else 0xFFFFFF
            )
            fixture_span = football_team_name_span(screen, rows[1]) if len(rows) > 1 else None
            if fixture_span:
                labels[1].color = fixture_color
        scene["due_group"].hidden = status != "PRE"
        scene["key"] = key
        return True

    def _show_football(self, screen, phase, now_epoch):
        """Roll the ball and fixture together; push the prior match to the left.

        Two reusable displayio scenes are allocated once. Each entry reuses a
        scene and changes only group coordinates and the 16x16 bitmap pixels.
        """
        update_started = ticks_ms()
        if self._football_group is None:
            import displayio

            self._football_group = displayio.Group()
            self._football_rotation_bitmaps = []
            for pose in range(8):
                bitmap = displayio.Bitmap(
                    FOOTBALL_BALL_WIDTH, FOOTBALL_BALL_HEIGHT,
                    len(FOOTBALL_BALL_PALETTE_INDEX),
                )
                draw_football_rolling_indexed(bitmap, pose)
                self._football_rotation_bitmaps.append(bitmap)
            self._football_slots = (self._new_football_scene(), self._new_football_scene())
            for item in self._football_slots:
                item["group"].hidden = True
                self._football_group.append(item["group"])

        screen_id = screen.get("id")
        previous = self._football_current
        root_visible = self.display.root_group is self._football_group
        phase_reset = (
            self._football_previous_phase is not None
            and phase + 0.25 < self._football_previous_phase
        )
        entering = (
            previous is None or screen_id != self._football_screen_id
            or not root_visible or phase_reset
        )
        animation_speed = screen.get("animation_speed")
        if screen.get("status") == "IN":
            offset, settled = 0, True
        else:
            offset, settled = football_slide_offset(phase, animation_speed)
        changed = False

        if entering:
            use_first = previous is None or previous is self._football_slots[1]
            scene = self._football_slots[0 if use_first else 1]
            # Only a directly consecutive football screen pushes the previous
            # one. A flash/other screen uses a fresh independent entry.
            pushing = (
                screen.get("status") != "IN" and previous is not None and root_visible
                and screen_id != self._football_screen_id
                and self._football_previous_phase is not None
                and football_presentation_position(
                    self._football_previous_phase,
                    animation_speed=self._football_previous_animation_speed,
                )[1]
            )
            self._football_outgoing = previous if pushing else None
            for item in self._football_slots:
                item["group"].hidden = item is not scene and item is not self._football_outgoing
            scene["key"] = None
            scene["content_signature"] = None
            scene["countdown_text"] = None
            scene["frame"] = -1
            scene["due_group"].hidden = True
            self._football_current = scene
            self._football_screen_id = screen_id
            changed = True
        scene = self._football_current
        self._football_previous_phase = phase
        self._football_previous_animation_speed = animation_speed
        # The tracked team name itself carries its club/country colour cycle.

        goal_active = screen.get("goal_flash_active") and screen.get("status") == "IN"
        # A PRE countdown changes independently of the fixture. Avoid
        # reconstructing the fixture/score strings, row list and colour list
        # on every 7 FPS animation tick or every 1 Hz countdown wakeup. An
        # immutable key also handles MQTT snapshots replaced between frames.
        content_signature = (
            screen.get("status"), screen.get("team_key"),
            screen.get("team_name"), screen.get("display_fixture"),
            screen.get("opponent_long_name"), screen.get("opponent"),
            screen.get("team_homeaway"), screen.get("homeaway"),
            screen.get("kickoff"), screen.get("home_team"),
            screen.get("away_team"), screen.get("home_score"),
            screen.get("away_score"), screen.get("clock"),
            screen.get("competition"), bool(screen.get("stale")),
            bool(goal_active), screen.get("goal_side"),
            int(phase * 4) % 2 if goal_active else 0,
            int(max(0.0, phase) / 2) if screen.get("status") == "IN" else 0,
        )
        if scene["content_signature"] != content_signature:
            rows = list(football_screen_lines(screen, now_epoch))
            if goal_active:
                team = screen.get("home_team") if screen.get("goal_side") == "home" else screen.get("away_team")
                rows[3] = "GOAL {}".format(str(team or "SCORED").upper())
            colors = [0xFFAA00, 0xFFFFFF, 0xFFFFFF, 0xFF5555 if screen.get("stale") else 0xAAAAAA]
            if goal_active:
                colors[3] = 0xFFFFFF if int(phase * 4) % 2 == 0 else 0xFF3300
            changed = self._set_football_content(scene, screen, rows, colors, phase) or changed
            scene["content_signature"] = content_signature

        # The fixture and date are *already populated* while their whole scene
        # translates from x=254 to zero; only the Due In text waits to appear.
        if scene["group"].x != offset:
            scene["group"].x = offset
            changed = True
        frame = 0 if screen.get("status") == "IN" else football_roll_frame(phase, animation_speed)
        if scene["frame"] != frame:
            scene["ball_grid"].bitmap = self._football_rotation_bitmaps[frame]
            scene["frame"] = frame
            changed = True

        outgoing = self._football_outgoing
        if outgoing is not None:
            old_x = offset - (FOOTBALL_START_X - FOOTBALL_RENDER_END_X)
            if outgoing["group"].x != old_x:
                outgoing["group"].x = old_x
                changed = True
            if settled:
                outgoing["group"].hidden = True
                self._football_outgoing = None
                changed = True

        due_visible = screen.get("status") == "PRE" and settled
        if scene["due_group"].hidden == due_visible:
            scene["due_group"].hidden = not due_visible
            changed = True
        if due_visible:
            # Absolute UTC epoch arithmetic; update the glyphs only when the
            # displayed value changes. The football scene never restarts.
            countdown = football_due_in(screen.get("kickoff"), now_epoch)
            if scene["countdown_text"] != countdown:
                label = scene["countdown"]
                label.text = countdown
                label.x = football_countdown_x(countdown)
                scene["countdown_text"] = countdown
                changed = True

        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "football", changed, elapsed_seconds(update_started), animation_class,
        )
        if not root_visible:
            self._present(self._football_group)
        elif changed:
            self._refresh(animation_class=animation_class)

    def show_loading(self, title="UPCOMING", message="Loading...", clock_time="--:--"):
        """Show a cheap transition card before building a heavy screen."""
        import displayio

        group = displayio.Group()
        title = _clip(title, 30)
        message = _clip(message, 30)
        message_x = max(0, (DISPLAY_WIDTH - len(message) * WEATHER_FONT_WIDTH) // 2)
        self._label(group, title, 0xFFAA00, 0, 3)
        self._label(group, message, 0xFFFFFF, message_x, 18)
        self._label(group, clock_time, 0xFFAA00, CLOCK_X, 3)
        self._present(group)

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
        status_x = (
            max(0, CLOCK_X - HEADER_GAP - 10 - len(status) * WEATHER_FONT_WIDTH)
            if status else int(right_edge)
        )
        platform_x = RAIL_PLATFORM_X
        destination_width = max(0, platform_x - HEADER_GAP - RAIL_DESTINATION_X)
        if MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT and self._rail_service_bitmap(
            group,
            (
                (ordinal_text, RAIL_ORDINAL_X + x_offset),
                (time_text, RAIL_TIME_X + x_offset),
                (_fit_text_pixels(destination, destination_width), RAIL_DESTINATION_X + x_offset),
                (platform, platform_x + x_offset),
                (status, status_x + x_offset),
            ),
            color,
            y,
            compact_field_x=RAIL_DESTINATION_X + x_offset,
        ):
            self._rail_static_row_bitmap_count = getattr(
                self, "_rail_static_row_bitmap_count", 0
            ) + 1
            return
        self._label(group, ordinal_text, color, RAIL_ORDINAL_X + x_offset, y)
        self._label(group, time_text, color, RAIL_TIME_X + x_offset, y)
        self._rail_destination_label(
            group, _fit_text_pixels(destination, destination_width), color,
            RAIL_DESTINATION_X + x_offset, y,
        )
        self._label(group, platform, color, platform_x + x_offset, y)
        if status:
            self._label(group, status, color, status_x + x_offset, y)

    def _rail_destination_label(self, group, text, color, x, baseline_y):
        """Draw the destination with one pixel less between glyphs."""
        if not hasattr(self.font, "get_glyph"):
            self._label(group, text, color, x, baseline_y)
            return
        import displayio

        text = str(text or "")
        if hasattr(self.font, "load_glyphs"):
            self.font.load_glyphs(set(ord(character) for character in text))
        ascent = getattr(self.font, "ascent", None)
        if ascent is None:
            ascent = self.font.get_bounding_box()[1]
        y_offset = ascent // 2
        glyphs = []
        cursor_x = min_x = min_y = 0
        max_x = max_y = 0
        for character in text:
            glyph = self.font.get_glyph(ord(character))
            if glyph is None:
                continue
            glyph_x = cursor_x + glyph.dx
            glyph_y = -glyph.height - glyph.dy + y_offset
            glyphs.append((glyph, glyph_x, glyph_y))
            min_x = min(min_x, glyph_x)
            max_x = max(max_x, glyph_x + glyph.width)
            min_y = min(min_y, glyph_y)
            max_y = max(max_y, glyph_y + glyph.height)
            cursor_x += max(1, glyph.shift_x - RAIL_DESTINATION_TRACKING)
        if not glyphs:
            return
        bitmap = displayio.Bitmap(max(1, max_x - min_x), max(1, max_y - min_y), 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = color
        for glyph, glyph_x, glyph_y in glyphs:
            for gy in range(glyph.height):
                for gx in range(glyph.width):
                    if glyph.bitmap[gx, gy]:
                        bitmap[glyph_x - min_x + gx, glyph_y - min_y + gy] = 1
        group.append(displayio.TileGrid(
            bitmap,
            pixel_shader=palette,
            x=int(x) + min_x,
            y=int(baseline_y) + min_y,
        ))

    def _rail_service_bitmap(self, group, fields, color, baseline_y,
                             compact_field_x=None):
        """Render one static service row into a single compact glyph bitmap."""
        if not hasattr(self.font, "get_glyph"):
            return False
        import displayio

        characters = set()
        for text, _ in fields:
            characters.update(ord(character) for character in str(text or ""))
        if hasattr(self.font, "load_glyphs"):
            self.font.load_glyphs(characters)

        ascent = getattr(self.font, "ascent", None)
        if ascent is None:
            ascent = self.font.get_bounding_box()[1]
        y_offset = ascent // 2
        glyphs = []
        min_x = min_y = 0
        max_x = max_y = 0
        for text, field_x in fields:
            cursor_x = 0
            for character in str(text or ""):
                glyph = self.font.get_glyph(ord(character))
                if glyph is None:
                    continue
                glyph_x = int(field_x) + cursor_x + glyph.dx
                glyph_y = -glyph.height - glyph.dy + y_offset
                glyphs.append((glyph, glyph_x, glyph_y))
                min_x = min(min_x, glyph_x)
                max_x = max(max_x, glyph_x + glyph.width)
                min_y = min(min_y, glyph_y)
                max_y = max(max_y, glyph_y + glyph.height)
                tracking = (RAIL_DESTINATION_TRACKING
                            if int(field_x) == int(compact_field_x)
                            else 0)
                cursor_x += max(1, glyph.shift_x - tracking)

        width = max(1, max_x - min_x)
        height = max(1, max_y - min_y)
        bitmap = displayio.Bitmap(width, height, 1)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = color
        for glyph, glyph_x, glyph_y in glyphs:
            for gy in range(glyph.height):
                for gx in range(glyph.width):
                    if glyph.bitmap[gx, gy]:
                        bitmap[glyph_x - min_x + gx, glyph_y - min_y + gy] = 1
        group.append(displayio.TileGrid(
            bitmap,
            pixel_shader=palette,
            x=min_x,
            y=int(baseline_y) + min_y,
        ))
        return True

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
            and self._rail_presentation == screen.get("rail_presentation")
            and self._rail_calling_seconds_cached
            == screen.get("calling_seconds", RAIL_CALLING_SECONDS)
            and self._rail_summary_seconds_cached
            == screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
            and self._rail_station_speed_cached == screen.get("station_scroll_speed")
            and self._rail_station_spacing_cached == screen.get("station_list_spacing")
            and self._rail_rows_scroll_cached == MATRIX_RAIL_ROWS_SCROLL
            and self._rail_static_rows_bitmap_cached
            == MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT
            and self._rail_pause_seconds_cached
            == screen.get("upcoming_train_pause_seconds", 2)
        )

    def rail_scene_ready(self, screen):
        """Report whether the persistent rail scene already matches this payload."""
        return self._rail_cache_matches(screen)

    def rail_scene_prebuilt(self, screen):
        """Report whether a valid hidden scene is waiting for its paired handoff."""
        return getattr(self, "_rail_prebuilt_pending", False) and self._rail_cache_matches(screen)

    def _build_rail_scene(self, screen, clock_time, phase):
        """Build one shared departures scene for both presentation phases."""
        import displayio

        build_started = ticks_ms()
        heap_before_build = self._heap_free()
        self._rail_static_row_bitmap_count = 0
        self._rail_calling_labels = []
        self._rail_departure_rows = []
        self._rail_top_service_group = None
        print(
            "RAIL BUILD START services={} static_row_renderer={} heap_free={}".format(
                len(screen.get("services") or ()),
                "bitmap" if MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT else "labels",
                self._heap_free(),
            )
        )
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        self._rail_scroll_speed, self._rail_scroll_gap = _station_scroll_settings(screen)
        self._rail_calling_seconds = calling_seconds
        self._rail_summary_seconds = summary_seconds
        services = screen.get("services") or ()
        right_edge = _header_content_right(screen)
        root = displayio.Group()
        scroll_group = displayio.Group()
        service_rows = []
        for index, service in enumerate(services):
            row_group = displayio.Group()
            if service is not None:
                color = 0xFF3300 if service.get("cancelled") else 0xFFFFFF
                self._rail_service(
                    row_group, service, color, 0, 0, right_edge, index + 1
                )
            if index == 0:
                self._rail_top_service_group = row_group
            else:
                scroll_group.append(row_group)
                self._rail_departure_rows.append(row_group)
            service_rows.append(row_group)

        root.append(scroll_group)

        # In the calling phase this masks scrolling rows while they pass
        # behind the fixed top service and the calling-at line. It is moved
        # offscreen during the summary phase.
        mask_group = displayio.Group()
        self._mask(mask_group, 0, 0, DISPLAY_WIDTH, RAIL_ROW_Y[2] - 3)
        root.append(mask_group)

        if self._rail_top_service_group is not None:
            root.append(self._rail_top_service_group)
        summary_header_group = displayio.Group()
        self._label(summary_header_group, "DEPARTURES", 0xFFAA00, 0, 0)
        root.append(summary_header_group)

        calling_group = displayio.Group()
        calling_labels = []
        if services:
            service = services[0]
            presentation = screen.get("rail_presentation") or {}
            calling = presentation.get("calling_text") or calling_text(service)
            stations = calling[len(CALLING_LABEL):] if calling.startswith(CALLING_LABEL) else calling
            first = self._calling_label_group(
                service, RAIL_ROW_Y[1], presentation.get("calling_segments")
            )
            calling_group.append(first)
            self._mask(
                calling_group, 0, RAIL_ROW_Y[1] - 3,
                len(CALLING_LABEL) * WEATHER_FONT_WIDTH, 8,
            )
            prefix = self._label(
                calling_group, CALLING_LABEL, 0xFFAA00, 0, RAIL_ROW_Y[1]
            )
            calling_labels.append({
                "prefix": prefix,
                "first": first,
                "text": calling,
                "station_width": presentation.get(
                    "calling_station_width_px", len(stations) * WEATHER_FONT_WIDTH
                ),
            })
        root.append(calling_group)

        # The four physical rows are reused across both phases. Only their
        # positions and the three small overlay groups change at handoff.
        clock_group = displayio.Group()
        clock_label = self._label(clock_group, "", 0xFFAA00, CLOCK_X, 3)
        weather_group = displayio.Group()
        if isinstance(screen.get("weather"), dict):
            self._header_weather(weather_group, screen.get("weather"), 0)
        root.append(clock_group)
        root.append(weather_group)

        scene = {
            "group": root,
            "calling_labels": calling_labels,
            "departure_rows": self._rail_departure_rows,
            "service_rows": service_rows,
            "mask_group": mask_group,
            "summary_header_group": summary_header_group,
            "top_service_group": self._rail_top_service_group,
            "calling_group": calling_group,
            "clock_group": clock_group,
            "clock_label": clock_label,
            "weather_group": weather_group,
        }
        # Both keys refer to the same scene object, rather than two complete
        # displayio trees with duplicate row bitmaps and labels.
        self._rail_scenes = {"summary": scene, "calling": scene}
        self._rail_calling_labels = calling_labels
        self._rail_summary_header_group = summary_header_group
        self._rail_calling_group = calling_group
        self._rail_services = screen.get("services")
        self._rail_title = screen.get("title")
        self._rail_stale = bool(screen.get("stale"))
        self._rail_weather = screen.get("weather")
        self._rail_presentation = screen.get("rail_presentation")
        self._rail_calling_seconds_cached = calling_seconds
        self._rail_summary_seconds_cached = summary_seconds
        self._rail_station_speed_cached = screen.get("station_scroll_speed")
        self._rail_station_spacing_cached = screen.get("station_list_spacing")
        self._rail_rows_scroll_cached = MATRIX_RAIL_ROWS_SCROLL
        self._rail_static_rows_bitmap_cached = MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT
        self._rail_pause_seconds_cached = screen.get("upcoming_train_pause_seconds", 2)
        heap_after_build = self._heap_free()
        self._rail_build_started_ms = build_started
        self._select_rail_scene(phase, calling_seconds, summary_seconds)
        self._rail_first_refresh_pending = True
        print(
            "RAIL BUILD OK scenes={} static_row_bitmaps={} duration={:.3f}s heap_free_before={} heap_free_after={} heap_drop={}".format(
                1, self._rail_static_row_bitmap_count,
                elapsed_seconds(build_started), heap_before_build,
                heap_after_build,
                (heap_before_build - heap_after_build)
                if heap_before_build is not None and heap_after_build is not None
                else None,
            )
        )

    def _collect_rail_build_garbage(self, heap_before_build, build_started):
        """Collect after a cold scene build and restore the animated-loop GC state."""
        import gc

        heap_before_gc = self._heap_free()
        gc_started = ticks_ms()
        gc.enable()
        try:
            gc.collect()
        finally:
            gc.disable()
        heap_after_gc = self._heap_free()
        gc_reclaimed = (
            heap_after_gc - heap_before_gc
            if heap_before_gc is not None and heap_after_gc is not None
            else None
        )
        retained_heap_drop = (
            heap_before_build - heap_after_gc
            if heap_before_build is not None and heap_after_gc is not None
            else None
        )
        print(
            "RAIL POST BUILD GC duration={:.3f}s heap_free_before={} heap_free_after={} reclaimed_bytes={} retained_heap_drop={} build_to_gc_ms={}".format(
                elapsed_seconds(gc_started), heap_before_gc, heap_after_gc,
                gc_reclaimed, retained_heap_drop, ticks_ms() - build_started,
            )
        )

    def prepare_rail_scene(
        self,
        screen,
        clock_time="--:--",
        minimum_free_bytes=MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES,
        maximum_scene_bytes=MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES,
    ):
        """Build a guarded rail scene without presenting or refreshing it."""
        if (not isinstance(screen, dict) or screen.get("kind") != "rail_combined"
                or screen.get("stale") or not screen.get("services")):
            print("RAIL PREBUILD SKIP reason=missing_or_stale_payload")
            self.discard_prepared_rail_scene(reason="missing_or_stale_payload", collect=True)
            return False
        if self._rail_cache_matches(screen):
            self._rail_prebuilt_pending = True
            print("RAIL PREBUILD REUSE screen_id={} services={}".format(
                screen.get("id"), len(screen.get("services") or ())
            ))
            return True

        if self._rail_group is not None:
            if self.display.root_group is self._rail_group:
                print("RAIL PREBUILD SKIP reason=visible_rail_scene")
                return False
            self.discard_prepared_rail_scene(reason="payload_or_settings_changed", collect=True)

        heap_before = self._heap_free()
        required_free = max(0, int(minimum_free_bytes)) + max(0, int(maximum_scene_bytes))
        if heap_before is None or heap_before < required_free:
            print(
                "RAIL PREBUILD SKIP reason=memory_guard heap_free={} required_free={}".format(
                    heap_before, required_free
                )
            )
            return False

        root_before = self.display.root_group
        started = ticks_ms()
        try:
            self._build_rail_scene(screen, clock_time, 0)
        except MemoryError:
            print("RAIL PREBUILD SKIP reason=memory_error heap_free={}".format(self._heap_free()))
            collect = getattr(__import__("gc"), "collect", None)
            if collect is not None:
                collect()
            return False

        # Static maintenance runs with automatic GC enabled. Collect transient
        # construction garbage while the completed scene is safely cached.
        import gc

        heap_before_gc = self._heap_free()
        gc_started = ticks_ms()
        gc.collect()
        gc_duration = elapsed_seconds(gc_started)
        heap_after = self._heap_free()
        gc_reclaimed = (
            heap_after - heap_before_gc
            if heap_before_gc is not None and heap_after is not None
            else None
        )
        self._rail_retained_heap_cost = (
            heap_before - heap_after
            if heap_before is not None and heap_after is not None
            else None
        )
        if self.display.root_group is not root_before:
            self.display.root_group = root_before
            print("RAIL PREBUILD ERROR reason=hidden_root_changed restored=true")
            self.discard_prepared_rail_scene(reason="hidden_root_changed", collect=True)
            return False
        if heap_after is not None and heap_after < max(0, int(minimum_free_bytes)):
            self.discard_prepared_rail_scene(reason="post_build_reserve", collect=True)
            print(
                "RAIL PREBUILD SKIP reason=post_build_reserve heap_free={} minimum_free={}".format(
                    self._heap_free(), minimum_free_bytes
                )
            )
            return False
        print(
            "RAIL PREBUILD OK screen_id={} duration={:.3f}s gc_duration={:.3f}s gc_reclaimed={} heap_free_before={} heap_free_after={} retained_heap_drop={}".format(
                screen.get("id"), elapsed_seconds(started), gc_duration,
                gc_reclaimed, heap_before, heap_after,
                self._rail_retained_heap_cost,
            )
        )
        self._rail_prebuilt_pending = True
        return True

    def discard_prepared_rail_scene(self, reason="obsolete", collect=False):
        """Release a hidden prepared scene, preserving a currently visible rail root."""
        if self._rail_group is not None and self.display.root_group is self._rail_group:
            return False
        had_scene = self._rail_group is not None
        heap_before = self._heap_free() if had_scene else None
        self._rail_scenes = {}
        self._rail_group = None
        self._rail_services = None
        self._rail_title = None
        self._rail_stale = None
        self._rail_weather = None
        self._rail_presentation = None
        self._rail_calling_seconds_cached = None
        self._rail_summary_seconds_cached = None
        self._rail_station_speed_cached = None
        self._rail_station_spacing_cached = None
        self._rail_rows_scroll_cached = None
        self._rail_static_rows_bitmap_cached = None
        self._rail_prebuilt_pending = False
        self._rail_pause_seconds_cached = None
        self._rail_calling_labels = []
        self._rail_departure_rows = []
        self._rail_summary_header_group = None
        self._rail_top_service_group = None
        self._rail_calling_group = None
        self._rail_phase = None
        self._rail_clock_group = None
        self._rail_clock_label = None
        self._rail_weather_group = None
        if had_scene and collect:
            import gc

            gc.collect()
        heap_after = self._heap_free() if had_scene else None
        if had_scene:
            print(
                "RAIL SCENE DISCARD reason={} heap_free_before={} heap_free_after={} reclaimed_bytes={}".format(
                    reason,
                    heap_before,
                    heap_after,
                    heap_after - heap_before
                    if heap_before is not None and heap_after is not None
                    else None,
                )
            )
        return True

    def _select_rail_scene(self, phase, calling_seconds=RAIL_CALLING_SECONDS,
                           summary_seconds=RAIL_SUMMARY_SECONDS):
        """Switch the shared departures scene between summary and calling."""
        state = rail_phase(phase, summary_seconds, calling_seconds)
        scene = self._rail_scenes[state]
        self._rail_group = scene["group"]
        self._rail_calling_labels = scene["calling_labels"]
        self._rail_departure_rows = scene["departure_rows"]
        hidden_y = RAIL_ROW_Y[-1] + 8
        row_step = RAIL_ROW_Y[3] - RAIL_ROW_Y[2]
        if self._rail_top_service_group is not None:
            self._rail_top_service_group.y = (
                RAIL_ROW_Y[0]
                if state == "calling" or len(self._rail_services or ()) >= 4
                else RAIL_ROW_Y[1]
            )
        if self._rail_summary_header_group is not None:
            self._rail_summary_header_group.y = (
                RAIL_ROW_Y[0]
                if state == "summary" and len(self._rail_services or ()) < 4
                else -DISPLAY_WIDTH
            )
        if self._rail_calling_group is not None:
            self._rail_calling_group.y = 0 if state == "calling" else -DISPLAY_WIDTH
        mask_group = scene["mask_group"]
        mask_group.y = 0 if state == "calling" else -DISPLAY_WIDTH
        summary_offset = 0 if len(self._rail_services or ()) >= 4 else 1
        for index, row_group in enumerate(self._rail_departure_rows):
            if state == "summary":
                visible_rows = 3 if summary_offset == 0 else 2
                if index < visible_rows:
                    row_group.y = RAIL_ROW_Y[index + 1 + summary_offset]
                else:
                    row_group.y = hidden_y + index * row_step
            else:
                row_group.y = hidden_y + index * row_step
        self._rail_departure_active_start = None
        self._rail_departure_active_count = 0
        self._rail_clock_group = scene["clock_group"]
        self._rail_clock_label = scene["clock_label"]
        self._rail_weather_group = scene["weather_group"]
        self._rail_phase = state

    def _update_rail_scene(self, screen, clock_time, phase):
        """Update only the calling-at marquee and rotating header item."""
        changed = False
        scroll_speed = self._rail_scroll_speed
        scroll_gap = self._rail_scroll_gap
        calling_seconds = self._rail_calling_seconds
        summary_seconds = self._rail_summary_seconds
        if self._rail_phase == "calling":
            for labels in self._rail_calling_labels:
                calling_x = None
                if summary_seconds == 0:
                    calling_x = _cached_calling_x(
                        phase, labels["station_width"], scroll_speed, calling_seconds
                    )
                if calling_x is None:
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
        if self._rail_phase == "calling" and MATRIX_RAIL_ROWS_SCROLL:
            start, progress, reset_progress = departure_scroll_state(
                rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                max(0, len(services) - 1),
                screen.get("upcoming_train_pause_seconds", 2),
                visible_rows=2,
            )
            if reset_progress is None:
                active_start = None
                active_count = 0
            elif reset_progress > 0:
                active_start = 0
                active_count = 2
            else:
                active_start = start
                active_count = 3

            previous_start = self._rail_departure_active_start
            previous_count = self._rail_departure_active_count
            if previous_start is not None:
                previous_end = previous_start + previous_count
                for index in range(previous_start, previous_end):
                    if (active_start is None
                            or index < active_start
                            or index >= active_start + active_count):
                        if index < len(self._rail_departure_rows):
                            row_group = self._rail_departure_rows[index]
                            row_y = hidden_y + index * row_step
                            if row_group.y != row_y:
                                row_group.y = row_y
                                changed = True

            if active_start is not None:
                active_end = active_start + active_count
                for index in range(active_start, active_end):
                    if index >= len(self._rail_departure_rows):
                        break
                    if reset_progress is not None and reset_progress > 0:
                        row_y = RAIL_ROW_Y[2] + 2 * row_step - int(
                            reset_progress * 2 * row_step
                        ) + index * row_step
                    else:
                        row_y = RAIL_ROW_Y[2] + (index - start) * row_step - int(
                            progress * row_step
                        )
                    row_group = self._rail_departure_rows[index]
                    if row_group.y != row_y:
                        row_group.y = row_y
                        changed = True
            self._rail_departure_active_start = active_start
            self._rail_departure_active_count = active_count
        elif self._rail_phase == "calling":
            for index in range(min(2, len(self._rail_departure_rows))):
                row_group = self._rail_departure_rows[index]
                row_y = RAIL_ROW_Y[2] + index * row_step
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

    def rail_gc_safe_to_collect(self, screen, phase):
        """Return whether all animated rail content is stationary."""
        if not isinstance(screen, dict) or screen.get("kind") != "rail_combined":
            return False
        summary_seconds = self._rail_summary_seconds
        calling_seconds = self._rail_calling_seconds
        if summary_seconds != 0 or not self._rail_calling_labels:
            return False
        try:
            phase_ms = int(max(0.0, float(phase or 0)) * 1000.0)
            calling_ms = int(max(0.1, float(calling_seconds)) * 1000.0)
            speed_int = int(self._rail_scroll_speed)
        except (TypeError, ValueError):
            return False
        if speed_int <= 0 or speed_int != self._rail_scroll_speed or calling_ms <= 0:
            return False
        prefix_width = len(CALLING_LABEL) * WEATHER_FONT_WIDTH
        pause_ms = int(CALLING_MARQUEE_PAUSE_SECONDS * 1000)
        for labels in self._rail_calling_labels:
            travel_ms = (
                (DISPLAY_WIDTH - prefix_width + int(labels["station_width"])) * 1000
                + speed_int - 1
            ) // speed_int
            within_ms = (phase_ms % calling_ms) % (travel_ms + pause_ms)
            if within_ms < travel_ms:
                return False
        if MATRIX_RAIL_ROWS_SCROLL:
            services = screen.get("services") or ()
            _, progress, reset_progress = departure_scroll_state(
                rail_marquee_elapsed(phase, summary_seconds, calling_seconds),
                max(0, len(services) - 1),
                screen.get("upcoming_train_pause_seconds", 2),
                visible_rows=2,
            )
            # A blank reset gap and the deliberate row pauses are stationary.
            if progress > 0 or (reset_progress is not None and reset_progress > 0):
                return False
        # The current header alternates clock/weather at rest; it has no slide.
        # Keep this explicit so future header animation changes gate rail GC.
        if _header_slide_active(phase, screen.get("weather")):
            return False
        return True

    def _show_rail(self, screen, clock_time, phase):
        """Render departures with a persistent scene and live calling marquee."""
        calling_seconds = screen.get("calling_seconds", RAIL_CALLING_SECONDS)
        summary_seconds = screen.get("summary_seconds", RAIL_SUMMARY_SECONDS)
        state = rail_phase(phase, summary_seconds, calling_seconds)
        prebuilt_for_handoff = self.rail_scene_prebuilt(screen)
        scene_built = False
        if not self._rail_cache_matches(screen):
            # A mismatched prepared payload is an on-demand fallback, never a
            # prepared handoff for a later unchanged cycle.
            self._rail_prebuilt_pending = False
            heap_before_build = self._heap_free()
            build_started = ticks_ms()
            try:
                self._build_rail_scene(screen, clock_time, phase)
            except Exception:
                # code.py may have enabled automatic GC for this cold build.
                # If construction fails before the post-build collector runs,
                # restore the animated-window state before propagating it.
                if MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT:
                    import gc

                    gc.disable()
                raise
            scene_built = True
            if MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT:
                self._collect_rail_build_garbage(heap_before_build, build_started)
            phase_changed = False
        elif self._rail_phase != state:
            self._select_rail_scene(phase, calling_seconds, summary_seconds)
            phase_changed = True
        else:
            phase_changed = False
        if self._rail_first_refresh_pending and not scene_built:
            # A prepared scene can sit hidden throughout the static slot.
            # Measure transition-to-present latency separately from its build.
            self._rail_build_started_ms = ticks_ms()
        update_heap_before = self._heap_free()
        update_started = ticks_ms()
        changed = self._update_rail_scene(screen, clock_time, phase) or phase_changed
        update_duration = elapsed_seconds(update_started)
        heap_gain = None
        self._last_rail_update_seconds = update_duration
        self._last_rail_heap_gain = None
        if self.telemetry_enabled and update_duration > 0.1:
            self._stats_rail_slow_updates += 1
        if update_duration > 0.1 and update_heap_before is not None:
            update_heap_after = self._heap_free()
            if update_heap_after is not None:
                heap_gain = update_heap_after - update_heap_before
                self._last_rail_heap_gain = heap_gain
                self._stats_rail_update_heap_gain_max = max(
                    self._stats_rail_update_heap_gain_max, heap_gain
                )
                if self.telemetry_enabled and heap_gain > 4096:
                    self._stats_rail_gc_events += 1
        if update_duration > 0.2:
            print(
                "RAIL UPDATE SLOW duration={:.3f}s heap_gain={}".format(
                    update_duration,
                    heap_gain,
                )
            )
        self._attach_brightness_overlay(self._rail_group)
        if self.display.root_group is not self._rail_group:
            self.display.root_group = self._rail_group
            changed = True
        if prebuilt_for_handoff:
            self._rail_prebuilt_pending = False
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

    def _bus_departures(self, group, screen, phase=0):
        """Compact two-row-per-stop timetable for the 256x32 board."""
        departures = screen.get("departures") or []
        title = _clip(screen.get("title") or "SL7", 26)
        self._label(group, title, 0xFFAA00, 0, 3)
        if screen.get("status") == "unavailable":
            self._label(group, "SL7 unavailable", 0xFF3300, 0, 18)
            return
        if not departures:
            self._label(group, "No SL7 services", 0xFFFFFF, 0, 18)
            return
        # Three 8px rows fit at y=8/16/24; y=29 clipped the third
        # row on the 32px matrix. Reserve the right columns for times/ETAs.
        for index, item in enumerate(departures[:3]):
            y = (8, 16, 24)[index]
            delay = _bus_minutes(item.get("planned"), item.get("estimated"))
            status = "CANCEL" if item.get("cancelled") else str(item.get("due_text") or "")
            if not status and delay:
                status = "+{}m".format(delay)
            color = 0xFF3300 if item.get("cancelled") else (0xFFAA00 if delay else 0xFFFFFF)
            destination = _fit_text_pixels(item.get("destination") or "--", 170)
            time_text = item.get("local_time") or _bus_time(item.get("estimated") or item.get("planned"))
            self._label(group, destination, color, 0, y)
            self._label(group, time_text, color, 178, y)
            if status:
                self._label(group, status[:6], color, max(218, _right_aligned_x(status[:6], DISPLAY_WIDTH)), y)

    def _bus_departures_split(self, group, screen, now_epoch=None):
        """Two independent 128-pixel columns, each with a heading + 3 rows."""
        for x, title, status, stale, rows in split_sl7_rows(screen, now_epoch):
            self._label(group, title, 0xFF3300 if stale else 0xFFAA00, x + 1, 3)
            if stale and rows:
                self._label(group, "!", 0xFF3300, x + 119, 3)
            if not rows:
                text = ("OFF" if status == "disabled" else
                        "Unavailable" if status == "unavailable" else
                        "STALE" if stale else "No services")
                self._label(group, text, 0xFF3300 if stale or status == "unavailable"
                            else 0xFFFFFF, x + 2, 11)
                continue
            for index, (due, time_text, cancelled, _delayed) in enumerate(rows):
                y = 11 + index * 8
                time_color = 0xFF3300 if cancelled else 0xFFFFFF
                prefix, value = split_sl7_due_parts(due)
                due_color = 0xFF3300 if cancelled or prefix == "CXL" else 0xFFAA00
                self._label(group, time_text[:5], time_color, x + SL7_TIME_COLUMN_X, y)
                self._label(group, prefix, due_color, x + SL7_DUE_COLUMN_X, y)
                if value:
                    value_x = x + SL7_DUE_COLUMN_X + len("Due in ") * (WEATHER_FONT_WIDTH + WEATHER_GAP)
                    self._label(group, value, 0xFFFFFF, value_x, y)

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

    def _flash(self, group, screen, phase=0):
        """Build a reminder marquee or a compact, paged assistant message."""
        import displayio
        if screen.get("title") == "ASSISTANT":
            self._label(group, "ASSISTANT", 0xFFAA00, 0, 2)
            _, lines = assistant_message_page(screen.get("label"), phase)
            for index, line in enumerate(lines):
                self._label(group, line, 0xFFFFFF, 0, ASSISTANT_MESSAGE_TEXT_Y + index * 8)
            return group

        motion = displayio.Group(x=reminder_scroll_x(screen, phase))
        bitmap = displayio.Bitmap(REMINDER_CLOCK_SIZE, REMINDER_CLOCK_SIZE, 2)
        palette = displayio.Palette(2)
        palette.make_transparent(0)
        palette[1] = 0xFFAA00
        for x in range(REMINDER_CLOCK_SIZE):
            for y in range(REMINDER_CLOCK_SIZE):
                if reminder_clock_pixel(x, y):
                    bitmap[x, y] = 1
        motion.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=1))
        label = str(screen.get("label") or "")
        self._scaled_label(motion, label,
                           0xFFFFFF, REMINDER_TEXT_X, 5, scale=REMINDER_TEXT_SCALE)
        group.append(motion)
        return motion

    def _show_flash(self, screen, phase):
        import displayio
        assistant = screen.get("title") == "ASSISTANT"
        page_index = assistant_message_page(screen.get("label"), phase)[0] if assistant else None
        key = (
            screen.get("id"),
            screen.get("title"),
            screen.get("label"),
            screen.get("duration_seconds"),
            page_index,
        )
        changed = False
        if getattr(self, "_flash_key", None) != key:
            self._flash_group = displayio.Group()
            self._flash_motion = self._flash(self._flash_group, screen, phase)
            self._flash_key = key
            changed = True
        if not assistant:
            x = reminder_scroll_x(screen, phase)
            if self._flash_motion.x != x:
                self._flash_motion.x = x
                changed = True
        self._attach_brightness_overlay(self._flash_group)
        if self.display.root_group is not self._flash_group:
            self.display.root_group = self._flash_group
            changed = True
        if changed:
            self._refresh(self._animation_class(screen, phase))

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

    def tasks_ready(self, screen, clock_date=""):
        return self._todoist_cache_matches(screen, clock_date)

    def prepare_tasks(self, screen, clock_time="--:--", clock_date=""):
        if not self.tasks_ready(screen, clock_date):
            fields = ['_todoist_group','_todoist_rows','_todoist_events','_todoist_clock_date','_todoist_title','_todoist_stale','_todoist_viewport_size','_todoist_page_step','_todoist_page_seconds','_todoist_page_starts','_todoist_page_durations','_todoist_weather_icon','_todoist_weather_temp','_todoist_weather_stale','_todoist_clock_group','_todoist_clock_label','_todoist_weather_group']
            previous = [(name, getattr(self, name, None)) for name in fields]
            try:
                self._build_todoist_scene(screen, clock_time, clock_date)
            except Exception:
                for name, value in previous:
                    setattr(self, name, value)
                raise

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

        update_started = ticks_ms()
        changed = self._update_todoist_scene(screen, clock_time, phase)
        self._attach_brightness_overlay(self._todoist_group)
        if self.display.root_group is not self._todoist_group:
            self.display.root_group = self._todoist_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "todoist",
            changed,
            elapsed_seconds(update_started),
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
        motion = displayio.Group(x=0, y=STEAM_TRAIN_VERTICAL_OFFSET)
        bitmap = displayio.Bitmap(STEAM_TRAIN_WIDTH, STEAM_TRAIN_HEIGHT, 5)
        palette = displayio.Palette(5)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = 0xFFFFFF
        palette[2] = 0xFFAA00
        palette[3] = 0xAAAAAA
        palette[4] = 0xFF3300

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
                    bitmap[px, py] = 4

        motion.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=3))
        words = str(screen.get("words") or "")
        if words:
            self._scaled_label(
                motion,
                words,
                0xFFAA00,
                STEAM_TRAIN_WIDTH + STEAM_TRAIN_TEXT_GAP,
                5,
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
        next_x = max(0, DISPLAY_WIDTH - int(elapsed * self._steam_train_speed))
        if self._steam_train_motion_group.x == next_x:
            return False
        self._steam_train_motion_group.x = next_x
        return True

    def _show_steam_train(self, screen, phase):
        if not self._steam_train_cache_matches(screen):
            self._build_steam_train_scene(screen)
        update_started = ticks_ms()
        changed = self._update_steam_train_scene(phase)
        self._attach_brightness_overlay(self._steam_train_group)
        if self.display.root_group is not self._steam_train_group:
            self.display.root_group = self._steam_train_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "steam_train",
            changed,
            elapsed_seconds(update_started),
            animation_class,
        )
        if changed:
            self._refresh(animation_class)

    def prepare_intro(self, screen, clock_date=""):
        """Build transition scenes before their first visible animation frame."""
        if not isinstance(screen, dict):
            return False
        kind = screen.get("kind")
        if kind == "steam_train_intro":
            if self._steam_train_cache_matches(screen):
                return False
            self._build_steam_train_scene(screen)
            return True
        if kind == "bus_intro":
            if self._bus_intro_cache_matches(screen):
                return False
            self._build_bus_intro_scene(screen)
            return True
        if kind == "christmas_tracker":
            if self._christmas_group is not None:
                return False
            self._build_christmas_scene(screen, clock_date)
            return True
        if kind == "christmas_tracker_intro":
            if self._christmas_intro_group is not None:
                return False
            self._build_christmas_intro_scene()
            return True
        return False

    def _build_christmas_intro_scene(self):
        import displayio

        root = displayio.Group()
        motion = displayio.Group(x=SLEIGH_START_X, y=4)
        bitmap = displayio.Bitmap(
            CHRISTMAS_SLEIGH_WIDTH, CHRISTMAS_SLEIGH_HEIGHT,
            len(CHRISTMAS_SLEIGH_PALETTE_INDEX),
        )
        palette = displayio.Palette(len(CHRISTMAS_SLEIGH_PALETTE_INDEX))
        palette[0] = 0x000000
        palette.make_transparent(0)
        for key, index in CHRISTMAS_SLEIGH_PALETTE_INDEX.items():
            if key != ".":
                red, green, blue = CHRISTMAS_SLEIGH_PALETTE[key]
                palette[index] = (red << 16) | (green << 8) | blue
        draw_christmas_sleigh_indexed(bitmap, 0, 0,
                                      CHRISTMAS_SLEIGH_WIDTH, CHRISTMAS_SLEIGH_HEIGHT)
        motion.append(displayio.TileGrid(bitmap, pixel_shader=palette))
        self._scaled_label(motion, "HO HO HO...", 0xFFAA00, 88, 6)
        root.append(motion)
        self._christmas_intro_group = root
        self._christmas_intro_motion = motion

    def _show_christmas_intro(self, phase):
        if self._christmas_intro_group is None:
            self._build_christmas_intro_scene()
        update_started = ticks_ms()
        elapsed = max(0.0, float(phase or 0))
        x = max(0, DISPLAY_WIDTH - int(elapsed * (DISPLAY_WIDTH / SLEIGH_SLIDE_SECONDS)))
        changed = self._christmas_intro_motion.x != x
        self._christmas_intro_motion.x = x
        self._attach_brightness_overlay(self._christmas_intro_group)
        if self.display.root_group is not self._christmas_intro_group:
            self.display.root_group = self._christmas_intro_group
            changed = True
        self._record_animation_update(
            "christmas_intro", changed, elapsed_seconds(update_started), "steam_train"
        )
        if changed:
            self._refresh("steam_train")

    def _build_christmas_scene(self, screen, clock_date):
        import displayio

        days = days_until_christmas(clock_date)
        root = displayio.Group()
        snow_bitmap = displayio.Bitmap(DISPLAY_WIDTH, 32, 2)
        snow_palette = displayio.Palette(2)
        snow_palette[0] = 0x000000
        snow_palette.make_transparent(0)
        snow_palette[1] = 0xFFFFFF
        snow_grid = displayio.TileGrid(snow_bitmap, pixel_shader=snow_palette)
        snow_grid.hidden = False
        root.append(snow_grid)

        sleigh_bitmap = displayio.Bitmap(
            CHRISTMAS_SLEIGH_WIDTH, CHRISTMAS_SLEIGH_HEIGHT,
            len(CHRISTMAS_SLEIGH_PALETTE_INDEX),
        )
        sleigh_palette = displayio.Palette(len(CHRISTMAS_SLEIGH_PALETTE_INDEX))
        sleigh_palette[0] = 0x000000
        sleigh_palette.make_transparent(0)
        for key, index in CHRISTMAS_SLEIGH_PALETTE_INDEX.items():
            if key != ".":
                red, green, blue = CHRISTMAS_SLEIGH_PALETTE[key]
                sleigh_palette[index] = (red << 16) | (green << 8) | blue
        draw_christmas_sleigh_indexed(sleigh_bitmap, 0, 0,
                                      CHRISTMAS_SLEIGH_WIDTH, CHRISTMAS_SLEIGH_HEIGHT)
        root.append(displayio.TileGrid(sleigh_bitmap, pixel_shader=sleigh_palette, x=0, y=4))

        count_text = "--" if days is None else str(days)
        # Keep the message to the right of the 84px sleigh. The count's left
        # edge stays fixed so any extra digit grows to the right.
        countdown = self._scaled_label(
            root, "{} DAYS".format(count_text), 0xFFFFFF, 103, 4, scale=2,
        )
        self._scaled_label(root, "UNTIL CHRISTMAS", 0xFFFFFF, 103, 20, scale=1)
        self._christmas_group = root
        self._christmas_snow_bitmap = snow_bitmap
        self._christmas_snow_grid = snow_grid
        self._christmas_countdown = countdown
        self._christmas_days = days
        self._christmas_flakes = [
            [SNOW_FLAKE_X[index], SNOW_FLAKE_START_Y[index], -1,
             SNOW_FLAKE_SPEED[index]]
            for index in range(len(SNOW_FLAKE_X))
        ]
        self._christmas_snow_visible = True

    def _update_christmas_scene(self, phase, clock_date):
        if self._christmas_group is None:
            return False
        days = days_until_christmas(clock_date)
        changed = False
        if days != self._christmas_days:
            text = "{} DAYS".format("--" if days is None else days)
            try:
                self._christmas_countdown.text = text
            except AttributeError:
                # The physical renderer's scaled label is a TileGrid bitmap,
                # not a text Label. Replace that layer when the daily count
                # changes; assigning .text stops the main loop on CircuitPython.
                group = self._christmas_group
                old_countdown = self._christmas_countdown
                countdown_index = None
                for index in range(len(group)):
                    if group[index] is old_countdown:
                        countdown_index = index
                        break
                if countdown_index is None:
                    raise RuntimeError("Christmas countdown layer is missing")
                countdown = self._scaled_label(
                    group, text, 0xFFFFFF, 103, 2, scale=2,
                )
                group.remove(countdown)
                group.remove(old_countdown)
                group.insert(countdown_index, countdown)
                self._christmas_countdown = countdown
            self._christmas_days = days
            changed = True
        visible = True
        if self._christmas_snow_visible != visible:
            self._christmas_snow_grid.hidden = not visible
            self._christmas_snow_visible = visible
            changed = True
        if visible:
            phase_value = max(0.0, float(phase or 0))
            for flake in self._christmas_flakes:
                y = (flake[1] + int(phase_value * flake[3])) % 32
                if y != flake[2]:
                    if flake[2] >= 0:
                        self._christmas_snow_bitmap[flake[0], flake[2]] = 0
                    self._christmas_snow_bitmap[flake[0], y] = 1
                    flake[2] = y
                    changed = True
        return changed

    def _show_christmas_tracker(self, phase, clock_date):
        if self._christmas_group is None:
            self._build_christmas_scene({}, clock_date)
        update_started = ticks_ms()
        changed = self._update_christmas_scene(phase, clock_date)
        self._attach_brightness_overlay(self._christmas_group)
        if self.display.root_group is not self._christmas_group:
            self.display.root_group = self._christmas_group
            changed = True
        self._record_animation_update(
            "christmas_tracker", changed, elapsed_seconds(update_started),
            "christmas_tracker",
        )
        if changed:
            self._refresh("christmas_tracker")

    def _bus_intro_cache_matches(self, screen):
        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        return (
            self._bus_intro_group is not None
            and self._bus_intro_words == str(screen.get("words") or "")
            and self._bus_intro_speed == speed
        )

    def _build_bus_intro_scene(self, screen):
        import displayio

        root = displayio.Group()
        motion = displayio.Group(x=0, y=BUS_VERTICAL_OFFSET)
        bitmap = displayio.Bitmap(BUS_WIDTH, BUS_HEIGHT, len(DOUBLE_DECKER_BUS_PALETTE_INDEX))
        palette = displayio.Palette(len(DOUBLE_DECKER_BUS_PALETTE_INDEX))
        palette[0] = 0x000000
        palette.make_transparent(0)
        for symbol, index in DOUBLE_DECKER_BUS_PALETTE_INDEX.items():
            if symbol != ".":
                red, green, blue = BUS_PALETTE[symbol]
                palette[index] = (red << 16) | (green << 8) | blue
        draw_double_decker_bus_indexed(bitmap, 0, 0)
        motion.append(displayio.TileGrid(bitmap, pixel_shader=palette, x=0, y=0))
        words = str(screen.get("words") or "")
        if words:
            self._scaled_label(motion, words, 0xFFAA00, BUS_WIDTH + BUS_TEXT_GAP, 5)
        root.append(motion)
        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        self._bus_intro_group = root
        self._bus_intro_motion_group = motion
        self._bus_intro_words = words
        self._bus_intro_speed = speed

    def _update_bus_intro_scene(self, phase):
        if self._bus_intro_motion_group is None:
            return False
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        next_x = max(0, DISPLAY_WIDTH - int(elapsed * self._bus_intro_speed))
        if self._bus_intro_motion_group.x == next_x:
            return False
        self._bus_intro_motion_group.x = next_x
        return True

    def _show_bus_intro(self, screen, phase):
        if not self._bus_intro_cache_matches(screen):
            self._build_bus_intro_scene(screen)
        update_started = ticks_ms()
        changed = self._update_bus_intro_scene(phase)
        self._attach_brightness_overlay(self._bus_intro_group)
        if self.display.root_group is not self._bus_intro_group:
            self.display.root_group = self._bus_intro_group
            changed = True
        animation_class = self._animation_class(screen, phase)
        self._record_animation_update("bus_intro", changed, elapsed_seconds(update_started), animation_class)
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
            bitmap = displayio.Bitmap(14, 14, 9)
            palette = displayio.Palette(9)
            palette[0] = 0x000000
            palette.make_transparent(0)
            for symbol, color_index in WEATHER_SPRITE_CHAR_INDEX.items():
                if symbol != ".":
                    palette[color_index] = _weather_sprite_color(symbol, stale)
            for y, row in enumerate(item["sprite_rows"]):
                for x, pixel in enumerate(row):
                    bitmap[x, y] = WEATHER_SPRITE_CHAR_INDEX[pixel]
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
            bitmap = displayio.Bitmap(14, 14, 9)
            palette = displayio.Palette(9)
            palette[0] = 0x000000
            palette.make_transparent(0)
            for symbol, color_index in WEATHER_SPRITE_CHAR_INDEX.items():
                if symbol != ".":
                    palette[color_index] = _weather_sprite_color(symbol, stale)
            for y, row in enumerate(item["sprite_rows"]):
                for x, pixel in enumerate(row):
                    bitmap[x, y] = WEATHER_SPRITE_CHAR_INDEX[pixel]
            group.append(displayio.TileGrid(
                bitmap, pixel_shader=palette, x=item["icon_x"], y=TODAY_WEATHER_ICON_Y
            ))
            self._temperature_label(
                group, item["temp_text"], text_color, item["temp_x"], TODAY_WEATHER_TEMPERATURE_Y
            )

    def _sun_weather(self, group, screen, phase):
        import displayio

        stale = bool(screen.get("stale"))
        text_color = 0xAAAAAA if stale else 0xFFFFFF
        label_color = 0x777777 if stale else 0xFFAA00
        values = (
            ("SUNRISE", _format_sun_time(screen.get("sunrise_time")), "clear_day", 0, DISPLAY_WIDTH // 2),
            ("SUNSET", _format_sun_time(screen.get("sunset_time")), "clear_night", DISPLAY_WIDTH // 2, DISPLAY_WIDTH),
        )
        icon_grids = []
        label_grids = []
        for label, value, icon_name, left, right in values:
            width = right - left
            if icon_name == "clear_day":
                for index, character in enumerate(label):
                    label_grid, label_palette = self._sun_text_label(
                        group, character, _sun_weather_rise_label_color(index, phase, stale),
                        left + 27 + index * 8, 11, SUN_WEATHER_TIME_SCALE,
                    )
                    label_grids.append(("rise", index, label_grid, label_palette))
            else:
                for index, character in enumerate(label):
                    label_grid, label_palette = self._sun_text_label(
                        group, character, _sun_weather_set_label_color(index, phase, stale),
                        left + 27 + index * 8, 11, SUN_WEATHER_TIME_SCALE,
                    )
                    label_grids.append(("set", index, label_grid, label_palette))
            rows = _celestial_sprite_rows(icon_name)
            bitmap = displayio.Bitmap(21, 21, 9)
            palette = displayio.Palette(9)
            palette[0] = 0x000000
            palette.make_transparent(0)
            for symbol, color_index in WEATHER_SPRITE_CHAR_INDEX.items():
                if symbol != ".":
                    palette[color_index] = (
                        0x777777 if stale else WEATHER_SPRITE_PALETTE[symbol]
                    )
            for y, row in enumerate(rows):
                for x, pixel in enumerate(row):
                    bitmap[x, y] = WEATHER_SPRITE_CHAR_INDEX[pixel]
            icon_grid = displayio.TileGrid(
                bitmap,
                pixel_shader=palette,
                x=left + 1,
                y=_sun_weather_icon_y(icon_name, phase),
            )
            group.append(icon_grid)
            icon_grids.append((icon_name, icon_grid))
            self._sun_text_label(group, value, text_color, left + 88, 11, SUN_WEATHER_TIME_SCALE)
        return tuple(icon_grids), tuple(label_grids)

    def _sun_text_label(self, group, text, color, x, y, scale):
        import displayio

        text = str(text)
        bitmap = displayio.Bitmap(len(text) * 4 * scale, 5 * scale, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette.make_transparent(0)
        palette[1] = color
        for index, char in enumerate(text):
            rows = WEEKLY_WEATHER_GLYPHS.get(char, (0, 0, 0, 0, 0))
            for row_index, row_bits in enumerate(rows):
                for column in range(WEEKLY_WEATHER_GLYPH_WIDTH):
                    if row_bits & (1 << (WEEKLY_WEATHER_GLYPH_WIDTH - column - 1)):
                        for dx in range(scale):
                            for dy in range(scale):
                                bitmap[index * 4 * scale + column * scale + dx,
                                       row_index * scale + dy] = 1
        grid = displayio.TileGrid(bitmap, pixel_shader=palette, x=x, y=y)
        group.append(grid)
        return grid, palette

    def _show_sun_weather(self, screen, phase):
        import displayio

        key = (
            screen.get("sunrise_time") or "--:--",
            screen.get("sunset_time") or "--:--",
            bool(screen.get("stale")),
        )
        if (
            self._sun_group is None
            or self._sun_key != key
            or self.display.root_group is not self._sun_group
        ):
            group = displayio.Group()
            self._sun_icon_grids, self._sun_label_grids = self._sun_weather(group, screen, phase)
            self._sun_group = group
            self._sun_key = key
            self._present(group)
            return

        changed = False
        stale = bool(screen.get("stale"))
        for icon_name, icon_grid in self._sun_icon_grids:
            next_y = _sun_weather_icon_y(icon_name, phase)
            if icon_grid.y != next_y:
                icon_grid.y = next_y
                changed = True
        for label_kind, index, label_grid, palette in self._sun_label_grids:
            next_color = (
                _sun_weather_rise_label_color(index, phase, stale)
                if label_kind == "rise"
                else _sun_weather_set_label_color(index, phase, stale)
            )
            if palette[1] != next_color:
                palette[1] = next_color
                changed = True
        if changed:
            self._refresh(animation_class="weather_sun_slide")

    def _bin_collection_cache_matches(self, screen, clock_date, header_kind):
        items = screen.get("collections") or []
        key = (
            str(screen.get("title") or "NEXT COLLECTION"),
            " / ".join(str(item.get("label") or "") for item in items),
            _bin_collection_due_label(screen.get("collection_date"), clock_date),
            bool(screen.get("stale")),
        )
        weather = screen.get("weather")
        return (
            self._bin_group is not None
            and self._bin_key == key
            and self._bin_header_kind == header_kind
            and self._bin_weather == weather
        )

    def _build_bin_lorry(self, kind):
        import displayio
        from recycling_lorries import INDEX, draw_indexed, palette_for

        bitmap = displayio.Bitmap(BIN_LORRY_WIDTH, BIN_LORRY_HEIGHT + BIN_LORRY_Y, len(INDEX))
        draw_indexed(bitmap, 0, BIN_LORRY_Y, kind=kind)
        palette = palette_for(kind, limited_palette=MATRIX_BIT_DEPTH == 1)
        palette.make_transparent(0)
        return displayio.TileGrid(bitmap, pixel_shader=palette, x=DISPLAY_WIDTH, y=0)

    def _build_bin_collection(self, screen, clock_time, clock_date, phase, header_kind):
        import displayio

        group = displayio.Group()
        content = displayio.Group()
        title = str(screen.get("title") or "NEXT COLLECTION")
        items = screen.get("collections") or []
        labels = " / ".join(str(item.get("label") or "") for item in items)
        self._bin_title = self._label(content, _clip(title, 40), 0xFFAA00, 0, 3)
        due_label = _bin_collection_due_label(screen.get("collection_date"), clock_date)
        due_width = len(due_label) * WEATHER_FONT_WIDTH
        type_width = max(
            0,
            DISPLAY_WIDTH - BIN_LORRY_WIDTH - due_width - HEADER_GAP * 2,
        )
        type_label = _fit_text_pixels(labels, type_width)
        type_label_width = len(type_label) * WEATHER_FONT_WIDTH
        self._bin_content_group = content
        self._bin_lorry_group = displayio.Group()
        self._bin_lorry_grid = self._build_bin_lorry(_bin_collection_lorry_kind(screen))
        self._bin_lorry_grid.x = 0
        self._bin_lorry_group.append(self._bin_lorry_grid)
        self._bin_lorry_label = self._label(
            self._bin_lorry_group,
            type_label,
            0xFFFFFF,
            BIN_LORRY_WIDTH + HEADER_GAP,
            14,
        )
        due_x = BIN_LORRY_WIDTH + HEADER_GAP * 2 + type_label_width
        self._bin_date = self._label(self._bin_lorry_group, due_label, 0xAAAAAA, due_x, 14)
        group.append(self._bin_lorry_group)
        # The new artwork fills most of the matrix height; keep the title
        # legible when the moving sprite passes behind it.
        group.append(content)
        self._bin_footer_group = self._bin_lorry_group
        self._bin_date_group = self._bin_lorry_group
        self._bin_label = self._bin_lorry_label
        if screen.get("stale"):
            self._bin_stale = self._label(group, "STALE", 0xFF3300, STALE_X, 3)
        else:
            self._bin_stale = None
        self._mask(group, HEADER_SLOT_X, 0, HEADER_SLOT_WIDTH, 8)
        if header_kind == "weather":
            self._bin_header_group = displayio.Group()
            self._header_weather(self._bin_header_group, screen.get("weather"), 0)
            group.append(self._bin_header_group)
            self._bin_clock_label = None
        else:
            self._bin_header_group = None
            self._bin_clock_label = self._label(group, clock_time, 0xFFAA00, CLOCK_X, 3)
        self._bin_group = group
        self._bin_header_kind = header_kind
        self._bin_weather = dict(screen["weather"]) if isinstance(screen.get("weather"), dict) else None
        self._bin_key = (
            title,
            labels,
            _bin_collection_due_label(screen.get("collection_date"), clock_date),
            bool(screen.get("stale")),
        )

    def _show_bin_collection(self, screen, clock_time, clock_date, phase):
        update_started = ticks_ms()
        header_kind, header_offset = _header_item_state(phase, screen.get("weather"))
        if not self._bin_collection_cache_matches(screen, clock_date, header_kind):
            self._build_bin_collection(screen, clock_time, clock_date, phase, header_kind)
            changed = True
        else:
            changed = False
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        next_lorry_x = _bin_collection_footer_x(screen, elapsed, clock_date)
        if self._bin_lorry_group.x != next_lorry_x:
            self._bin_lorry_group.x = next_lorry_x
            changed = True
        if self._bin_clock_label is not None:
            if self._bin_clock_label.text != clock_time:
                self._bin_clock_label.text = clock_time
                changed = True
            next_x = CLOCK_X + header_offset
            if self._bin_clock_label.x != next_x:
                self._bin_clock_label.x = next_x
                changed = True
        elif self._bin_header_group is not None and self._bin_header_group.x != header_offset:
            self._bin_header_group.x = header_offset
            changed = True
        self._attach_brightness_overlay(self._bin_group)
        if self.display.root_group is not self._bin_group:
            self.display.root_group = self._bin_group
            changed = True
        if changed:
            animation_class = self._animation_class(screen, phase)
            self._refresh(animation_class=animation_class)
        else:
            animation_class = self._animation_class(screen, phase)
        self._record_animation_update(
            "bin_collection", changed, elapsed_seconds(update_started), animation_class
        )

    def _header_weather(self, group, weather, offset=0):
        # The header keeps a steady clock; forecast screens carry weather.
        return

    @staticmethod
    def _novelty_weather_key(weather):
        if not isinstance(weather, dict):
            return None
        return (
            _weather_text(weather), _weather_icon(weather)[0],
            bool(weather.get("stale")),
        )

    def _show_novelty(self, screen, heading, lines, clock_time, phase):
        """Keep joke/fact content static while the shared header stays live."""
        import displayio

        weather = screen.get("weather")
        key = (heading, tuple(lines), self._novelty_weather_key(weather))
        if getattr(self, "_novelty_key", None) != key:
            root = displayio.Group()
            self._label(root, heading, 0xFFAA00, 0, NOVELTY_HEADING_Y)
            for index, line in enumerate(lines):
                self._label(root, line, 0xFFFFFF, 0, NOVELTY_FIRST_LINE_Y + index * 8)
            self._mask(root, HEADER_SLOT_X, 0, HEADER_SLOT_WIDTH, 8)

            clock_group = displayio.Group()
            clock_label = self._label(clock_group, clock_time, 0xFFAA00, CLOCK_X, 3)
            root.append(clock_group)
            weather_group = displayio.Group()
            if isinstance(weather, dict):
                self._header_weather(weather_group, weather, 0)
            root.append(weather_group)

            self._novelty_key = key
            self._novelty_group = root
            self._novelty_clock_group = clock_group
            self._novelty_clock_label = clock_label
            self._novelty_weather_group = weather_group

        changed = False
        if self._novelty_clock_label.text != clock_time:
            self._novelty_clock_label.text = clock_time
            changed = True
        item, _offset = _header_item_state(phase, weather)
        clock_x = 0 if item == "clock" else DISPLAY_WIDTH
        weather_x = 0 if item == "weather" else DISPLAY_WIDTH
        if self._novelty_clock_group.x != clock_x:
            self._novelty_clock_group.x = clock_x
            changed = True
        if self._novelty_weather_group.x != weather_x:
            self._novelty_weather_group.x = weather_x
            changed = True

        if self.display.root_group is not self._novelty_group:
            self._present(self._novelty_group)
        elif changed:
            self._refresh()

    def show(self, screen, clock_time="--:--", clock_date="", phase=2, now_epoch=None):
        import displayio

        empty_state = screen.get("empty_state")
        kind = screen.get("kind")
        presentation_mode = getattr(self, "presentation_mode", MATRIX_PRESENTATION_MODE)
        if presentation_mode != "auto_refresh":
            use_rail_auto_refresh = (
                MATRIX_RAIL_AUTO_REFRESH_EXPERIMENT
                and not empty_state
                and kind == "rail_combined"
            )
            if use_rail_auto_refresh != getattr(
                self, "_rail_auto_refresh_override", False
            ):
                self.display.auto_refresh = use_rail_auto_refresh
                self._rail_auto_refresh_override = use_rail_auto_refresh
                print(
                    "RAIL PRESENTATION auto_refresh={}".format(
                        use_rail_auto_refresh
                    )
                )
        if not empty_state and kind in ("dad_joke", "random_fact", "insult_of_hour", "quotes", "today"):
            if kind == "today":
                update_started = ticks_ms()
                date_label = _today_compact_date_label(clock_date)
                weather = screen.get("weather") or {}
                temperature = _weather_text(weather)
                key = ("TODAY", date_label, clock_time, temperature,
                       _weather_icon(weather)[0], bool(weather.get("stale") or screen.get("stale")))
                if getattr(self, "_static_key", None) != key:
                    import displayio
                    group = displayio.Group()
                    date_x = _today_date_position(date_label, clock_time)
                    self._today_date_bitmap(group, date_label, date_x)
                    icon_name = _weather_icon(weather)[0] or "unknown"
                    rows = _weather_sprite_rows(icon_name)
                    bitmap = displayio.Bitmap(
                        TODAY_HEADER_ICON_SIZE, TODAY_HEADER_ICON_SIZE, 9,
                    )
                    palette = displayio.Palette(9)
                    palette[0] = 0x000000
                    palette.make_transparent(0)
                    for symbol, color_index in WEATHER_SPRITE_CHAR_INDEX.items():
                        if symbol != ".":
                            palette[color_index] = _weather_sprite_color(
                                symbol, bool(weather.get("stale"))
                            )
                    for row_index in range(TODAY_HEADER_ICON_SIZE):
                        source_row = rows[row_index * len(rows) // TODAY_HEADER_ICON_SIZE]
                        for column in range(TODAY_HEADER_ICON_SIZE):
                            pixel = source_row[column * len(rows[0]) // TODAY_HEADER_ICON_SIZE]
                            bitmap[column, row_index] = WEATHER_SPRITE_CHAR_INDEX[pixel]
                    group.append(displayio.TileGrid(
                        bitmap, pixel_shader=palette,
                        x=TODAY_HEADER_ICON_X, y=TODAY_HEADER_ICON_Y,
                    ))
                    time_x = max(0, DISPLAY_WIDTH - len(clock_time) * 6 * TODAY_TIME_SCALE + 10)
                    self._scaled_label(group, clock_time, 0xFFAA00, time_x,
                                       TODAY_TIME_Y, scale=TODAY_TIME_SCALE)
                    temperature_x = max(0, DISPLAY_WIDTH - len(temperature) * 6 * TODAY_TIME_SCALE)
                    self._scaled_label(group, temperature, 0xFFFFFF, temperature_x,
                                       TODAY_TEMPERATURE_Y, scale=TODAY_TIME_SCALE)
                    if key[-1]:
                        self._label(group, "STALE", 0x888888, 0, 0)
                    self._static_group = group
                    self._static_key = key
                date_changed = self._update_today_date_colors(phase)
                self._record_animation_update(
                    "today", date_changed, elapsed_seconds(update_started), "today_date"
                )
                if self.display.root_group is not self._static_group:
                    self._present(self._static_group)
                elif date_changed:
                    self._refresh(animation_class="today_date")
                return
            heading = ("QUOTES VIA ZENQUOTES.IO" if kind == "quotes" else
                       "DAD JOKE" if kind == "dad_joke" else "DID YOU KNOW?" if kind == "random_fact" else "INSULT OF THE HOUR")
            if kind == "quotes" and screen.get("stale"):
                heading += " STALE"
            lines = _quote_page(screen, phase) if kind == "quotes" else _novelty_page(screen, phase)
            if kind in ("dad_joke", "random_fact"):
                self._show_novelty(screen, heading, lines, clock_time, phase)
                return
            key = (heading, tuple(lines))
            if getattr(self, "_static_key", None) != key:
                group = displayio.Group()
                self._label(group, heading, 0xFFAA00, 0, NOVELTY_HEADING_Y)
                for index, line in enumerate(lines):
                    self._label(group, line, 0xFFFFFF, 0, NOVELTY_FIRST_LINE_Y + index * 8)
                self._static_group = group
                self._static_key = key
            if self.display.root_group is not self._static_group:
                self._present(self._static_group)
            return
        if not empty_state and kind == "flash":
            self._show_flash(screen, phase)
            return

        if not empty_state and kind == "football_score":
            self._show_football(screen, phase, now_epoch)
            return

        if not empty_state and kind == "steam_train_intro":
            self._show_steam_train(screen, phase)
            return

        if not empty_state and kind == "christmas_tracker_intro":
            self._show_christmas_intro(phase)
            return

        if not empty_state and kind == "bus_intro":
            self._show_bus_intro(screen, phase)
            return

        if not empty_state and kind == "bin_collection":
            self._show_bin_collection(screen, clock_time, clock_date, phase)
            return

        if not empty_state and kind == "christmas_tracker":
            self._show_christmas_tracker(phase, clock_date)
            return

        if not empty_state and kind == "bus_departures_combined":
            group = displayio.Group()
            self._bus_departures_split(group, screen, now_epoch)
            self._present(group)
            return

        if not empty_state and kind == "bus_departures":
            group = displayio.Group()
            self._bus_departures(group, screen, phase)
            self._label(group, clock_time, 0xFFAA00, CLOCK_X, 3)
            if screen.get("stale"):
                self._label(group, "STALE", 0xFF3300, STALE_X, 3)
            self._present(group)
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
            if kind == "weather_sun":
                self._show_sun_weather(screen, phase)
                return
            if kind == "weather_weekly":
                items = screen.get("days") or []
                key = (bool(screen.get("stale")), tuple(
                    (item.get("weekday"), item.get("weather_code"), item.get("icon"),
                     item.get("temperature_max_c"))
                    for item in items if isinstance(item, dict)
                ))
            else:
                items = screen.get("blocks") or []
                key = (bool(screen.get("stale")), tuple(
                    (item.get("label"), item.get("weather_code"), item.get("icon"),
                     item.get("temperature_c"))
                    for item in items if isinstance(item, dict)
                ))
            if self._weather_keys.get(kind) != key:
                group = displayio.Group()
                if kind == "weather_weekly":
                    self._weekly_weather(group, screen)
                else:
                    self._today_weather(group, screen)
                self._weather_groups[kind] = group
                self._weather_keys[kind] = key
            group = self._weather_groups[kind]
            if self.display.root_group is not group:
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
        elif kind == "bus_intro":
            self._show_bus_intro(screen, phase)
            return
        elif kind == "theme_park_queues":
            self._queues(group, screen, phase)
        elif kind == "bus_departures":
            self._bus_departures(group, screen, phase)
        elif kind == "calendar_agenda":
            self._calendar(group, screen, phase, clock_date)
        elif kind == "flash":
            self._flash(group, screen, phase)
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

    def _text(self, value, x, y, color, scale=1):
        glyphs = {
            " ": (0, 0, 0, 0, 0), "-": (0, 0, 1, 0, 0), ":": (0, 1, 0, 0, 1),
            "0": (1, 1, 1, 1, 1), "1": (0, 1, 1, 0, 0), "2": (1, 0, 1, 1, 1),
            "3": (1, 0, 1, 0, 1), "4": (1, 1, 1, 0, 0), "5": (1, 1, 0, 0, 1),
            "6": (1, 1, 0, 1, 1), "7": (1, 0, 0, 0, 0), "8": (1, 1, 1, 1, 1), "9": (1, 1, 1, 0, 1),
        }
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        pixel_color = color if callable(color) else None
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
                        for dx in range(scale):
                            for dy in range(scale):
                                px, py = x + column * scale + dx, y + row * scale + dy
                                self._pixel(px, py, pixel_color(px, py) if pixel_color else color)
            x += WEATHER_FONT_WIDTH * scale

    def _text_scaled(self, value, x, y, color, scale=WEEKLY_WEATHER_TEXT_SCALE):
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
        x = max(0, DISPLAY_WIDTH - int(elapsed * speed))
        offset = STEAM_TRAIN_VERTICAL_OFFSET

        def fill_rect(px, py, width, height, color):
            self._fill_rect(px, py + offset, width, height, color)

        fill_rect(x + 4, 12, 29, 9, (255, 255, 255))
        fill_rect(x + 30, 7, 16, 14, (255, 255, 255))
        fill_rect(x + 8, 5, 7, 7, (170, 170, 170))
        fill_rect(x + 6, 4, 11, 2, (170, 170, 170))
        fill_rect(x + 28, 5, 20, 3, (255, 170, 0))
        fill_rect(x, 17, 6, 3, (255, 170, 0))
        fill_rect(x + 16, 9, 16, 3, (255, 255, 255))
        fill_rect(x + 34, 9, 7, 6, (0, 0, 0))
        wheel_points = (
            (-2, -3), (-1, -3), (0, -3), (1, -3), (2, -3),
            (-3, -2), (3, -2), (-3, -1), (3, -1),
            (-3, 0), (0, 0), (3, 0),
            (-3, 1), (3, 1), (-3, 2), (3, 2),
            (-2, 3), (-1, 3), (0, 3), (1, 3), (2, 3),
        )
        for center_x in (11, 34, 43):
            for dx, dy in wheel_points:
                self._pixel(x + center_x + dx, 23 + dy + offset, (255, 51, 0))
        words = str(screen.get("words") or "")
        if words:
            self._text(words, x + STEAM_TRAIN_WIDTH + STEAM_TRAIN_TEXT_GAP,
                       12 + offset, (255, 170, 0))

    def _bus_intro(self, screen, phase):
        try:
            speed = max(8.0, min(80.0, float(screen.get("animation_speed") or 24)))
        except (TypeError, ValueError):
            speed = 24.0
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        x = max(0, DISPLAY_WIDTH - int(elapsed * speed))
        draw_double_decker_bus(
            self._pixel, x, BUS_VERTICAL_OFFSET,
            limited_palette=MATRIX_BIT_DEPTH == 1,
        )
        words = str(screen.get("words") or "")
        if words:
            self._text(
                words, x + BUS_WIDTH + BUS_TEXT_GAP, 12 + BUS_VERTICAL_OFFSET,
                (255, 170, 0),
            )

    def _bin_collection(self, screen, phase, clock_date=""):
        from recycling_lorries import draw

        items = screen.get("collections") or []
        labels = " / ".join(str(item.get("label") or "") for item in items)
        try:
            elapsed = max(0.0, float(phase or 0))
        except (TypeError, ValueError):
            elapsed = 0.0
        x = _bin_collection_footer_x(screen, elapsed, clock_date)
        draw(
            self._pixel,
            x,
            BIN_LORRY_Y,
            kind=_bin_collection_lorry_kind(screen),
            limited_palette=MATRIX_BIT_DEPTH == 1,
        )
        self._text(_clip(str(screen.get("title") or "NEXT COLLECTION"), 40), 0, 3, (255, 170, 0))
        due_label = _bin_collection_due_label(screen.get("collection_date"), clock_date)
        due_width = len(due_label) * WEATHER_FONT_WIDTH
        type_width = max(
            0,
            DISPLAY_WIDTH - BIN_LORRY_WIDTH - due_width - HEADER_GAP * 2,
        )
        type_label = _fit_text_pixels(labels, type_width)
        type_label_width = len(type_label) * WEATHER_FONT_WIDTH
        due_x = x + BIN_LORRY_WIDTH + HEADER_GAP * 2 + type_label_width
        self._text(type_label, x + BIN_LORRY_WIDTH + HEADER_GAP, 14, (255, 255, 255))
        self._text(due_label, due_x, 14, (170, 170, 170))

    def _christmas_tracker(self, screen, phase, clock_date):
        white = (255, 255, 255)
        snow_phase = max(0.0, float(phase or 0))
        for index in range(len(SNOW_FLAKE_X)):
            y = (SNOW_FLAKE_START_Y[index]
                 + int(snow_phase * SNOW_FLAKE_SPEED[index])) % 32
            self._pixel(SNOW_FLAKE_X[index], y, white)
        days = days_until_christmas(clock_date)
        count = "--" if days is None else str(days)
        draw_christmas_sleigh(self._pixel, 0, 4, DISPLAY_WIDTH, 32)
        self._text("{} DAYS".format(count), 103, 4, white, scale=2)
        self._text("UNTIL CHRISTMAS", 103, 20, white)

    def _christmas_tracker_intro(self, screen, phase):
        elapsed = max(0.0, float(phase or 0))
        x = max(0, DISPLAY_WIDTH - int(elapsed * (DISPLAY_WIDTH / SLEIGH_SLIDE_SECONDS)))
        draw_christmas_sleigh(self._pixel, x, 4, DISPLAY_WIDTH, 32)
        self._text("HO HO HO...", x + 88, 5, (255, 170, 0))

    def _rail_service(self, service, color, x_offset, y, right_edge, ordinal=1):
        ordinal_text, time_text, destination, platform, status = _rail_columns(service, ordinal)
        status_x = (
            max(0, CLOCK_X - HEADER_GAP - 10 - len(status) * WEATHER_FONT_WIDTH)
            if status else int(right_edge)
        )
        platform_x = RAIL_PLATFORM_X
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
            for y, row in enumerate(item["sprite_rows"]):
                for x, pixel in enumerate(row):
                    if pixel != ".":
                        self._pixel(item["icon_x"] + x,
                                    WEEKLY_WEATHER_ICON_Y + y,
                                    _rgb_tuple(_weather_sprite_color(pixel, stale)))
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
            for y, row in enumerate(item["sprite_rows"]):
                for x, pixel in enumerate(row):
                    if pixel != ".":
                        self._pixel(item["icon_x"] + x,
                                    TODAY_WEATHER_ICON_Y + y,
                                    _rgb_tuple(_weather_sprite_color(pixel, stale)))
            self._text_scaled(
                item["temp_text"], item["temp_x"], TODAY_WEATHER_TEMPERATURE_Y, text_color
            )

    def _sun_weather(self, screen, phase):
        stale = bool(screen.get("stale"))
        text_color = (170, 170, 170) if stale else (255, 255, 255)
        label_color = (119, 119, 119) if stale else (255, 170, 0)
        values = (
            ("SUNRISE", _format_sun_time(screen.get("sunrise_time")), "clear_day", 0, DISPLAY_WIDTH // 2),
            ("SUNSET", _format_sun_time(screen.get("sunset_time")), "clear_night", DISPLAY_WIDTH // 2, DISPLAY_WIDTH),
        )
        for label, value, icon_name, left, right in values:
            width = right - left
            for index, character in enumerate(label):
                label_palette_color = (
                    _sun_weather_rise_label_color(index, phase, stale)
                    if icon_name == "clear_day"
                    else _sun_weather_set_label_color(index, phase, stale)
                )
                self._text_scaled(
                    character,
                    left + 27 + index * 8,
                    11,
                    _rgb_tuple(label_palette_color),
                    SUN_WEATHER_TIME_SCALE,
                )
            icon_rows = _celestial_sprite_rows(icon_name)
            icon_x = left + 1
            for y, row in enumerate(icon_rows):
                for x, pixel in enumerate(row):
                    if pixel != ".":
                        color = 0x777777 if stale else WEATHER_SPRITE_PALETTE[pixel]
                        self._pixel(
                            icon_x + x,
                            _sun_weather_icon_y(icon_name, phase) + y,
                            _rgb_tuple(color),
                        )
            self._text_scaled(value, left + 88, 11, text_color, SUN_WEATHER_TIME_SCALE)

    def _draw_screen(self, screen, phase, clock_date="", clock_time="--:--", now_epoch=None):
        kind = screen.get("kind")
        if kind in ("dad_joke", "random_fact", "insult_of_hour", "quotes", "today"):
            if kind == "today":
                weather = screen.get("weather") or {}
                date_label = _today_compact_date_label(clock_date)
                date_x = _today_date_position(date_label, clock_time)
                width = _today_date_width(len(date_label))
                position = _today_date_sweep_position(phase, width)
                colors = [_today_date_blend_color(_today_date_column_state(position, width, x))
                          for x in range(width)]
                def date_pixel_color(x, y):
                    return _rgb_tuple(_today_date_pixel_color(
                        colors[x - date_x], x - date_x, y - TODAY_DATE_Y
                    ))
                for index, character in enumerate(date_label):
                    self._text(
                        character, date_x + index * TODAY_DATE_CHAR_ADVANCE, TODAY_DATE_Y,
                        date_pixel_color,
                        scale=TODAY_DATE_SCALE,
                    )
                icon_name = _weather_icon(weather)[0] or "unknown"
                rows = _weather_sprite_rows(icon_name)
                for y in range(TODAY_HEADER_ICON_SIZE):
                    source_row = rows[y * len(rows) // TODAY_HEADER_ICON_SIZE]
                    for x in range(TODAY_HEADER_ICON_SIZE):
                        pixel = source_row[x * len(rows[0]) // TODAY_HEADER_ICON_SIZE]
                        if pixel != ".":
                            self._pixel(
                                TODAY_HEADER_ICON_X + x,
                                TODAY_HEADER_ICON_Y + y,
                                _rgb_tuple(_weather_sprite_color(
                                    pixel, bool(weather.get("stale"))
                                )),
                            )
                temperature = _weather_text(weather) or "--C"
                self._text(clock_time,
                           max(0, DISPLAY_WIDTH - len(clock_time) * 6 * TODAY_TIME_SCALE + 10),
                           TODAY_TIME_Y, (255, 170, 0), scale=TODAY_TIME_SCALE)
                self._text(temperature,
                           max(0, DISPLAY_WIDTH - len(temperature) * 6 * TODAY_TIME_SCALE),
                           TODAY_TEMPERATURE_Y, (255, 255, 255), scale=TODAY_TIME_SCALE)
                if weather.get("stale") or screen.get("stale"):
                    self._text("STALE", 0, 1, (136, 136, 136))
                return
            heading = ("QUOTES VIA ZENQUOTES.IO" if kind == "quotes" else
                       "DAD JOKE" if kind == "dad_joke" else "DID YOU KNOW?" if kind == "random_fact" else "INSULT OF THE HOUR")
            if kind == "quotes" and screen.get("stale"):
                heading += " STALE"
            self._text(heading, 0, NOVELTY_HEADING_Y, (255, 170, 0))
            lines = _quote_page(screen, phase) if kind == "quotes" else _novelty_page(screen, phase)
            for index, line in enumerate(lines):
                self._text(line, 0, NOVELTY_FIRST_LINE_Y + index * 8, (255, 255, 255))
        elif kind == "steam_train_intro":
            self._steam_train(screen, phase)
        elif kind == "christmas_tracker_intro":
            self._christmas_tracker_intro(screen, phase)
        elif kind == "bus_intro":
            self._bus_intro(screen, phase)
        elif kind == "weather_weekly":
            self._weekly_weather(screen)
        elif kind == "weather_today":
            self._today_weather(screen)
        elif kind == "weather_sun":
            self._sun_weather(screen, phase)
        elif kind == "bin_collection":
            self._bin_collection(screen, phase, clock_date)
        elif kind == "football_score":
            from football_ball import ROWS as BALL_ROWS

            ball_x, info_visible = football_presentation_position(
                phase, screen.get("status") != "IN" and screen.get("ball_animation", False),
                screen.get("animation_speed"),
            )
            for row, pixels in enumerate(BALL_ROWS):
                for column, pixel in enumerate(pixels):
                    if pixel == "W":
                        color = (245, 245, 245)
                    elif pixel == "D":
                        color = (48, 48, 48)
                    else:
                        continue
                    self._pixel(ball_x + column, 8 + row, color)
            if info_visible:
                max_chars = max(0, (DISPLAY_WIDTH - FOOTBALL_TEXT_X) // 6)
                rows = football_screen_lines(screen, now_epoch)
                if screen.get("goal_flash_active") and screen.get("status") == "IN":
                    team = screen.get("home_team") if screen.get("goal_side") == "home" else screen.get("away_team")
                    rows = rows[:3] + ("GOAL {}".format(str(team or "SCORED").upper()),)
                for index, line in enumerate(rows):
                    line_text = _clip(str(line), max_chars)
                    base_color = (255, 255, 255)
                    if screen.get("status") == "PRE" and index < 2:
                        y = 5 + index * 13
                    else:
                        y = index * 8
                    if ((screen.get("status") == "PRE" and index == 0)
                            or (screen.get("status") != "PRE" and index == 1)):
                        base_color = FOOTBALL_FIXTURE_TEXT_COLOR
                    color = base_color
                    if index in (0, 1):
                        span = football_team_name_span(screen, line_text)
                        if span:
                            start, name, team_color = span
                            if team_color:
                                positions = {
                                    char_index: team_color
                                    for char_index, character in enumerate(name, start=start)
                                    if character != " "
                                }

                                def color(px, _py, positions=positions, base=base_color):
                                    char_index = int(px) // 6 - FOOTBALL_TEXT_X // 6
                                    rgb = positions.get(char_index)
                                    return rgb if rgb is not None else base

                    self._text(line_text, FOOTBALL_TEXT_X, y, color)
        elif kind == "christmas_tracker":
            self._christmas_tracker(screen, phase, clock_date)
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
        elif kind == "bus_departures_combined":
            for x, title, status, stale, rows in split_sl7_rows(screen, now_epoch):
                self._text(title, x + 1, 0, (255, 51, 0) if stale else (255, 170, 0))
                if stale and rows:
                    self._text("!", x + 119, 0, (255, 51, 0))
                if not rows:
                    empty = ("OFF" if status == "disabled" else
                             "Unavailable" if status == "unavailable" else
                             "STALE" if stale else "No services")
                    self._text(empty, x + 2, 8, (255, 51, 0) if stale else (255, 255, 255))
                for index, (due, time_text, cancelled, _delayed) in enumerate(rows):
                    y = 8 + index * 8
                    time_color = (255, 51, 0) if cancelled else (255, 255, 255)
                    prefix, value = split_sl7_due_parts(due)
                    due_color = (255, 51, 0) if cancelled or prefix == "CXL" else (255, 170, 0)
                    self._text(time_text[:5], x + SL7_TIME_COLUMN_X, y, time_color)
                    self._text(prefix, x + SL7_DUE_COLUMN_X, y, due_color)
                    if value:
                        value_x = x + SL7_DUE_COLUMN_X + len("Due in ") * WEATHER_FONT_WIDTH
                        self._text(value, value_x, y, (255, 255, 255))
        elif kind == "bus_departures":
            title = _clip(screen.get("title") or "SL7", 26)
            self._text(title, 0, 0, (255, 170, 0))
            departures = screen.get("departures") or []
            if screen.get("status") == "unavailable":
                self._text("SL7 unavailable", 0, 16, (255, 20, 0))
            elif not departures:
                self._text("No SL7 services", 0, 16, (255, 255, 255))
            else:
                for index, item in enumerate(departures[:3]):
                    y = (8, 16, 24)[index]
                    color = (255, 20, 0) if item.get("cancelled") else (255, 255, 255)
                    destination = _fit_text_pixels(item.get("destination") or "--", 170)
                    self._text(destination, 0, y, color)
                    self._text(item.get("local_time") or _bus_time(item.get("estimated") or item.get("planned")), 178, y, color)
                    status = "CANCEL" if item.get("cancelled") else str(item.get("due_text") or "")
                    if status:
                        self._text(status[:6], max(218, _right_aligned_x(status[:6], DISPLAY_WIDTH)), y, color)
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
            if screen.get("title") == "ASSISTANT":
                self._text("ASSISTANT", 0, 1, (255, 170, 0))
                _, lines = assistant_message_page(screen.get("label"), phase)
                for index, line in enumerate(lines):
                    self._text(line, 0, ASSISTANT_MESSAGE_TEXT_Y + index * 8, (255, 255, 255))
            else:
                x = reminder_scroll_x(screen, phase)
                self._text(str(screen.get("label") or ""),
                           x + REMINDER_TEXT_X, 5, (255, 255, 255), scale=REMINDER_TEXT_SCALE)
                for px in range(REMINDER_CLOCK_SIZE):
                    for py in range(REMINDER_CLOCK_SIZE):
                        if reminder_clock_pixel(px, py):
                            self._pixel(x + px, 1 + py, (255, 170, 0))
        else:
            self._text(_clip(screen.get("title") or "Display unavailable", 30), 0, 0, (255, 255, 255))

    def _header_weather(self, weather, offset=0):
        # The header keeps a steady clock; forecast screens carry weather.
        return

    def show(self, screen, clock_time="--:--", clock_date="", phase=2, now_epoch=None):
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
            self._draw_screen(screen, phase, clock_date, clock_time, now_epoch)
            if kind not in WEATHER_FULLSCREEN_KINDS and kind not in ("steam_train_intro", "christmas_tracker_intro", "bus_intro", "bus_departures_combined", "flash", "today", "insult_of_hour", "quotes", "christmas_tracker", "football_score"):
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
        elif kind == "christmas_tracker_intro":
            print("CHRISTMAS INTRO HO HO HO...")
        elif kind == "bus_intro":
            print("BUS {}".format(screen.get("words") or ""))
        elif kind == "bin_collection":
            for item in screen.get("collections") or []:
                print(str(item.get("label") or ""))
            print(_bin_collection_due_label(screen.get("collection_date"), clock_date))
        elif kind == "football_score":
            from football_screens import football_screen_lines

            for line in football_screen_lines(screen, now_epoch):
                print(line)
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

    def show_loading(self, title="UPCOMING", message="Loading...", clock_time="--:--"):
        if self.pixels is None:
            print("\n{} {} {}".format(title, message, clock_time))
            return
        self.pixels.fill((0, 0, 0))
        title = _clip(title, 30)
        message = _clip(message, 30)
        message_x = max(0, (DISPLAY_WIDTH - len(message) * WEATHER_FONT_WIDTH) // 2)
        self._text(title, 0, 0, (255, 170, 0))
        self._text(message, message_x, 18, (255, 255, 255))
        self._text(clock_time, CLOCK_X, 0, (255, 100, 0))
        self.pixels.show()

    def show_diagnostic(self, color):
        """Keep fixture mode observable when the hardware path is unavailable."""
        if self.pixels is not None:
            self.pixels.fill(_rgb_tuple(int(color)))
            self.pixels.show()
        print("DIAGNOSTIC 0x{:06X}".format(int(color)))


def create(settings):
    if settings.DISPLAY_BACKEND == "matrix":
        return MatrixDisplay(
            getattr(settings, "MATRIX_BRIGHTNESS_PERCENT", 100),
            getattr(settings, "STEAM_TRAIN_TEST", False),
        )
    return FixtureDisplay()
