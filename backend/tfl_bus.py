"""Anonymous TfL Unified API live-arrival provider for the SL7 screens."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.parse import quote
from urllib.request import Request, urlopen

TFL_API = "https://api.tfl.gov.uk"
TFL_USER_AGENT = "led-sl7-bus/1.0 (https://github.com/antonio1000homens/led)"
ROUTE = "SL7"
DEFAULT_STOPS = {
    # NaPTAN StopPoint IDs, as used by the TfL StopPoint arrivals endpoint.
    "heathrow": {"name": "Heathrow", "stop_id": "4900801619"},
    "new-malden": {"name": "New Malden", "stop_id": "490015206J"},
}


def _iso(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class TflBusProvider:
    """Fetch TfL's live predicted arrival times without API credentials."""

    def __init__(self, stops=None, base_url=TFL_API, timeout=15, opener=None):
        self.stops = dict(stops or DEFAULT_STOPS)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = opener or urlopen

    def _fetch(self, stop_id):
        request = Request(
            f"{self.base_url}/StopPoint/{quote(str(stop_id), safe='')}/Arrivals",
            headers={"Accept": "application/json", "User-Agent": TFL_USER_AGENT},
        )
        with self.opener(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalise(item):
        # TfL's expectedArrival is the real-time countdown prediction. Never
        # substitute a timetable departure here; no live prediction means the
        # row is not eligible for the TfL screen.
        expected = _iso(item.get("expectedArrival"))
        if not expected:
            return None
        return {
            "planned": expected,
            "estimated": expected,
            "trip_id": item.get("tripId") or item.get("id"),
            "destination": (item.get("destinationName") or item.get("towards") or "SL7").strip(),
            "cancelled": False,
            "alerts": False,
            "time_basis": "live_prediction",
            "time_to_station_seconds": item.get("timeToStation"),
        }

    def fetch(self, now=None):
        observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        result = {}
        for key, definition in self.stops.items():
            rows = self._fetch(definition["stop_id"])
            departures, seen = [], set()
            for item in rows or []:
                if not isinstance(item, dict) or str(item.get("lineName", "")).upper() != ROUTE:
                    continue
                # The arrivals endpoint is stop-scoped, but enforce exact stop
                # identity when the response includes a NaPTAN ID.
                naptan = item.get("naptanId")
                if naptan and str(naptan).upper() != definition["stop_id"].upper():
                    continue
                departure = self._normalise(item)
                if departure is None or (departure["trip_id"] and departure["trip_id"] in seen):
                    continue
                if departure["trip_id"]:
                    seen.add(departure["trip_id"])
                departures.append(departure)
            departures.sort(key=lambda row: row["estimated"])
            result[key] = {
                "stop_name": definition["name"],
                "stop_id": definition["stop_id"],
                "route": ROUTE,
                "source": "tfl",
                "observed_at": observed_at,
                "departures": departures,
            }
        return result
