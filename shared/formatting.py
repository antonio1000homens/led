"""Fixed-width board formatting, independent of display hardware."""


QUEUE_VISIBLE_ROWS = 3
QUEUE_HOLD_SECONDS = 1.0
QUEUE_SLIDE_SECONDS = 0.3
QUEUE_STEP_SECONDS = QUEUE_HOLD_SECONDS + QUEUE_SLIDE_SECONDS
RAIL_MARQUEE_SPEED = 48.0
RAIL_MARQUEE_DELAY_SECONDS = 1.2
RAIL_MARQUEE_GAP = 56
CALLING_LABEL = "CALLING AT: "
CALLING_MARQUEE_PAUSE_SECONDS = 3.0
CALLING_STATION_FONT_WIDTH = 5
DEFAULT_STATION_LIST_SPACING = 10
# Shared four-row grid for the physical 32px panel.
# Four 7px glyph baselines with one-pixel inter-row gaps.  The font's
# ascender is above the label coordinate, so this uses the full 32px panel
# without clipping the first row or leaving a large unused bottom band.
RAIL_ROW_Y = (4, 12, 20, 28)
RAIL_SUMMARY_SECONDS = 8.0
RAIL_CALLING_SECONDS = 8.0
AGENDA_VISIBLE_ROWS = 3
AGENDA_SLIDE_SECONDS = 0.4
AGENDA_PAGE_SECONDS = 5.0
AGENDA_ROW_WIDTH = 42
AGENDA_FONT_WIDTH = 5
AGENDA_WHEN_WIDTH = 11
AGENDA_TITLE_GAP = 1
AGENDA_TITLE_X = (AGENDA_WHEN_WIDTH + AGENDA_TITLE_GAP) * AGENDA_FONT_WIDTH
AGENDA_TITLE_VISIBLE_CHARS = AGENDA_ROW_WIDTH - AGENDA_WHEN_WIDTH - AGENDA_TITLE_GAP
AGENDA_MARQUEE_SPEED = 30.0
AGENDA_MARQUEE_PAUSE_SECONDS = 1.25


def _pad_right(value, width):
    value = str(value or "")
    width = max(0, int(width or 0))
    return (value + (" " * max(0, width - len(value))))[:width]


def _pad_left(value, width):
    value = str(value or "")
    width = max(0, int(width or 0))
    return ((" " * max(0, width - len(value))) + value)[-width:] if width else ""


def _clip(value, width):
    value = str(value or "")
    return _pad_right(value, width)


def service_status_text(service):
    """Return the normalized status text shown at the right of a rail row."""
    return "CANCELLED" if service.get("cancelled") else str(service.get("status", ""))


def rail_row_parts(service):
    """Return the left rail content and independently rendered status text."""
    time = _clip(service.get("time", "--:--"), 5)
    destination = str(service.get("destination") or "Unknown")
    platform = ("P" + str(service.get("platform", "-")))[:3]
    return "{} {} {}".format(time, destination, platform), service_status_text(service)


def format_row(service, width=32):
    # Keep platform and status intact, using all remaining room for a station.
    time = _clip(service.get("time", "--:--"), 5)
    platform = ("P" + str(service.get("platform", "-")))[:3]
    status = service_status_text(service)
    prefix = time + " "
    suffix = " " + platform + " " + status
    destination = _clip(service.get("destination", "Unknown"), max(1, width - len(prefix) - len(suffix)))
    return _pad_right(prefix + destination + suffix, width)


def calendar_row_parts(event):
    """Return the fixed date/time prefix and independently scrollable title."""
    date_text = str(event.get("date_text") or "").strip()
    time_text = str(event.get("time_text") or "").strip()
    if event.get("all_day") or time_text.upper() == "ALL":
        time_text = ""
    if not date_text:
        start = str(event.get("start") or "")
        if "T" in start:
            date_text = start[:10]
            time_text = time_text or start.split("T", 1)[1][:5]
        else:
            date_text = start[:10]
    when = (date_text + (" " + time_text if time_text else "")).strip()
    title = str(event.get("title") or event.get("location") or "Event")
    return _pad_right(when, AGENDA_WHEN_WIDTH), title


