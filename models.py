"""Small, CircuitPython-friendly data model shared by providers and renderers."""


def service_from_api(item):
    """Normalize one LDBWS JSON ServiceItem into the fields we display."""
    destinations = item.get("destination") or item.get("currentDestinations") or []
    destination = ""
    if destinations:
        destination = destinations[0].get("locationName", "")
    expected = item.get("etd") or item.get("eta") or item.get("std") or ""
    return {
        "time": item.get("std") or item.get("sta") or "--:--",
        "destination": destination or "Unknown",
        "platform": item.get("platform") or "-",
        "status": expected,
        "cancelled": bool(item.get("isCancelled")),
        "delay_reason": item.get("delayReason") or "",
    }


def services_from_board(board):
    return [service_from_api(item) for item in (board.get("trainServices") or [])]

