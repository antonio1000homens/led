"""Live departures board entrypoint."""

import time

import settings

try:
    import settings_local as local
except ImportError:
    local = None

if local:
    for name in dir(local):
        if not name.startswith("_"):
            setattr(settings, name, getattr(local, name))

from display import create
from fixtures import animated_services


def fetch_services(now):
    if settings.DATA_SOURCE == "fixture":
        return animated_services(now, settings.ANIMATION_SECONDS)
    from rail_client import NationalRailClient
    return NationalRailClient(settings).fetch()


display = create(settings)
services = []
stale = False
next_fetch = 0

while True:
    now = time.monotonic()
    if settings.DATA_SOURCE == "fixture" or now >= next_fetch:
        try:
            fresh = fetch_services(now)
            if fresh:
                services = fresh
                stale = False
        except Exception as error:
            print("Fetch failed:", error)
            stale = bool(services)
        next_fetch = now + settings.POLL_SECONDS
    if not services:
        services = [{"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting", "cancelled": False}]
    display.show(settings.STATION_CRS, services, stale, phase=now % settings.ANIMATION_SECONDS if settings.ANIMATE else 2)
    time.sleep(settings.FRAME_SECONDS if settings.ANIMATE else settings.POLL_SECONDS)
