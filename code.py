"""MatrixPortal / Wokwi information-board entrypoint."""

import sys
import time

# Wokwi requires code.py at the project root, while implementation modules are
# grouped by responsibility in the repository. Physical-board staging flattens
# these directories back onto CIRCUITPY, where the extra paths are harmless.
for source_path in ("/hardware/matrixportal/firmware", "/shared", "hardware/matrixportal/firmware", "shared"):
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

from wifi_startup import start_wifi

start_wifi(settings)

from queue_display import create
from fixtures import animated_services
from flash_events import FlashState
from animation_scheduler import earliest_wake_seconds, next_deadline, screen_fetch_decision
from matrix_runtime import RuntimeMode
from screen_client import ClockState, ScreenClient, ScreenRotation
from mqtt_screens import MqttScreenState
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
                "id": "steam-train",
                "kind": "steam_train_intro",
                "duration_seconds": 16,
                "title": "Steam train",
                "source": "fixture",
                "stale": False,
                "animation_speed": 24,
                "words": "choo choo",
            },
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

_pending_button_events = []
_BUTTON_POLL_SECONDS = 0.05
_MQTT_SLEEP_POLL_SECONDS = 0.25
_ANIMATION_FETCH_RETRY_SECONDS = 0.5
_ANIMATION_FETCH_GUARD_SECONDS = 3.0
mqtt_screens_changed = False


def _sleep_interruptible(seconds, service_mqtt=False):
    """Sleep without changing render cadence, servicing requested I/O while idle."""
    global mqtt_screens_changed
    seconds = max(0.0, float(seconds or 0))
    if buttons is None and not service_mqtt:
        time.sleep(seconds)
        return
    deadline = time.monotonic() + seconds
    next_mqtt_poll = time.monotonic()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(_BUTTON_POLL_SECONDS, remaining))
        now = time.monotonic()
        epoch_now = _reminder_epoch(now)
        if epoch_now is not None and mqtt_screens.expire(epoch_now):
            rotation.update_sources(rotation.http_screens, mqtt_screens.screens(epoch_now), now)
            mqtt_screens_changed = True
            return
        if service_mqtt and _service_reminder_clock(now):
            return
        if service_mqtt and mqtt is not None and now >= next_mqtt_poll:
            mqtt.poll(now)
            next_mqtt_poll = now + _MQTT_SLEEP_POLL_SECONDS
            if mqtt_screens_changed:
                return
            if flash.active(now):
                return
        if buttons is not None:
            events = buttons.poll(now)
            if events:
                _pending_button_events.extend(events)
                return


next_fetch = 0
transport_stale = False
fixture_clock_synced = False
runtime_mode = RuntimeMode()
flash = FlashState(
    # Reminder events stay gated until the screen payload enables Flash in
    # the admin control plane. Cycle screens use the independent MQTT source.
    enabled=False,
)
flash_resume = None
mqtt = None
mqtt_screens = MqttScreenState(
    getattr(settings, "MQTT_SCREENS_TOPIC", "led/screens/+")
)


def _reminder_epoch(now):
    epoch_now = clock.epoch(now)
    if epoch_now is None:
        system_epoch = time.time()
        epoch_now = system_epoch if system_epoch >= 1000000000 else None
    return epoch_now


def _flash_started(now):
    global flash_resume, last_render_key
    if flash_resume is None:
        flash_resume = rotation.freeze(now)
    last_render_key = None
    print("FLASH START id={}".format(flash.event["id"]))


def _service_reminder_clock(now):
    if not flash.enabled or flash.pending is None:
        return False
    if flash.tick(now, _reminder_epoch(now)):
        _flash_started(now)
        return True
    return False


if settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL:
    from mqtt_client import FlashMqttClient

    def receive_mqtt(topic, payload):
        global mqtt_screens_changed
        now = time.monotonic()
        if topic == settings.MQTT_TOPIC:
            epoch_now = _reminder_epoch(now)
            if epoch_now is None:
                print("FLASH ignored: clock not synchronized")
                return
            if flash.accept(payload, now, epoch_now=epoch_now):
                _flash_started(now)
            return
        epoch_now = _reminder_epoch(now)
        if epoch_now is None:
            print("MQTT screen ignored: clock not synchronized")
            return
        if mqtt_screens.accept(topic, payload, epoch_now):
            rotation.update_sources(
                rotation.http_screens, mqtt_screens.screens(epoch_now), now
            )
            mqtt_screens_changed = True

    mqtt = FlashMqttClient(
        settings,
        receive_mqtt,
        startup_delay_seconds=settings.MQTT_STARTUP_DELAY_SECONDS,
    )
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
pace_last_tick_started = None
pace_interval_total = 0.0
pace_interval_count = 0
pace_interval_max = 0.0
pace_worst_gap_show = 0.0
pace_worst_gap_sleep = 0.0
pace_worst_gap_other = 0.0
pace_worst_gap_preframe = 0.0
pace_interval_over_200ms = 0
pace_interval_over_500ms = 0
pace_other_total = 0.0
pace_other_count = 0
pace_other_max = 0.0
pace_other_over_200ms = 0
pace_preframe_total = 0.0
pace_preframe_count = 0
pace_preframe_max = 0.0
pace_preframe_stage_max = {
    "reminder": 0.0, "mqtt": 0.0, "buttons": 0.0,
    "fetch_decision": 0.0, "fetch": 0.0, "screen_select": 0.0,
}
pace_last_show_seconds = 0.0
pace_last_sleep_seconds = 0.0
pace_sleep_requested_total = 0.0
pace_sleep_requested_count = 0
pace_sleep_requested_max = 0.0
pace_sleep_actual_total = 0.0
pace_sleep_actual_count = 0
pace_sleep_actual_max = 0.0
pace_sleep_overshoots = 0
pace_show_total = 0.0
pace_show_count = 0
pace_show_max = 0.0
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
animation_cadence = None


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
    if _smooth_steam_train(screen):
        return phase
    if screen.get("kind") == "calendar_agenda" and screen.get("source") == "todoist":
        return phase
    if _smooth_queue(screen):
        return phase
    if _smooth_sun_weather(screen):
        return phase
    if _smooth_bin_collection(screen):
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


def _smooth_queue(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "theme_park_queues"
    )


def _smooth_sun_weather(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "weather_sun"
    )


def _smooth_steam_train(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "steam_train_intro"
    )


