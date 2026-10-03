"""Pure deadline helpers for application-owned Matrix animation pacing."""


def next_deadline(previous_deadline, now, cadence, cadence_changed=False):
    """Return (deadline, remaining, late, rebased) for one current-state tick.

    A cadence change starts from the current post-render time, so an old
    cadence cannot leave a stale deadline active. A delay longer than one
    frame rebases instead of replaying missed animation positions.
    """
    frame_seconds = 1.0 / max(1.0, float(cadence))
    rebased = cadence_changed or previous_deadline is None
    deadline = now if rebased else previous_deadline
    deadline += frame_seconds
    remaining = deadline - now
    late = remaining <= 0
    if late and -remaining > frame_seconds:
        deadline = now
        rebased = True
    return deadline, remaining, late, rebased


def earliest_wake_seconds(until_rotation, until_fetch, boundary_sleep, fallback=1.0):
    """Choose the earliest positive rotation, fetch, or animation boundary."""
    values = []
    for value in (until_rotation, until_fetch, boundary_sleep):
        if value is not None:
            values.append(max(0.05, float(value)))
    return min(values) if values else max(0.05, float(fallback))


def screen_fetch_decision(
    now,
    next_fetch,
    animation_active,
    safe_window=None,
    retry_seconds=0.5,
    min_window_seconds=3.0,
):
    """Avoid starting a blocking fetch during motion or just before it resumes."""
    if now < next_fetch:
        return False, next_fetch
    if animation_active or (
        safe_window is not None and safe_window < min_window_seconds
    ):
        return False, now + max(0.05, float(retry_seconds))
    return True, next_fetch
