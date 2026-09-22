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
