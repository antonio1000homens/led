"""Transitous/MOTIS provider for the SL7 bus screens."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TRANSITOUS_API = "https://api.transitous.org/api"
TRANSITOUS_USER_AGENT = "led-sl7-bus/1.0 (https://github.com/antonio1000homens/led)"
ROUTE = "SL7"
DEFAULT_STOPS = {
    "heathrow": {"name": "Heathrow", "stop_id": "gb-great-britain_490008016S"},
    "new-malden": {"name": "New Malden", "stop_id": "gb-great-britain_490015206K"},
}

def _iso(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value, timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _departure_time(item):
    place = item.get("place") or {}
    return place.get("departure") or place.get("scheduledDeparture") or item.get("departure")

class TransitousBusProvider:
    def __init__(self, stops=None, base_url=TRANSITOUS_API, timeout=15, opener=None):
        self.stops = dict(stops or DEFAULT_STOPS)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.opener = opener or urlopen

    def _fetch(self, stop_id):
        query = urlencode({"stopId": stop_id, "n": 100, "radius": 250})
        request = Request(f"{self.base_url}/v5/stoptimes?{query}", headers={"Accept": "application/json", "User-Agent": TRANSITOUS_USER_AGENT})
        with self.opener(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _normalise(item):
        place = item.get("place") or {}
        planned = _iso(place.get("scheduledDeparture") or item.get("scheduledDeparture") or _departure_time(item))
        estimated = _iso(place.get("departure") or item.get("departure"))
        if not planned:
            return None
        return {"planned": planned, "estimated": estimated, "trip_id": item.get("tripId"), "destination": (item.get("headsign") or "SL7").strip(), "cancelled": bool(item.get("cancelled") or item.get("tripCancelled") or place.get("cancelled")), "alerts": bool(item.get("alerts") or place.get("alerts"))}

    def fetch(self, now=None):
        observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        result = {}
        for key, definition in self.stops.items():
            payload = self._fetch(definition["stop_id"])
            rows = payload if isinstance(payload, list) else payload.get("stopTimes", payload.get("stoptimes", payload.get("times", [])))
            departures, seen = [], set()
            for item in rows or []:
                if not isinstance(item, dict) or item.get("routeShortName") != ROUTE:
                    continue
                # Radius queries may include neighbouring stops. Honour the
                # exact requested departure stop when MOTIS supplies a stopId.
                place_id = (item.get("place") or {}).get("stopId")
                if place_id and str(place_id).removesuffix("_G") != definition["stop_id"].removesuffix("_G"):
                    continue
                departure = self._normalise(item)
                if departure is None or (departure["trip_id"] and departure["trip_id"] in seen):
                    continue
                if departure["trip_id"]:
                    seen.add(departure["trip_id"])
                departures.append(departure)
            departures.sort(key=lambda row: row["estimated"] or row["planned"])
            result[key] = {"stop_name": definition["name"], "stop_id": definition["stop_id"], "route": ROUTE, "observed_at": observed_at, "departures": departures}
        return result
