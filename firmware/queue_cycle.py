"""Queue-Times page cycling and transition timing shared by display backends.

This module deliberately uses only CircuitPython-compatible language features so
the same timing rules can run on the MatrixPortal and under CPython tests.
"""

QUEUE_VISIBLE_ROWS = 3
QUEUE_ROW_HEIGHT = 8
DEFAULT_QUEUE_SCROLL_SPEED = 27.0
DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS = 1.0
QUEUE_PARK_FLASH_SECONDS = 0.35
QUEUE_SPLASH_SLIDE_IN_SECONDS = 0.55
QUEUE_SPLASH_FLASH_SECONDS = 0.35
QUEUE_SPLASH_SLIDE_UP_SECONDS = 0.55


def _positive_number(value, default):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = float(default)
    return number if number > 0 else float(default)


def queue_slide_seconds(scroll_speed, row_height=QUEUE_ROW_HEIGHT):
    """Return seconds required to move one queue row at the configured speed."""
    speed = _positive_number(scroll_speed, DEFAULT_QUEUE_SCROLL_SPEED)
    return max(0.08, float(row_height) / speed)


def queue_scroll_state(
    phase,
    ride_count,
    pause_seconds=DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS,
    scroll_speed=DEFAULT_QUEUE_SCROLL_SPEED,
    visible_rows=QUEUE_VISIBLE_ROWS,
    row_height=QUEUE_ROW_HEIGHT,
):
    """Return the first visible ride and 0..1 upward slide progress.

    Rows pause for ``pause_seconds`` and then move upward at the configured pixel
    speed.  The final viewport remains settled; park switching is handled by
    ``queue_cycle_state``.
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
    pause = _positive_number(pause_seconds, DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS)
    slide = queue_slide_seconds(scroll_speed, row_height)
    step_seconds = pause + slide
    step = int(phase // step_seconds)
    if step >= max_start:
        return max_start, 0.0

    within = phase - step * step_seconds
    if within <= pause:
        return step, 0.0
    return step, min(1.0, (within - pause) / slide)


def queue_park_data_seconds(
    ride_count,
    pause_seconds=DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS,
    scroll_speed=DEFAULT_QUEUE_SCROLL_SPEED,
    visible_rows=QUEUE_VISIBLE_ROWS,
    row_height=QUEUE_ROW_HEIGHT,
):
    """Return how long one park needs to show every configured queue once."""
    ride_count = max(0, int(ride_count or 0))
    visible_rows = max(1, int(visible_rows or 1))
    pause = _positive_number(pause_seconds, DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS)
    max_start = max(0, ride_count - visible_rows)
    if max_start == 0:
        return pause
    slide = queue_slide_seconds(scroll_speed, row_height)
    return pause + max_start * (slide + pause)


def queue_transition_seconds(splash_enabled):
    if splash_enabled:
        return (
            QUEUE_SPLASH_SLIDE_IN_SECONDS
            + QUEUE_SPLASH_FLASH_SECONDS
            + QUEUE_SPLASH_SLIDE_UP_SECONDS
        )
    return QUEUE_PARK_FLASH_SECONDS


def queue_cycle_state(
    phase,
    ride_counts,
    pause_seconds=DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS,
    scroll_speed=DEFAULT_QUEUE_SCROLL_SPEED,
    splash_enabled=False,
):
    """Return ``(park_index, data_phase, mode, transition_progress)``.

    ``mode`` is one of ``flash``, ``splash_in``, ``splash_flash``,
    ``splash_up`` or ``data``.  The park changes only after its final queue
    viewport has paused, then the cycle repeats from the first park.
    """
    counts = [max(0, int(value or 0)) for value in (ride_counts or [])]
    if not counts:
        return 0, 0.0, "data", 1.0
    try:
        phase = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        phase = 0.0

    transition = queue_transition_seconds(bool(splash_enabled))
    durations = [
        transition + queue_park_data_seconds(count, pause_seconds, scroll_speed)
        for count in counts
    ]
    total = sum(durations)
    if total <= 0:
        return 0, 0.0, "data", 1.0
    within_cycle = phase % total

    park_index = 0
    local = within_cycle
    for index, duration in enumerate(durations):
        park_index = index
        if local < duration or index == len(durations) - 1:
            break
        local -= duration

    if splash_enabled:
        if local < QUEUE_SPLASH_SLIDE_IN_SECONDS:
            return park_index, 0.0, "splash_in", local / QUEUE_SPLASH_SLIDE_IN_SECONDS
        local -= QUEUE_SPLASH_SLIDE_IN_SECONDS
        if local < QUEUE_SPLASH_FLASH_SECONDS:
            return park_index, 0.0, "splash_flash", local / QUEUE_SPLASH_FLASH_SECONDS
        local -= QUEUE_SPLASH_FLASH_SECONDS
        if local < QUEUE_SPLASH_SLIDE_UP_SECONDS:
            return park_index, 0.0, "splash_up", local / QUEUE_SPLASH_SLIDE_UP_SECONDS
        local -= QUEUE_SPLASH_SLIDE_UP_SECONDS
        return park_index, max(0.0, local), "data", 1.0

    if local < QUEUE_PARK_FLASH_SECONDS:
        return park_index, 0.0, "flash", local / QUEUE_PARK_FLASH_SECONDS
    return park_index, max(0.0, local - QUEUE_PARK_FLASH_SECONDS), "data", 1.0