def calendar_row_text(event):
    """Format one normalized agenda event without clipping its title."""
    when, title = calendar_row_parts(event)
    return when + " " + title


def calendar_row(event, width=AGENDA_ROW_WIDTH):
    """Format one normalized agenda event to a fixed-width static row."""
    return _pad_right(calendar_row_text(event), width)


def agenda_marquee_x(
    text,
    phase,
    visible_chars=AGENDA_ROW_WIDTH,
    font_width=AGENDA_FONT_WIDTH,
    speed=AGENDA_MARQUEE_SPEED,
    pause_seconds=AGENDA_MARQUEE_PAUSE_SECONDS,
):
    """Return the x offset for a long agenda row marquee.

    Rows at or below ``visible_chars`` remain fixed at x=0. Longer rows move
    right-to-left until their final character is visible, pause there, then
    jump back to x=0 and repeat.
    """
    text = str(text or "")
    if len(text) <= visible_chars:
        return 0
    try:
        phase = max(0.0, float(phase or 0))
        speed = max(1.0, float(speed or AGENDA_MARQUEE_SPEED))
        pause_seconds = max(0.0, float(pause_seconds or 0))
    except (TypeError, ValueError):
        phase = 0.0
        speed = AGENDA_MARQUEE_SPEED
        pause_seconds = AGENDA_MARQUEE_PAUSE_SECONDS
    overflow = max(0, (len(text) - int(visible_chars)) * int(font_width))
    if overflow <= 0:
        return 0
    scroll_seconds = overflow / speed
    cycle_seconds = scroll_seconds + pause_seconds
    within_cycle = phase % cycle_seconds if cycle_seconds > 0 else 0
    if within_cycle >= scroll_seconds:
        return -overflow
    return -min(overflow, int(within_cycle * speed))


def agenda_title_marquee_x(title, phase):
    """Return the title x position while keeping the agenda date/time fixed."""
    return AGENDA_TITLE_X + agenda_marquee_x(
        title,
        phase,
        visible_chars=AGENDA_TITLE_VISIBLE_CHARS,
    )


def calling_marquee_x(
    text,
    phase,
    display_width=256,
    font_width=6,
    speed=RAIL_MARQUEE_SPEED,
    delay_seconds=RAIL_MARQUEE_DELAY_SECONDS,
    gap=RAIL_MARQUEE_GAP,
    pause_seconds=CALLING_MARQUEE_PAUSE_SECONDS,
):
    """Return the station-text x position while keeping ``CALLING AT:`` fixed.

    ``None`` means the calling row must remain hidden. Once visible, the fixed
    label stays at x=0 while long station text scrolls in the remaining space.
    Each loop pauses with the first station beside the label.
    """
    try:
        phase = max(0.0, float(phase or 0))
        delay_seconds = max(0.0, float(delay_seconds or 0))
        speed = max(1.0, float(speed or RAIL_MARQUEE_SPEED))
        pause_seconds = max(0.0, float(pause_seconds or 0))
    except (TypeError, ValueError):
        phase = 0.0
        delay_seconds = RAIL_MARQUEE_DELAY_SECONDS
        speed = RAIL_MARQUEE_SPEED
        pause_seconds = CALLING_MARQUEE_PAUSE_SECONDS
    if phase < delay_seconds:
        return None
    text = str(text or "")
    prefix_width = len(CALLING_LABEL) * int(font_width)
    stations = text[len(CALLING_LABEL):] if text.startswith(CALLING_LABEL) else text
    visible_width = max(1, int(display_width) - prefix_width)
    text_width = len(stations) * int(font_width)
    if text_width <= visible_width:
        return prefix_width
    elapsed = phase - delay_seconds
    moving_elapsed = max(0.0, elapsed - pause_seconds)
    cycle_width = text_width + max(0, int(gap or 0))
    return prefix_width - int((moving_elapsed * speed) % cycle_width)


