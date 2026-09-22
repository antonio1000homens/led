"""MatrixPortal / Wokwi information-board entrypoint."""

import sys
import time

# Wokwi requires code.py at the project root, while implementation modules are
# grouped by responsibility in the repository. Physical-board staging flattens
# these directories back onto CIRCUITPY, where the extra paths are harmless.
for source_path in ("/firmware", "/shared", "firmware", "shared"):
    if source_path not in sys.path:
        sys.path.append(source_path)

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
from flash_events import FlashState
from matrix_runtime import RuntimeMode
from screen_client import ClockState, ScreenClient, ScreenRotation
from matrix_config import (
    MATRIX_PRESENTATION_MODE,
    MATRIX_REFRESH_FPS,
    MATRIX_STATS_INTERVAL_SECONDS,
)


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
flash = FlashState(
    enabled=(settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL),
)
flash_resume = None
mqtt = None
if settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL:
    from mqtt_client import FlashMqttClient

    def receive_flash(payload):
        global flash_resume, last_render_key
        now = time.monotonic()
        epoch_now = clock.epoch(now)
        if epoch_now is None:
            system_epoch = time.time()
            epoch_now = system_epoch if system_epoch >= 1000000000 else None
        if epoch_now is None:
            print("FLASH ignored: clock not synchronized")
            return
        if flash.accept(payload, now, epoch_now=epoch_now):
            # A replacement must not advance the frozen underlying rotation.
            if flash_resume is None:
                flash_resume = rotation.pause(now)
            last_render_key = None
            print("FLASH START id={}".format(flash.event["id"]))

    mqtt = FlashMqttClient(settings, receive_flash)
rendered_diagnostic_index = None
last_render_key = None

# Todoist frame-pacing diagnostics are reset whenever the board enters the
# Todoist screen, so each serial summary represents one comparable run.
pace_active = False
pace_started = 0.0
pace_last_report = 0.0
pace_ticks = 0
pace_late_frames = 0
pace_late_streak = 0
pace_max_late_streak = 0
next_animation_deadline = None

# Low-volume work-attribution telemetry for soak runs. These counters are
# reported with FRAME PACE and deliberately avoid per-frame serial output.
telemetry_started = time.monotonic()
telemetry_fetches = 0
telemetry_fetch_failures = 0
telemetry_fetch_total = 0.0
telemetry_fetch_max = 0.0
telemetry_scene_renders = 0
telemetry_scene_render_total = 0.0
telemetry_scene_render_max = 0.0
telemetry_scene_render_over_budget = 0


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
    if _smooth_departures(screen):
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


def _smooth_departures(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "rail_combined"
    )


def _report_pace(now):
    if not pace_active or now - pace_last_report < MATRIX_STATS_INTERVAL_SECONDS:
        return False
    elapsed = max(0.001, now - pace_started)
    telemetry_elapsed = max(0.001, now - telemetry_started)
    fetch_average = telemetry_fetch_total / telemetry_fetches if telemetry_fetches else 0.0
    render_average = (
        telemetry_scene_render_total / telemetry_scene_renders
        if telemetry_scene_renders else 0.0
    )
    print(
        "FRAME PACE mode={} target_fps={} elapsed={:.1f} animation_ticks={} "
        "tick_fps={:.2f} late_frames={} max_late_streak={} "
        "fetches={} fetch_failures={} fetch_avg={:.3f} fetch_max={:.3f} "
        "scene_renders={} render_avg={:.3f} render_max={:.3f} "
        "render_over_budget={} telemetry_elapsed={:.1f}".format(
            MATRIX_PRESENTATION_MODE,
            MATRIX_REFRESH_FPS,
            elapsed,
            pace_ticks,
            pace_ticks / elapsed,
            pace_late_frames,
            pace_max_late_streak,
            telemetry_fetches,
            telemetry_fetch_failures,
            fetch_average,
            telemetry_fetch_max,
            telemetry_scene_renders,
            render_average,
            telemetry_scene_render_max,
            telemetry_scene_render_over_budget,
            telemetry_elapsed,
        )
    )
    return True


def _apply_flash_config(payload):
    config = payload.get("flash") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        return
    # The public screen payload carries only non-secret operational settings.
    # Transport activation remains controlled exclusively by local board flags.
    flash.configure(
        enabled=(settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL and config.get("enabled", False)),
        duration_seconds=config.get("screen_duration_seconds"),
    )