def _smooth_bin_collection(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "bin_collection"
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
    interval_average = (
        pace_interval_total / pace_interval_count if pace_interval_count else 0.0
    )
    other_average = pace_other_total / pace_other_count if pace_other_count else 0.0
    sleep_requested_average = (
        pace_sleep_requested_total / pace_sleep_requested_count
        if pace_sleep_requested_count else 0.0
    )
    sleep_actual_average = (
        pace_sleep_actual_total / pace_sleep_actual_count
        if pace_sleep_actual_count else 0.0
    )
    show_average = pace_show_total / pace_show_count if pace_show_count else 0.0
    print(
        "FRAME PACE mode={} target_fps={} elapsed={:.1f} animation_ticks={} "
        "tick_fps={:.2f} late_frames={} max_late_streak={} "
        "tick_gap_avg={:.3f} tick_gap_max={:.3f} gap_over_200ms={} "
        "gap_over_500ms={} other_avg={:.4f} other_max={:.4f} "
        "worst_gap_parts_show={:.3f} sleep={:.3f} other={:.3f} "
        "preframe_avg={:.4f} preframe_max={:.4f} worst_preframe={:.3f} "
        "stage_maxes={} "
        "other_over_200ms={} show_avg={:.4f} show_max={:.4f} "
        "sleep_req_avg={:.4f} sleep_req_max={:.4f} "
        "sleep_avg={:.4f} sleep_max={:.4f} sleep_overshoots={} "
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
            interval_average,
            pace_interval_max,
            pace_interval_over_200ms,
            pace_interval_over_500ms,
            other_average,
            pace_other_max,
            pace_worst_gap_show,
            pace_worst_gap_sleep,
            pace_worst_gap_other,
            pace_preframe_total / pace_preframe_count if pace_preframe_count else 0.0,
            pace_preframe_max,
            pace_worst_gap_preframe,
            pace_preframe_stage_max,
            pace_other_over_200ms,
            show_average,
            pace_show_max,
            sleep_requested_average,
            pace_sleep_requested_max,
            sleep_actual_average,
            pace_sleep_actual_max,
            pace_sleep_overshoots,
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
    # Both board-local flags and this runtime setting gate reminders.
    runtime_enabled = (
        settings.MQTT_ENABLED
        and settings.MQTT_ENABLE_EXPERIMENTAL
        and config.get("enabled", False)
    )
    flash.configure(
        enabled=runtime_enabled,
        duration_seconds=config.get("screen_duration_seconds"),
    )


while True:
    now = time.monotonic()
    loop_started = now
    stage_started = time.monotonic()
    _service_reminder_clock(now)
    stage_durations = {"reminder": time.monotonic() - stage_started}
    stage_started = time.monotonic()
    if mqtt is not None:
        mqtt_allow_connect = True
        if rotation.screens and not flash.active(now):
            mqtt_screen, mqtt_phase = rotation.current(now)
            mqtt_allow_connect = not display.animation_active(mqtt_screen, mqtt_phase)
        mqtt.poll(now, allow_connect=mqtt_allow_connect)
    stage_durations["mqtt"] = time.monotonic() - stage_started
    stage_started = time.monotonic()
    button_events = list(_pending_button_events)
    _pending_button_events[:] = []
    if buttons is not None:
        button_events.extend(buttons.poll(now))
    stage_durations["buttons"] = time.monotonic() - stage_started
    for event in button_events:
        if runtime_mode.mode == "normal" and event in ("up", "down"):
            display.adjust_brightness(1 if event == "up" else -1)
            continue
        if runtime_mode.handle(event, rotation, now):
            rendered_diagnostic_index = None

    if runtime_mode.mode == "diagnostic":
        if rendered_diagnostic_index != runtime_mode.diagnostic_index:
            name, color = runtime_mode.diagnostic()
            print("DIAGNOSTIC", name)
            display.show_diagnostic(color)
            rendered_diagnostic_index = runtime_mode.diagnostic_index
        _sleep_interruptible(settings.FRAME_SECONDS)
        continue

    stage_started = time.monotonic()
    should_fetch = settings.SCREEN_SOURCE == "fixture"
    fetch_during_animation = False
    if settings.SCREEN_SOURCE != "fixture":
        candidate = None
        candidate_phase = 0
        if rotation.screens and not flash.active(now):
            candidate, candidate_phase = rotation.current(now)
            fetch_during_animation = (
                _smooth_todoist(candidate)
                or _smooth_departures(candidate)
                or _smooth_steam_train(candidate)
                or _smooth_sun_weather(candidate)
            )
        animation_active = bool(
            fetch_during_animation
            and display.animation_active(candidate, candidate_phase)
        )
        safe_window = None
        if fetch_during_animation and not animation_active:
            safe_window = display.animation_sleep_seconds(candidate, candidate_phase)
        should_fetch, next_fetch = screen_fetch_decision(
            now,
            next_fetch,
            animation_active,
            safe_window,
            _ANIMATION_FETCH_RETRY_SECONDS,
            _ANIMATION_FETCH_GUARD_SECONDS,
        )
    stage_durations["fetch_decision"] = time.monotonic() - stage_started
    stage_started = time.monotonic()
    if should_fetch:
        fetch_started = time.monotonic()
        # Screen API calls are synchronous and can take multiple animation
        # frames. Freeze the selected screen phase for that interval so the
        # first post-fetch frame resumes where the last one left off.
        fetch_resume = None
        if rotation.screens and not flash.active(fetch_started):
            fetch_resume = rotation.pause(fetch_started)
        try:
            print("FETCH START")
            payload = fixture_payload(now) if client is None else client.fetch()
            screens = payload.get("screens")
            fetch_completed = time.monotonic()
            fetch_duration = fetch_completed - fetch_started
            telemetry_fetches += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("FETCH OK screens={} duration={:.3f}".format(len(screens or []), fetch_duration))
            epoch_now = _reminder_epoch(fetch_completed)
            rotation.update_sources(
                screens,
                mqtt_screens.screens(epoch_now) if epoch_now is not None else [],
                fetch_completed,
            )
            if fetch_resume is not None:
                rotation.resume(fetch_completed, fetch_resume[0], fetch_resume[1])
            _apply_flash_config(payload)
            fetched_at = payload.get("clock_at") or payload.get("fetched_at")
            if fetched_at and (client is not None or not fixture_clock_synced):
                clock.sync(fetched_at, fetch_completed)
                fixture_clock_synced = True
            transport_stale = False
        except Exception as error:
            fetch_completed = time.monotonic()
            fetch_duration = fetch_completed - fetch_started
            telemetry_fetches += 1
            telemetry_fetch_failures += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("Screen fetch failed duration={:.3f}:".format(fetch_duration), error)
            transport_stale = bool(rotation.screens)
            if fetch_resume is not None:
                rotation.resume(fetch_completed, fetch_resume[0], fetch_resume[1])
        now = fetch_completed
        next_fetch = now + settings.POLL_SECONDS
        if fetch_during_animation and hasattr(display, "note_fetch_overlap"):
            display.note_fetch_overlap()
    stage_durations["fetch"] = time.monotonic() - stage_started

    epoch_now = _reminder_epoch(now)
    if epoch_now is not None and mqtt_screens.expire(epoch_now):
        rotation.update_sources(rotation.http_screens, mqtt_screens.screens(epoch_now), now)
        mqtt_screens_changed = True

    stage_started = time.monotonic()
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
    stage_durations["screen_select"] = time.monotonic() - stage_started
    screen = hardware_safe_screen(screen)
    if transport_stale and any(candidate is screen for candidate in rotation.http_screens):
        screen = dict(screen)
        screen["stale"] = True
        weather = screen.get("weather")
        if isinstance(weather, dict):
            weather = dict(weather)
            weather["stale"] = True
            screen["weather"] = weather
    frame_started = time.monotonic()
    preframe_duration = frame_started - loop_started
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
    show_started = time.monotonic()
    display.show(
        screen,
        clock.text(now),
        clock_date=clock.date_text(now),
        phase=_display_phase(screen, phase),
    )
    show_duration = time.monotonic() - show_started
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
    mqtt_screens_changed = False
    smooth_animation = (
        _smooth_todoist(screen)
        or _smooth_departures(screen)
        or _smooth_queue(screen)
        or _smooth_steam_train(screen)
        or _smooth_sun_weather(screen)
        or _smooth_bin_collection(screen)
    )
    if smooth_animation:
        desired_cadence = display.animation_cadence(screen, phase)
        if desired_cadence <= 0:
            pace_active = False
            pace_last_tick_started = None
            animation_cadence = None
            next_animation_deadline = None
            boundary_sleep = display.animation_sleep_seconds(screen, phase)
            duration = max(1.0, float(screen.get("duration_seconds") or 8))
            until_rotation = max(0.05, duration - max(0, phase))
            until_fetch = max(0.05, next_fetch - time.monotonic())
            _sleep_interruptible(
                earliest_wake_seconds(until_rotation, until_fetch, boundary_sleep),
                service_mqtt=True,
            )
            continue
        cadence_changed = animation_cadence != desired_cadence
        if cadence_changed:
            was_active = pace_active
            animation_cadence = desired_cadence
            next_animation_deadline = None
            if was_active and hasattr(display, "note_cadence_switch"):
                display.note_cadence_switch()
        frame_seconds = 1.0 / desired_cadence
        after_render = time.monotonic()
        if not pace_active:
            pace_active = True
            pace_started = after_render
            pace_last_report = after_render
            pace_ticks = 0
            pace_late_frames = 0
            pace_late_streak = 0
            pace_max_late_streak = 0
            pace_last_tick_started = after_render
            pace_interval_total = 0.0
            pace_interval_count = 0
            pace_interval_max = 0.0
            pace_worst_gap_show = 0.0
            pace_worst_gap_sleep = 0.0
            pace_worst_gap_other = 0.0
            pace_worst_gap_preframe = 0.0
            pace_interval_over_200ms = 0
            pace_interval_over_500ms = 0
            pace_other_total = 0.0
            pace_other_count = 0
            pace_other_max = 0.0
            pace_other_over_200ms = 0
            pace_preframe_total = 0.0
            pace_preframe_count = 0
            pace_preframe_max = 0.0
            for stage_name in pace_preframe_stage_max:
                pace_preframe_stage_max[stage_name] = 0.0
            pace_last_show_seconds = 0.0
            pace_last_sleep_seconds = 0.0
            pace_sleep_requested_total = 0.0
            pace_sleep_requested_count = 0
            pace_sleep_requested_max = 0.0
            pace_sleep_actual_total = 0.0
            pace_sleep_actual_count = 0
            pace_sleep_actual_max = 0.0
            pace_sleep_overshoots = 0
            pace_show_total = 0.0
            pace_show_count = 0
            pace_show_max = 0.0
            if not instrument_render:
                pace_show_total += show_duration
                pace_show_count += 1
                pace_show_max = max(pace_show_max, show_duration)
            next_animation_deadline = after_render
        else:
            if pace_last_tick_started is not None:
                tick_interval = frame_started - pace_last_tick_started
                pace_interval_total += tick_interval
                pace_interval_count += 1
                pace_interval_max = max(pace_interval_max, tick_interval)
                if tick_interval > 0.2:
                    pace_interval_over_200ms += 1
                if tick_interval > 0.5:
                    pace_interval_over_500ms += 1
                other_time = max(
                    0.0,
                    tick_interval - pace_last_show_seconds - pace_last_sleep_seconds,
                )
                if tick_interval >= pace_interval_max:
                    pace_worst_gap_show = pace_last_show_seconds
                    pace_worst_gap_sleep = pace_last_sleep_seconds
                    pace_worst_gap_other = other_time
                    pace_worst_gap_preframe = preframe_duration
                pace_other_total += other_time
                pace_other_count += 1
                pace_other_max = max(pace_other_max, other_time)
                if other_time > 0.2:
                    pace_other_over_200ms += 1
                pace_preframe_total += preframe_duration
                pace_preframe_count += 1
                pace_preframe_max = max(pace_preframe_max, preframe_duration)
                for stage_name, stage_duration in stage_durations.items():
                    pace_preframe_stage_max[stage_name] = max(
                        pace_preframe_stage_max[stage_name], stage_duration
                    )
            pace_last_tick_started = frame_started
            pace_show_total += show_duration
            pace_show_count += 1
            pace_show_max = max(pace_show_max, show_duration)

        pace_ticks += 1
        next_animation_deadline, remaining, late, rebased = next_deadline(
            next_animation_deadline,
            after_render,
            desired_cadence,
            cadence_changed=cadence_changed,
        )

        frame_sleep_duration = 0.0
        frame_sleep_requested = 0.0
        if MATRIX_PRESENTATION_MODE in ("immediate", "auto_refresh"):
            # Modes B/C own the animation cadence in the application. Use an
            # absolute deadline to avoid accumulating render-time drift.
            if remaining > 0:
                pace_late_streak = 0
                frame_sleep_requested = remaining
                sleep_started = time.monotonic()
                _sleep_interruptible(remaining)
                frame_sleep_duration = time.monotonic() - sleep_started
            else:
                pace_late_frames += 1
                pace_late_streak += 1
                pace_max_late_streak = max(pace_max_late_streak, pace_late_streak)
        else:
            # Mode A is the control: preserve the existing relative sleep so
            # its measurements remain directly comparable with issue #66.
            remaining = frame_seconds - (after_render - frame_started)
            if remaining > 0:
                pace_late_streak = 0
                frame_sleep_requested = remaining
                sleep_started = time.monotonic()
                _sleep_interruptible(remaining)
                frame_sleep_duration = time.monotonic() - sleep_started
            else:
                pace_late_frames += 1
                pace_late_streak += 1
                pace_max_late_streak = max(pace_max_late_streak, pace_late_streak)

        # The first scene build ends before the animation timer starts; do not
        # attribute its full render duration to the first paced-frame gap.
        pace_last_show_seconds = (
            0.0 if pace_ticks == 1 and instrument_render else show_duration
        )
        pace_last_sleep_seconds = frame_sleep_duration
        if frame_sleep_requested > 0:
            pace_sleep_requested_total += frame_sleep_requested
            pace_sleep_requested_count += 1
            pace_sleep_requested_max = max(
                pace_sleep_requested_max, frame_sleep_requested
            )
            pace_sleep_actual_total += frame_sleep_duration
            pace_sleep_actual_count += 1
            pace_sleep_actual_max = max(pace_sleep_actual_max, frame_sleep_duration)
            if frame_sleep_duration - frame_sleep_requested > 0.05:
                pace_sleep_overshoots += 1
        report_now = time.monotonic()
        if _report_pace(report_now):
            pace_last_report = report_now
    elif settings.ANIMATE:
        pace_active = False
        pace_last_tick_started = None
        animation_cadence = None
        next_animation_deadline = None
        frame_seconds = settings.FRAME_SECONDS
        remaining = frame_seconds - (time.monotonic() - frame_started)
        if remaining > 0:
            _sleep_interruptible(remaining)
    else:
        pace_active = False
        pace_last_tick_started = None
        animation_cadence = None
        next_animation_deadline = None
        # Static pages must still rotate independently of the network poll.
        # Waking only at the next page/fetch boundary avoids repeatedly
        # rebuilding the complete HUB75 framebuffer, which can show as
        # horizontal flashes on long panel chains.
        duration = max(1.0, float(screen.get("duration_seconds") or 8))
        until_rotation = max(0.05, duration - max(0, phase))
        until_fetch = max(0.05, next_fetch - time.monotonic())
        _sleep_interruptible(min(until_rotation, until_fetch), service_mqtt=True)
