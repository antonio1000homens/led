"""Temporary full-colour display diagnostics for flash correlation."""

from monotonic_clock import ticks_ms
from matrix_config import MATRIX_DIAGNOSTIC_COLOR_COUNTER


current_count = None


def colour_at(index):
    """Return one of eight darker RGB combinations, using all three channels."""
    value = int(index) % 8
    red = 0x55 if value & 4 else 0
    green = 0x55 if value & 2 else 0
    blue = 0x55 if value & 1 else 0
    return (red << 16) | (green << 8) | blue


def set_frame(count, colour_index, colour):
    global current_count
    current_count = int(count)
    if MATRIX_DIAGNOSTIC_COLOR_COUNTER:
        print(
            "DIAG FRAME count={} colour_index={} rgb={:06X} uptime_ms={}".format(
                current_count, int(colour_index), int(colour), ticks_ms()
            )
        )


def event(category, phase, detail=""):
    if not MATRIX_DIAGNOSTIC_COLOR_COUNTER:
        return
    print(
        "DIAG EVENT category={} phase={} count={} uptime_ms={} detail={}".format(
            category, phase, current_count, ticks_ms(), detail
        )
    )


def collect(gc_module, detail="explicit"):
    collector = getattr(gc_module, "collect", None)
    if collector is None:
        return None
    started = ticks_ms()
    try:
        return collector()
    finally:
        event("GC", "DONE", "{} duration_ms={}".format(detail, ticks_ms() - started))
