"""Fixed-width board formatting, independent of display hardware."""


QUEUE_VISIBLE_ROWS = 3
QUEUE_HOLD_SECONDS = 1.0
QUEUE_SLIDE_SECONDS = 0.3
QUEUE_STEP_SECONDS = QUEUE_HOLD_SECONDS + QUEUE_SLIDE_SECONDS
AGENDA_VISIBLE_ROWS = 3
AGENDA_SLIDE_SECONDS = 0.4
AGENDA_PAGE_SECONDS = 5.0


def _clip(value, width):
    value = str(value or "")
    return value[:width].ljust(width)


def format_row(service, width=32):
    # Keep platform and status intact, using all remaining room for a station.
    time = _clip(service.get("time", "--:--"), 5)
    platform = ("P" + str(service.get("platform", "-")))[:3]
    status = "CANCELLED" if service.get("cancelled") else str(service.get("status", ""))
    prefix = time + " "
    suffix = " " + platform + " " + status
    destination = _clip(service.get("destination", "Unknown"), max(1, width - len(prefix) - len(suffix)))
    return (prefix + destination + suffix)[:width].ljust(width)


def calendar_row(event, width=32):
    """Format one normalized agenda event as date/time then title."""
    date_text = str(event.get("date_text") or "").strip()
    time_text = str(event.get("time_text") or "").strip()
    if not date_text:
        start = str(event.get("start") or "")
        if "T" in start:
            date_text = start[:10]
            time_text = time_text or start.split("T", 1)[1][:5]
        else:
            date_text = start[:10]
    when = (date_text + (" " + time_text if time_text else "")).strip()
    title = str(event.get("title") or event.get("location") or "Event")
    prefix = when[:11].ljust(11) + " "
    return (prefix + title)[:width].ljust(width)


def header(station, stale=False):
    suffix = "  STALE" if stale else ""
    return ("NEW DEPARTURES" + suffix)[:42]


def row_slide_phase(phase, index, stagger=1.0):
    """Return the 0..1 slide progress for one staggered departure row."""
    return max(0.0, min(1.0, (phase - index * stagger) / 1.2))


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
