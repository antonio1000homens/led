"""Integer timing for animation and measurements after long board uptime."""

import time


def ticks_ms():
    # Do not convert the absolute uptime to float: CircuitPython loses enough
    # precision after several days to repeat/jump entire animation frames.
    return time.monotonic_ns() // 1_000_000


def elapsed_seconds(start_ms, end_ms=None):
    if end_ms is None:
        end_ms = ticks_ms()
    return (end_ms - start_ms) / 1000.0
