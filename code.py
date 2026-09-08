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
from fixtures import SERVICES


def fetch_services():
    if settings.DATA_SOURCE == "fixture":
        return SERVICES
    from rail_client import NationalRailClient
    return NationalRailClient(settings).fetch()


display = create(settings)
services = []
stale = False

while True:
    try:
        fresh = fetch_services()
        if fresh:
            services = fresh
            stale = False
    except Exception as error:
        print("Fetch failed:", error)
        stale = bool(services)
    if not services:
        services = [{"time": "--:--", "destination": "No data", "platform": "-", "status": "Waiting", "cancelled": False}]
    display.show(settings.STATION_CRS, services, stale)
    time.sleep(settings.POLL_SECONDS)

