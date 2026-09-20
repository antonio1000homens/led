"""MatrixPortal / Wokwi information-board entrypoint."""

import time

try:
    import gc
except ImportError:
    gc = None

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
from matrix_runtime import RuntimeMode
from screen_client import ClockState, ScreenClient, ScreenRotation
from matrix_config import MATRIX_REFRESH_FPS


if settings.SCREEN_SOURCE not in ("fixture", "api"):
    raise ValueError("SCREEN_SOURCE must be fixture or api")

# The four-panel MatrixPortal installation is operated in static mode.  A
# local settings file may select the backend and network, but cannot re-enable
# the high-frequency animation path that produced scan-line flashes.
if settings.DISPLAY_BACKEND == "matrix":
    settings.ANIMATE = False


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
buttons = None
if settings.DISPLAY_BACKEND == "matrix":
    from button_control import MatrixButtons

    buttons = MatrixButtons()
next_fetch = 0
transport_stale = False
fixture_clock_synced = False
runtime_mode = RuntimeMode()
rendered_diagnostic_index = None
last_render_key = None


def _matrix_root_token():
    """Return the current root-group identity when running on MatrixPortal."""
    base = getattr(display, "base", display)
    hardware_display = getattr(base, "display", None)
    root_group = getattr(hardware_display, "root_group", None)
    return id(root_group) if root_group is not None else None


def _memory_free():
    if gc is None or not hasattr(gc, "mem_free"):
        return None
    return gc.mem_free()


def _display_phase(screen, phase):
    if settings.ANIMATE:
        return phase
    if screen.get("kind") == "calendar_agenda" and screen.get("source") == "todoist":
        return phase
    return 2


def _smooth_todoist(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "calendar_agenda"
        and screen.get("source") == "todoist"
    )

while True:
    now = time.monotonic()
    for event in buttons.poll(now) if buttons is not None else ():
        if runtime_mode.handle(event, rotation, now):
            rendered_diagnostic_index = None

    if runtime_mode.mode == "diagnostic":
        if rendered_diagnostic_index != runtime_mode.diagnostic_index:
            name, color = runtime_mode.diagnostic()
            print("DIAGNOSTIC", name)
            display.show_diagnostic(color)
            rendered_diagnostic_index = runtime_mode.diagnostic_index
        time.sleep(settings.FRAME_SECONDS)
        continue

    should_fetch = settings.SCREEN_SOURCE == "fixture" or now >= next_fetch
    if should_fetch:
        try:
            print("FETCH START")
            payload = fixture_payload(now) if client is None else client.fetch()
            screens = payload.get("screens")
            print("FETCH OK screens={}".format(len(screens or [])))
            rotation.update(screens, now)
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
    frame_started = time.monotonic()
    render_key = (screen.get("id"), screen.get("kind")) if isinstance(screen, dict) else (None, None)
    instrument_render = render_key != last_render_key
    if instrument_render:
        if gc is not None and hasattr(gc, "collect"):
            gc.collect()
        render_started = time.monotonic()
        memory_before = _memory_free()
        root_before = _matrix_root_token()
        print(
            "RENDER START id={} kind={} index={} phase={} mode={} mem={}".format(
                render_key[0], render_key[1], rotation.index, phase, runtime_mode.mode, memory_before
            )
        )
    display.show(
        screen,
        clock.text(now),
        clock_date=clock.date_text(now),
        phase=_display_phase(screen, phase),
    )
    if instrument_render:
        memory_after = _memory_free()
        root_after = _matrix_root_token()
        print(
            "RENDER OK id={} duration={:.3f} mem_before={} mem_after={} root_changed={}".format(
                render_key[0], time.monotonic() - render_started, memory_before, memory_after,
                root_before != root_after,
            )
        )
        last_render_key = render_key
    smooth_todoist = _smooth_todoist(screen)
    if settings.ANIMATE or smooth_todoist:
        frame_seconds = settings.FRAME_SECONDS if settings.ANIMATE else 1.0 / MATRIX_REFRESH_FPS
        remaining = frame_seconds - (time.monotonic() - frame_started)
        if remaining > 0:
            time.sleep(remaining)
    else:
        # Static pages must still rotate independently of the network poll.
        # Waking only at the next page/fetch boundary avoids repeatedly
        # rebuilding the complete HUB75 framebuffer, which can show as
        # horizontal flashes on long panel chains.
        duration = max(1, int(screen.get("duration_seconds") or 8))
        until_rotation = max(0.05, duration - max(0, phase))
        until_fetch = max(0.05, next_fetch - time.monotonic())
        time.sleep(min(until_rotation, until_fetch))