while True:
    now = time.monotonic()
    if mqtt is not None:
        mqtt.poll(now)
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
        fetch_started = time.monotonic()
        try:
            print("FETCH START")
            payload = fixture_payload(now) if client is None else client.fetch()
            screens = payload.get("screens")
            fetch_duration = time.monotonic() - fetch_started
            telemetry_fetches += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("FETCH OK screens={} duration={:.3f}".format(len(screens or []), fetch_duration))
            rotation.update(screens, now)
            _apply_flash_config(payload)
            fetched_at = payload.get("fetched_at")
            if fetched_at and (client is not None or not fixture_clock_synced):
                clock.sync(fetched_at, now)
                fixture_clock_synced = True
            transport_stale = False
        except Exception as error:
            fetch_duration = time.monotonic() - fetch_started
            telemetry_fetches += 1
            telemetry_fetch_failures += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("Screen fetch failed duration={:.3f}:".format(fetch_duration), error)
            transport_stale = bool(rotation.screens)
        next_fetch = now + settings.POLL_SECONDS

    if flash.active(now):
        screen, phase = flash.screen(), now - flash.started_at
    else:
        if flash.event is not None:
            flash.clear()
            if flash_resume is not None:
                rotation.resume(now, flash_resume[0], flash_resume[1])
                flash_resume = None
            last_render_key = None
            print("FLASH END")
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
        render_duration = time.monotonic() - render_started
        telemetry_scene_renders += 1
        telemetry_scene_render_total += render_duration
        telemetry_scene_render_max = max(telemetry_scene_render_max, render_duration)
        if render_duration > (1.0 / max(1, MATRIX_REFRESH_FPS)):
            telemetry_scene_render_over_budget += 1
        print(
            "RENDER OK id={} duration={:.3f} mem_before={} mem_after={} root_changed={}".format(
                render_key[0], render_duration, memory_before, memory_after,
                root_before != root_after,
            )
        )
        last_render_key = render_key
    smooth_animation = _smooth_todoist(screen) or _smooth_departures(screen)
    if smooth_animation:
        frame_seconds = 1.0 / MATRIX_REFRESH_FPS
        if not pace_active:
            pace_active = True
            pace_started = frame_started
            pace_last_report = frame_started
            pace_ticks = 0
            pace_late_frames = 0
            pace_late_streak = 0
            pace_max_late_streak = 0
            next_animation_deadline = frame_started

        pace_ticks += 1
        after_render = time.monotonic()

        if MATRIX_PRESENTATION_MODE in ("immediate", "auto_refresh"):
            # Modes B/C own the animation cadence in the application. Use an
            # absolute deadline to avoid accumulating render-time drift.
            next_animation_deadline += frame_seconds
            remaining = next_animation_deadline - after_render
            if remaining > 0:
                pace_late_streak = 0
                time.sleep(remaining)
            else:
                pace_late_frames += 1
                pace_late_streak += 1
                pace_max_late_streak = max(pace_max_late_streak, pace_late_streak)
                # A fetch or screen transition can put us more than one full
                # frame behind. Rebase rather than spinning through stale ticks.
                if -remaining > frame_seconds:
                    next_animation_deadline = after_render
        else:
            # Mode A is the control: preserve the existing relative sleep so
            # its measurements remain directly comparable with issue #66.
            remaining = frame_seconds - (after_render - frame_started)
            if remaining > 0:
                pace_late_streak = 0
                time.sleep(remaining)
            else:
                pace_late_frames += 1
                pace_late_streak += 1
                pace_max_late_streak = max(pace_max_late_streak, pace_late_streak)

        report_now = time.monotonic()
        if _report_pace(report_now):
            pace_last_report = report_now
    elif settings.ANIMATE:
        pace_active = False
        next_animation_deadline = None
        frame_seconds = settings.FRAME_SECONDS
        remaining = frame_seconds - (time.monotonic() - frame_started)
        if remaining > 0:
            time.sleep(remaining)
    else:
        pace_active = False
        next_animation_deadline = None
        # Static pages must still rotate independently of the network poll.
        # Waking only at the next page/fetch boundary avoids repeatedly
        # rebuilding the complete HUB75 framebuffer, which can show as
        # horizontal flashes on long panel chains.
        duration = max(1, int(screen.get("duration_seconds") or 8))
        until_rotation = max(0.05, duration - max(0, phase))
        until_fetch = max(0.05, next_fetch - time.monotonic())
        time.sleep(min(until_rotation, until_fetch))
