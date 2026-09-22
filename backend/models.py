"""Small, CircuitPython-friendly data model shared by providers and renderers."""


def calling_points_from_api(item):
    groups = item.get("subsequentCallingPoints") or []
    if isinstance(groups, dict):
        groups = groups.get("callingPointList") or [groups]
    if isinstance(groups, dict):
        groups = [groups]
    stops = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        points = group.get("callingPoint") or group.get("callingPoints") or []
        if isinstance(points, dict):
            points = [points]
        for point in points:
            if not isinstance(point, dict):
                continue
            scheduled = point.get("st") or point.get("sta") or "--:--"
            expected = point.get("et") or point.get("at") or scheduled
            cancelled = bool(point.get("isCancelled")) or str(expected).lower() == "cancelled"
            status = "Cancelled" if cancelled else ("On time" if str(expected).lower() == "on time" or expected == scheduled else expected)
            stops.append({
                "station": point.get("locationName") or "Unknown",
                "crs": point.get("crs") or "",
                "time": scheduled,
                "status": status,
                "cancelled": cancelled,
            })
    return stops


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
        "stops": calling_points_from_api(item),
    }


def services_from_board(board):
    return [service_from_api(item) for item in (board.get("trainServices") or [])]
