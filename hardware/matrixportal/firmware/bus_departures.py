"""Bounded SL7 departure normalisation shared by firmware and tests."""

ROUTE = "SL7"
STOP_KEYS = ("heathrow", "new-malden")
MAX_DEPARTURES = 10
MAX_TEXT = 64


def _epoch(value):
    # Lazy import avoids a cycle: mqtt_screens uses this module for validation.
    from mqtt_screens import _epoch as parse_epoch
    return parse_epoch(value)


def _text(value, maximum=MAX_TEXT):
    return value.strip()[:maximum] if isinstance(value, str) else ""


def _valid_bool(value):
    return isinstance(value, bool)


def _effective(item):
    value = item.get("estimated") or item.get("planned")
    try:
        return _epoch(value)
    except (TypeError, ValueError):
        return None


def valid_bus_screen(screen, slot):
    if not isinstance(screen, dict):
        return False
    if screen.get("id") != slot or screen.get("kind") != "bus_departures":
        return False
    if screen.get("route") != ROUTE or screen.get("stop_key") not in STOP_KEYS:
        return False
    if not _text(screen.get("title")) or not _text(screen.get("stop_name")):
        return False
    duration = screen.get("duration_seconds")
    if (not isinstance(screen.get("observed_at"), str)
            or isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not 2 <= float(duration) <= 300
            or screen.get("status", "ok") not in ("ok", "empty", "unavailable")):
        return False
    if not isinstance(screen.get("departures"), list) or len(screen["departures"]) > MAX_DEPARTURES:
        return False
    try:
        _epoch(screen["observed_at"])
    except (TypeError, ValueError):
        return False
    for item in screen["departures"]:
        if not isinstance(item, dict) or not _text(item.get("destination")):
            return False
        if not isinstance(item.get("planned"), str):
            return False
        try:
            _epoch(item["planned"])
            if item.get("estimated") is not None:
                _epoch(item["estimated"])
        except (TypeError, ValueError):
            return False
        if item.get("trip_id") is not None and not _text(item.get("trip_id"), 96):
            return False
        if not _valid_bool(item.get("cancelled", False)) or not _valid_bool(item.get("alerts", False)):
            return False
    return True


def normalise_bus_screen(screen, now_epoch, *, count=3, tolerance_seconds=60):
    """Filter, deduplicate and order a validated screen for local rendering."""
    if not valid_bus_screen(screen, screen.get("id") if isinstance(screen, dict) else None):
        return None
    result = dict(screen)
    selected = []
    seen = set()
    cutoff = int(now_epoch) - int(tolerance_seconds)
    for item in screen.get("departures") or []:
        when = _effective(item)
        if when is None or when < cutoff * 1000:
            continue
        trip_id = item.get("trip_id")
        if trip_id and trip_id in seen:
            continue
        if trip_id:
            seen.add(trip_id)
        selected.append((when, dict(item)))
    selected.sort(key=lambda pair: pair[0])
    result["departures"] = [
        item for _, item in selected[:max(1, min(MAX_DEPARTURES, int(count or 3)))]
    ]
    result["empty_state"] = not result["departures"]
    return result
