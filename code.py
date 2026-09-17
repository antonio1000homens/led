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

from queue_display import create
from fixtures import animated_services
from screen_client import ClockState, ScreenClient, ScreenRotation


if settings.SCREEN_SOURCE not in ("fixture", "api"):
    raise ValueError("SCREEN_SOURCE must be fixture or api")


def fixture_payload(now):
    services = animated_services(now, settings.ANIMATION_SECONDS)
    weather = {
        "source": "fixture",
        "stale": False,
        "temperature_c": 17,
        "weather_code": 2,
        "icon": "partly_cloudy_day",
        "is_day": True,
    }
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
                "weather": weather,
            }
        ],
    }


def hardware_safe_screen(screen):
    """Keep hardware-safe screen text without collapsing combined park titles."""
    return screen


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
    screen = hardware_safe_screen(screen)
    if transport_stale:
        screen = dict(screen)
        screen["stale"] = True
        weather = screen.get("weather")
        if isinstance(weather, dict):
            weather = dict(weather)
            weather["stale"] = True
            screen["weather"] = weather
    display.show(
        screen,
        clock.text(now),
        clock_date=clock.date_text(now),
        phase=phase if settings.ANIMATE else 2,
    )
    time.sleep(settings.FRAME_SECONDS if settings.ANIMATE else settings.POLL_SECONDS)
