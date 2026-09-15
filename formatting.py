"""Fixed-width board formatting, independent of display hardware."""


QUEUE_VISIBLE_ROWS = 3
QUEUE_HOLD_SECONDS = 1.0
QUEUE_SLIDE_SECONDS = 0.3
QUEUE_STEP_SECONDS = QUEUE_HOLD_SECONDS + QUEUE_SLIDE_SECONDS
RAIL_MARQUEE_SPEED = 48.0
RAIL_MARQUEE_DELAY_SECONDS = 1.2
RAIL_MARQUEE_GAP = 56
AGENDA_VISIBLE_ROWS = 3
AGENDA_SLIDE_SECONDS = 0.4
AGENDA_PAGE_SECONDS = 5.0
AGENDA_ROW_WIDTH = 42
AGENDA_FONT_WIDTH = 6
AGENDA_WHEN_WIDTH = 11
AGENDA_TITLE_GAP = 1
AGENDA_TITLE_X = (AGENDA_WHEN_WIDTH + AGENDA_TITLE_GAP) * AGENDA_FONT_WIDTH
AGENDA_TITLE_VISIBLE_CHARS = AGENDA_ROW_WIDTH - AGENDA_WHEN_WIDTH - AGENDA_TITLE_GAP
AGENDA_MARQUEE_SPEED = 30.0
AGENDA_MARQUEE_PAUSE_SECONDS = 1.25


def _clip(value, width):
    value = str(value or "")
    return value[:width].ljust(width)


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
    return (prefix + destination + suffix)[:width].ljust(width)


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
    return when[:AGENDA_WHEN_WIDTH].ljust(AGENDA_WHEN_WIDTH), title


def calendar_row_text(event):
    """Format one normalized agenda event without clipping its title."""
    when, title = calendar_row_parts(event)
    return when + " " + title


def calendar_row(event, width=AGENDA_ROW_WIDTH):
    """Format one normalized agenda event to a fixed-width static row."""
    return calendar_row_text(event)[:width].ljust(width)


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
):
    """Return the calling-points marquee x position after the primary row lands.

    ``None`` means the calling row must remain hidden. Once visible, long text
    scrolls right-to-left at the configured speed and short text stays fixed.
    """
    try:
        phase = max(0.0, float(phase or 0))
        delay_seconds = max(0.0, float(delay_seconds or 0))
        speed = max(1.0, float(speed or RAIL_MARQUEE_SPEED))
    except (TypeError, ValueError):
        phase = 0.0
        delay_seconds = RAIL_MARQUEE_DELAY_SECONDS
        speed = RAIL_MARQUEE_SPEED
    if phase < delay_seconds:
        return None
    text_width = len(str(text or "")) * int(font_width)
    if text_width <= int(display_width):
        return 0
    elapsed = phase - delay_seconds
    cycle_width = text_width + max(0, int(gap or 0))
    return -int((elapsed * speed) % cycle_width)


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
        return ""
    if day_delta == 0:
        return "DUE IN TODAY"
    return "DUE IN {} DAY{}".format(day_delta, "" if day_delta == 1 else "S")


def header(station, stale=False):
    suffix = "  STALE" if stale else ""
    return ("NEW DEPARTURES" + suffix)[:42]


def row_slide_phase(phase, index, stagger=1.0):
    """Return the 0..1 slide progress for one staggered departure row."""
    return max(0.0, min(1.0, (phase - index * stagger) / 1.2))


def departure_scroll_state(phase, service_count, pause_seconds=2, visible_rows=2):
    """Return the current upcoming-service window and upward slide progress."""
    service_count = max(0, int(service_count or 0))
    visible_rows = max(1, int(visible_rows or 1))
    max_start = max(0, service_count - visible_rows)
    if max_start == 0:
        return 0, 0.0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0
    try:
        pause_seconds = max(0.0, float(pause_seconds or 0))
    except (TypeError, ValueError):
        pause_seconds = 2.0
    slide_seconds = 0.4
    step_seconds = pause_seconds + slide_seconds
    step = min(max_start, int(phase // step_seconds))
    if step >= max_start:
        return max_start, 0.0
    within = phase - step * step_seconds
    if within <= pause_seconds:
        return step, 0.0
    return step, min(1.0, (within - pause_seconds) / slide_seconds)


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
    return "CALLING AT: " + "  -  ".join(parts)