def _iso_date_parts(value):
    text = str(value or "")
    if len(text) < 10:
        return None
    try:
        year = int(text[0:4])
        month = int(text[5:7])
        day = int(text[8:10])
    except (TypeError, ValueError):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return year, month, day


def _date_ordinal(year, month, day):
    """Return a Gregorian day ordinal using only integer arithmetic."""
    previous_year = year - 1
    days = 365 * previous_year + previous_year // 4 - previous_year // 100 + previous_year // 400
    month_lengths = (31, 28 + (1 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 0), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    days += sum(month_lengths[:month - 1])
    return days + day


def _time_minutes(value):
    text = str(value or "")
    if len(text) < 5:
        return None
    try:
        hour = int(text[0:2])
        minute = int(text[3:5])
    except (TypeError, ValueError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute


def calendar_due_text(event, current_date, current_time):
    """Return a compact countdown for the next agenda event.

    ``current_date`` is ``YYYY-MM-DD`` in the board display timezone and
    ``current_time`` is ``HH:MM``. Future-day events deliberately use calendar
    day difference rather than a rolling 24-hour duration.
    """
    if not isinstance(event, dict):
        return ""
    event_date = _iso_date_parts(event.get("start"))
    now_date = _iso_date_parts(current_date)
    if event_date is None or now_date is None:
        return ""

    day_delta = _date_ordinal(*event_date) - _date_ordinal(*now_date)
    if day_delta < 0:
        return ""
    if day_delta > 0:
        return "DUE IN {}d".format(day_delta)
    if event.get("all_day"):
        return "DUE TODAY"

    event_minutes = _time_minutes(event.get("time_text"))
    if event_minutes is None:
        start = str(event.get("start") or "")
        event_minutes = _time_minutes(start[11:16] if "T" in start else "")
    now_minutes = _time_minutes(current_time)
    if event_minutes is None or now_minutes is None:
        return ""

    remaining = event_minutes - now_minutes
    if remaining <= 0:
        return "DUE NOW"
    hours, minutes = divmod(remaining, 60)
    if hours and minutes:
        return "DUE IN {}h {}m".format(hours, minutes)
    if hours:
        return "DUE IN {}h".format(hours)
    return "DUE IN {}m".format(minutes)


def todoist_due_label(event, current_date):
    """Return Todoist's day-only due label for a task row."""
    if not isinstance(event, dict):
        return ""
    event_date = _iso_date_parts(event.get("start"))
    now_date = _iso_date_parts(current_date)
    if event_date is None or now_date is None:
        return ""
    day_delta = _date_ordinal(*event_date) - _date_ordinal(*now_date)
    if day_delta < 0:
        return "OVERDUE"
    if day_delta == 0:
        return "TODAY"
    return "DUE {} DAY{}".format(day_delta, "" if day_delta == 1 else "S")


def todoist_page_timing(events, page_seconds=AGENDA_PAGE_SECONDS, visible_rows=AGENDA_VISIBLE_ROWS,
                        current_date="", marquee_speed=AGENDA_MARQUEE_SPEED,
                        settle_pause_seconds=AGENDA_MARQUEE_PAUSE_SECONDS):
    """Return the minimum readable timeline for a Todoist screen.

    Each page gets its own title-scroll time followed by the configured
    settled/readable dwell.  Due labels are included in the available title
    width so an overdue label cannot be hidden by a long title.
    """
    events = list(events or [])
    visible_rows = max(1, int(visible_rows or AGENDA_VISIBLE_ROWS))
    page_seconds = max(0.0, float(page_seconds or 0))
    marquee_speed = max(1.0, float(marquee_speed or AGENDA_MARQUEE_SPEED))
    settle_pause_seconds = max(0.0, float(settle_pause_seconds or 0))
    page_durations = []
    for start in range(0, len(events), visible_rows):
        longest_scroll = 0.0
        for event in events[start:start + visible_rows]:
            _when, title = calendar_row_parts(event)
            due = todoist_due_label(event, current_date)
            due_width = len(due) * AGENDA_FONT_WIDTH if due else 0
            available_width = max(
                AGENDA_FONT_WIDTH,
                256 - AGENDA_TITLE_X - 4 - due_width,
            )
            overflow = max(0, len(title) * AGENDA_FONT_WIDTH - available_width)
            longest_scroll = max(longest_scroll, overflow / marquee_speed)
        page_durations.append(
            longest_scroll + (settle_pause_seconds if longest_scroll else 0.0) + page_seconds
        )
    if not page_durations:
        return 0.0
    return sum(page_durations) + max(0, len(page_durations) - 1) * AGENDA_SLIDE_SECONDS


def todoist_effective_duration(screen_duration, events, page_seconds=AGENDA_PAGE_SECONDS,
                               visible_rows=AGENDA_VISIBLE_ROWS, current_date=""):
    """Extend, never shorten, the server-configured Todoist screen duration."""
    configured = max(1.0, float(screen_duration or 1))
    required = todoist_page_timing(
        events,
        page_seconds=page_seconds,
        visible_rows=visible_rows,
        current_date=current_date,
    )
    return int(max(configured, required) + 0.999999)


def header(station, stale=False):
    suffix = "  STALE" if stale else ""
    return ("NEW DEPARTURES" + suffix)[:42]


def row_slide_phase(phase, index, stagger=1.0):
    """Return the 0..1 slide progress for one staggered departure row."""
    return max(0.0, min(1.0, (phase - index * stagger) / 1.2))


def departure_scroll_state(phase, service_count, pause_seconds=2, visible_rows=2):
    """Return (window start, upward progress, left-entry reset progress).

    ``reset_progress`` is ``None`` during the intentional blank gap before the
    first two upcoming rows re-enter from the left.
    """
    service_count = max(0, int(service_count or 0))
    visible_rows = max(1, int(visible_rows or 1))
    max_start = max(0, service_count - visible_rows)
    if max_start == 0:
        return 0, 0.0, 0.0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0
    try:
        pause_seconds = max(0.0, float(pause_seconds or 0))
    except (TypeError, ValueError):
        pause_seconds = 2.0
    slide_seconds = 0.4
    reset_gap_seconds = 0.4
    reset_slide_seconds = 0.8
    step_seconds = pause_seconds + slide_seconds
    normal_duration = (max_start + 1) * step_seconds
    cycle_duration = normal_duration + reset_gap_seconds + reset_slide_seconds
    phase %= cycle_duration
    if phase >= normal_duration - 1e-9:
        reset_elapsed = max(0.0, phase - normal_duration)
        if reset_elapsed < reset_gap_seconds:
            return 0, 0.0, None
        reset_progress = min(1.0, (reset_elapsed - reset_gap_seconds) / reset_slide_seconds)
        return 0, 0.0, 0.0 if reset_progress < 1e-9 else reset_progress
    step = min(max_start, int(phase // step_seconds))
    within = phase - step * step_seconds
    if within <= pause_seconds:
        return step, 0.0, 0.0
    return step, min(1.0, (within - pause_seconds) / slide_seconds), 0.0


def ordinal_label(number):
    """Return a compact ordinal label for a departure row."""
    number = int(number)
    if 10 < number % 100 < 14:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return "{}{}".format(number, suffix)


def queue_scroll_state(phase, ride_count, visible_rows=QUEUE_VISIBLE_ROWS):
    """Return the first visible ride and 0..1 upward slide progress.

    Queue rows hold still for readability, then move up together by one row.
    Once the final configured rides are visible the viewport stays there until
    the screen rotates away instead of wrapping mid-screen.
    """
    ride_count = max(0, int(ride_count or 0))
    visible_rows = max(1, int(visible_rows or 1))
    max_start = max(0, ride_count - visible_rows)
    if max_start == 0:
        return 0, 0.0

    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0

    step = int(phase // QUEUE_STEP_SECONDS)
    if step >= max_start:
        return max_start, 0.0

    within_step = phase - step * QUEUE_STEP_SECONDS
    if within_step <= QUEUE_HOLD_SECONDS:
        progress = 0.0
    else:
        progress = min(1.0, (within_step - QUEUE_HOLD_SECONDS) / QUEUE_SLIDE_SECONDS)
    return step, progress


def agenda_scroll_state(
    phase,
    event_count,
    page_seconds=AGENDA_PAGE_SECONDS,
    visible_rows=AGENDA_VISIBLE_ROWS,
):
    """Return page start and 0..1 progress for a two-page agenda.

    Up to three events remain static. Four to six events show the first three
    until ``page_seconds`` and then slide the full viewport upward once so the
    remaining events settle in the same three display rows.
    """
    event_count = max(0, int(event_count or 0))
    visible_rows = max(1, int(visible_rows or 1))
    if event_count <= visible_rows:
        return 0, 0.0
    try:
        phase = max(0.0, float(phase or 0))
        page_seconds = max(0.0, float(page_seconds or AGENDA_PAGE_SECONDS))
    except (TypeError, ValueError):
        phase = 0.0
        page_seconds = AGENDA_PAGE_SECONDS
    if phase <= page_seconds:
        return 0, 0.0
    progress = min(1.0, (phase - page_seconds) / AGENDA_SLIDE_SECONDS)
    if progress >= 1.0:
        return visible_rows, 0.0
    return 0, progress


def _station_separator(service):
    """Return blank padding between calling-point entries from logical pixels."""
    try:
        spacing = float(service.get("station_spacing_px", DEFAULT_STATION_LIST_SPACING))
    except (TypeError, ValueError, AttributeError):
        spacing = DEFAULT_STATION_LIST_SPACING
    spaces = max(1, int(round(max(0.0, spacing) / CALLING_STATION_FONT_WIDTH)))
    return " " * spaces


def calling_text(service):
    """Format calling stations and times for the scrolling second line."""
    stops = service.get("stops") or []
    if not stops:
        return "CALLING AT: {} only".format(service.get("destination", "destination"))
    parts = []
    for stop in stops:
        value = "{} {}".format(stop.get("station", "Unknown"), stop.get("time", "--:--"))
        if stop.get("cancelled"):
            value += " CANCELLED"
        elif stop.get("status") not in (None, "", "On time"):
            value += " ({})".format(stop.get("status"))
        parts.append(value)
    return "CALLING AT: " + _station_separator(service).join(parts)


def rail_phase(phase, summary_seconds=RAIL_SUMMARY_SECONDS, calling_seconds=RAIL_CALLING_SECONDS):
    """Return the departures presentation state for the supplied phase."""
    try:
        total = max(0.1, float(summary_seconds)) + max(0.1, float(calling_seconds))
        value = max(0.0, float(phase or 0)) % total
    except (TypeError, ValueError):
        value = 0.0
        summary_seconds = RAIL_SUMMARY_SECONDS
    return "summary" if value < max(0.1, float(summary_seconds)) else "calling"


def rail_phase_elapsed(phase, summary_seconds=RAIL_SUMMARY_SECONDS, calling_seconds=RAIL_CALLING_SECONDS):
    """Return phase-local elapsed seconds, resetting at the calling state."""
    summary_seconds = max(0.1, float(summary_seconds))
    total = summary_seconds + max(0.1, float(calling_seconds))
    value = max(0.0, float(phase or 0)) % total
    return value if value < summary_seconds else value - summary_seconds


def rail_rows(services, phase):
    """Return four logical departures rows shared by hardware and fixtures."""
    services = list(services or [])
    state = rail_phase(phase)
    if state == "summary":
        return [
            ("header", None),
            ("service", services[1] if len(services) > 1 else None),
            ("service", services[2] if len(services) > 2 else None),
            ("service", services[3] if len(services) > 3 else None),
        ]
    return [
        ("service", services[0] if len(services) > 0 else None),
        ("calling", services[0] if len(services) > 0 else None),
        ("service", services[1] if len(services) > 1 else None),
        ("calling", services[1] if len(services) > 1 else None),
    ]
