"""MatrixPortal / Wokwi information-board entrypoint."""

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
from screen_client import ClockState, ScreenClient, ScreenRotation


def fixture_payload(now):
    services = animated_services(now, settings.ANIMATION_SECONDS)
    return {
        "fetched_at": "2026-09-12T12:00:00Z",
        "screens": [
            {
                "id": "departures",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "title": "{} departures".format(settings.STATION_CRS),
                "source": "fixture",
                "stale": False,
                "services": services[:3],
            }
        ],
    }


display = create(settings)
rotation = ScreenRotation()
clock = ClockState()
client = ScreenClient(settings) if settings.SCREEN_SOURCE == "api" else None
next_fetch = 0
transport_stale = False
fixture_clock_synced = False

while True:
    now = time.monotonic()
    should_fetch = settings.SCREEN_SOURCE == "fixture" or now >= next_fetch
    if should_fetch:
        try:
            payload = fixture_payload(now) if client is None else client.fetch()
            rotation.update(payload.get("screens"), now)
            fetched_at = payload.get("fetched_at")
            if fetched_at and (client is not None or not fixture_clock_synced):
                clock.sync(fetched_at, now)
                fixture_clock_synced = True
            transport_stale = False
        except Exception as error:
            print("Screen fetch failed:", error)
            transport_stale = bool(rotation.screens)
        next_fetch = now + settings.POLL_SECONDS

    screen, phase = rotation.current(now)
    if transport_stale:
        screen = dict(screen)
        screen["stale"] = True
    display.show(screen, clock.text(now), phase=phase if settings.ANIMATE else 2)
    time.sleep(settings.FRAME_SECONDS if settings.ANIMATE else settings.POLL_SECONDS)
