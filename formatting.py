"""Fixed-width board formatting, independent of display hardware."""


def _clip(value, width):
    value = str(value or "")
    return value[:width].ljust(width)


def format_row(service, width=32):
    # Fits a 256px board with the standard 6px terminal font.
    destination = _clip(service.get("destination", "Unknown"), 12)
    time = _clip(service.get("time", "--:--"), 5)
    platform = _clip("P" + str(service.get("platform", "-")), 3)
    status = "CANCELLED" if service.get("cancelled") else str(service.get("status", ""))
    return (time + " " + destination + " " + platform + " " + status)[:width].ljust(width)


def header(station, stale=False):
    suffix = "  STALE" if stale else ""
    return ("NEW DEPARTURES" + suffix)[:42]


def row_slide_phase(phase, index, stagger=1.0):
    """Return the 0..1 slide progress for one staggered departure row."""
    return max(0.0, min(1.0, (phase - index * stagger) / 1.2))
