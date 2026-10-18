"""MatrixPortal / Wokwi information-board entrypoint."""

import sys
import time

# Wokwi requires code.py at the project root, while implementation modules are
# grouped by responsibility in the repository. Physical-board staging flattens
# these directories back onto CIRCUITPY, where the extra paths are harmless.
for source_path in ("/hardware/matrixportal/firmware", "/shared", "hardware/matrixportal/firmware", "shared"):
    if source_path not in sys.path:
        sys.path.append(source_path)

from monotonic_clock import elapsed_seconds, ticks_ms

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
from animation_scheduler import (
    earliest_wake_seconds,
    frame_gap_exceeded,
    next_deadline,
)
from matrix_runtime import RuntimeMode, collect_gc_with_state, enter_rail_gc_window
from wifi_isolation_window import WifiIsolationWindow
from screen_client import ClockState, ScreenClient, ScreenRotation
from cron_schedule import cron_matches_local
from mqtt_screens import MqttScreenState
from matrix_config import (
    MATRIX_PRESENTATION_MODE,
    MATRIX_RAIL_PREBUILD_EXPERIMENT,
    MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES,
    MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES,
    MATRIX_REFRESH_FPS,
    MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT,
    MATRIX_STATS_INTERVAL_SECONDS,
    MATRIX_TELEMETRY_ENABLED,
)


if settings.SCREEN_SOURCE not in ("fixture", "api"):
    raise ValueError("SCREEN_SOURCE must be fixture or api")

# The four-panel MatrixPortal installation is operated in static mode.  A
# local settings file may select the backend and network, but cannot re-enable
# the high-frequency animation path that produced scan-line flashes.
if settings.DISPLAY_BACKEND == "matrix":
    settings.ANIMATE = False


steam_train_test = bool(getattr(settings, "STEAM_TRAIN_TEST", False))
steam_train_wifi_isolation = None
if steam_train_test:
    wifi_off_after = float(
        getattr(settings, "STEAM_TRAIN_TEST_WIFI_OFF_AFTER_SECONDS", 0)
    )
    wifi_off_duration = float(
        getattr(settings, "STEAM_TRAIN_TEST_WIFI_OFF_DURATION_SECONDS", 30)
    )
    if wifi_off_after > 0 and wifi_off_duration > 0:
        steam_train_wifi_isolation = WifiIsolationWindow(
            time.monotonic() + wifi_off_after,
            wifi_off_duration,
        )


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
    screens = [
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
    ]
    if steam_train_test:
        screens = screens[:1]
        test_speed = max(1.0, float(getattr(settings, "STEAM_TRAIN_TEST_SPEED", 8)))
        screens[0]["duration_seconds"] = max(2.0, 256.0 / test_speed + 1.0)
        screens[0]["animation_speed"] = test_speed
    return {
        "fetched_at": "2026-09-12T12:00:00Z",
        "screens": screens,
    }


def hardware_safe_screen(screen):
    """Keep hardware-safe screen text without collapsing combined park titles."""
    return screen


display = create(settings)
rotation = ScreenRotation(ticks_per_second=1000)
clock = ClockState()
if steam_train_test:
    import matrix_config

    print(
        "STEAM TRAIN TEST enabled speed_px_s={} cadence_fps={} presentation_preset={} bit_depth={} clock=integer_ms uptime_ms={}".format(
            getattr(settings, "STEAM_TRAIN_TEST_SPEED", 8),
            getattr(settings, "STEAM_TRAIN_TEST_FPS", 8),
            matrix_config.MATRIX_EXPERIMENT_PRESET,
            matrix_config.MATRIX_BIT_DEPTH,
            ticks_ms(),
        )
    )
client = ScreenClient(settings) if settings.SCREEN_SOURCE == "api" and not steam_train_test else None
buttons = None
if settings.DISPLAY_BACKEND == "matrix" and not steam_train_test:
    from button_control import MatrixButtons

    buttons = MatrixButtons()

_pending_button_events = []
_BUTTON_POLL_SECONDS = 0.05
_MQTT_SLEEP_POLL_SECONDS = 0.25
mqtt_screens_changed = False


def _sleep_interruptible(seconds, service_mqtt=False):
    """Sleep without changing render cadence, servicing requested I/O while idle."""
    global mqtt_screens_changed
    seconds = max(0.0, float(seconds or 0))
    if buttons is None and not service_mqtt:
        slice_ms = (
            float(getattr(settings, "STEAM_TRAIN_TEST_SLEEP_SLICE_MS", 0))
            if steam_train_test else 0
        )
        if slice_ms <= 0:
            time.sleep(seconds)
        else:
            deadline = ticks_ms() + int(seconds * 1000)
            sleep_slice = max(0.001, slice_ms / 1000.0)
            while True:
                remaining = (deadline - ticks_ms()) / 1000.0
                if remaining <= 0:
                    break
                time.sleep(min(sleep_slice, remaining))
        return
    deadline = ticks_ms() + int(seconds * 1000)
    next_mqtt_poll = time.monotonic()
    while True:
        remaining = (deadline - ticks_ms()) / 1000.0
        if remaining <= 0:
            return
        time.sleep(min(_BUTTON_POLL_SECONDS, remaining))
        now = time.monotonic()
        epoch_now = _reminder_epoch(now)
        if epoch_now is not None and mqtt_screens.expire(epoch_now):
            rotation.update_sources(rotation.http_screens, mqtt_screens.effective_screens(epoch_now, clock.date_text(now)), ticks_ms())
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
last_maintenance_slot = None
last_visible_screen = None
last_logged_screen_started = None
screen_heap_low_water = None
task_retry_at = 0
prepared_task = None
transport_stale = False
fixture_clock_synced = False
runtime_mode = RuntimeMode()
flash = FlashState(
    # Flash events stay gated until the screen payload enables Flash in the
    # admin control plane. Cycle screens use the independent MQTT source.
    enabled=False,
)
flash_resume = None
flash_started_ticks = None
mqtt = None
mqtt_screens = MqttScreenState(
    getattr(settings, "MQTT_SCREENS_TOPIC", "led/screens/+")
)
last_recycling_date = None


def _reminder_epoch(now):
    epoch_now = clock.epoch(now)
    if epoch_now is None:
        system_epoch = time.time()
        epoch_now = system_epoch if system_epoch >= 1000000000 else None
    return epoch_now


def _flash_started(now):
    global flash_resume, last_render_key, flash_started_ticks
    flash_started_ticks = ticks_ms()
    if flash_resume is None:
        flash_resume = rotation.freeze(ticks_ms())
    last_render_key = None
    print("FLASH START id={}".format(flash.event["id"]))


def _service_reminder_clock(now):
    if not flash.enabled or flash.pending is None:
        return False
    if flash.tick(now, _reminder_epoch(now)):
        _flash_started(now)
        return True
    return False


if settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL and not steam_train_test:
    from mqtt_client import FlashMqttClient

    def receive_mqtt(topic, payload):
        global mqtt_screens_changed
        now = time.monotonic()
        assistant_topic = getattr(
            settings, "MQTT_ASSISTANT_RESPONSE_TOPIC",
            "led/flash/assistant-response",
        )
        if topic in (settings.MQTT_TOPIC, assistant_topic):
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
            rotation.update_sources(rotation.http_screens, mqtt_screens.effective_screens(epoch_now, clock.date_text(now)), ticks_ms())
            mqtt_screens_changed = True

    mqtt = FlashMqttClient(
        settings,
        receive_mqtt,
        startup_delay_seconds=settings.MQTT_STARTUP_DELAY_SECONDS,
    )
rendered_diagnostic_index = None
last_render_key = None
last_logged_screen_key = None

# Todoist frame-pacing diagnostics are reset whenever the board enters the
# Todoist screen, so each serial summary represents one comparable run.
pace_active = False
pace_started = 0.0
pace_last_report = 0.0
pace_ticks = 0
pace_frame_work_overrun_max = 0.0
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

# Low-volume work-attribution telemetry for soak runs. These counters are
# reported with FRAME PACE and deliberately avoid per-frame serial output.
telemetry_started = ticks_ms()
telemetry_fetches = 0
telemetry_fetch_failures = 0
telemetry_fetch_total = 0.0
telemetry_fetch_max = 0.0
telemetry_scene_renders = 0
telemetry_scene_render_total = 0.0
telemetry_scene_render_max = 0.0
telemetry_scene_render_over_budget = 0
animation_cadence = None
animation_deadline = None
rail_gc_suspended = False
rail_gc_pause_active = False
rail_gc_last_pressure_collect = None
sun_gc_completed_key = None
rail_prebuild_last_slot = None
previous_rail_frame_started = None
last_rail_sleep_requested_ms = 0.0
last_rail_preframe_ms = 0.0


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


def _memory_allocated():
    if gc is None or not hasattr(gc, "mem_alloc"):
        return None
    return gc.mem_alloc()


HEAP_DIAGNOSTICS_ENABLED = True
RAIL_GC_MIN_FREE_BYTES = 768 * 1024
heap_trace_started = ticks_ms()
heap_trace_last_report = heap_trace_started
heap_trace_low_water = _memory_free()
heap_trace_samples = 0


def _display_phase(screen, phase):
    if screen.get("display_group") == "static_feeds" or screen.get("kind") in ("dad_joke", "random_fact", "insult_of_hour", "quotes", "today"):
        return phase
    if screen.get("kind") == "flash":
        return phase
    if settings.ANIMATE:
        return phase
    if _smooth_departures(screen):
        return phase
    if _smooth_steam_train(screen):
        return phase
    if _smooth_bus_intro(screen):
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


def _smooth_today(screen):
    return settings.DISPLAY_BACKEND == "matrix" and screen.get("kind") == "today"


def _smooth_steam_train(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "steam_train_intro"
    )


def _smooth_bus_intro(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "bus_intro"
    )


def _smooth_bin_collection(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "bin_collection"
    )


def _report_pace(now):
    if not pace_active or elapsed_seconds(pace_last_report, now) < MATRIX_STATS_INTERVAL_SECONDS:
        return False
    elapsed = max(0.001, elapsed_seconds(pace_started, now))
    telemetry_elapsed = max(0.001, elapsed_seconds(telemetry_started, now))
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
        "slept_frames={} no_sleep_frames={} frame_work_overrun_max={:.4f} "
        "fetches={} fetch_failures={} fetch_avg={:.3f} fetch_max={:.3f} "
        "scene_renders={} render_avg={:.3f} render_max={:.3f} "
        "render_over_budget={} telemetry_elapsed={:.1f}".format(
            MATRIX_PRESENTATION_MODE,
            animation_cadence or MATRIX_REFRESH_FPS,
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
            pace_sleep_requested_count,
            max(0, pace_ticks - pace_sleep_requested_count),
            pace_frame_work_overrun_max,
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


def _apply_flash_config(payload, now=None):
    config = payload.get("flash") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        return
    # The public screen payload carries only non-secret operational settings.
    # Both board-local flags and this runtime setting gate flash events.
    runtime_enabled = (
        settings.MQTT_ENABLED
        and settings.MQTT_ENABLE_EXPERIMENTAL
        and config.get("enabled", False)
    )
    expression = config.get("cron_schedule") or ""
    if expression:
        try:
            local_date = clock.date_text(now)
            local_time = clock.text(now)
            year, month, day = (int(part) for part in local_date.split("-"))
            hour, minute = (int(part) for part in local_time.split(":"))
            runtime_enabled = runtime_enabled and cron_matches_local(
                expression, year, month, day, hour, minute
            )
        except (AttributeError, TypeError, ValueError, IndexError):
            runtime_enabled = False
    flash.configure(
        enabled=runtime_enabled,
        duration_seconds=config.get("screen_duration_seconds"),
    )


while True:
    now = time.monotonic()
    loop_started = ticks_ms()
    if HEAP_DIAGNOSTICS_ENABLED:
        heap_free_now = _memory_free()
        if heap_free_now is not None:
            heap_trace_samples += 1
            if heap_trace_low_water is None or heap_free_now < heap_trace_low_water:
                heap_trace_low_water = heap_free_now
            if screen_heap_low_water is None or heap_free_now < screen_heap_low_water:
                screen_heap_low_water = heap_free_now
        if elapsed_seconds(heap_trace_last_report, loop_started) >= MATRIX_STATS_INTERVAL_SECONDS:
            print(
                "HEAP TRACE elapsed={:.1f}s free={} allocated={} low_water={} samples={} "
                "last_screen={} rail_gc_suspended={} rail_gc_pause={}".format(
                    elapsed_seconds(heap_trace_started, loop_started),
                    heap_free_now,
                    _memory_allocated(),
                    heap_trace_low_water,
                    heap_trace_samples,
                    last_visible_screen,
                    rail_gc_suspended,
                    rail_gc_pause_active,
                )
            )
            heap_trace_last_report = loop_started
    if steam_train_wifi_isolation is not None:
        steam_train_wifi_isolation.update(now)
    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    _service_reminder_clock(now)
    stage_durations = (
        {"reminder": elapsed_seconds(stage_started)}
        if MATRIX_TELEMETRY_ENABLED else None
    )
    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    if mqtt is not None:
        mqtt_animation_active = False
        mqtt_allow_connect = True
        if rotation.screens and not flash.active(now):
            mqtt_screen, mqtt_phase = rotation.current(ticks_ms())
            mqtt_animation_active = display.animation_active(mqtt_screen, mqtt_phase)
            mqtt_allow_connect = not mqtt_animation_active
        # MiniMQTT's nominal socket timeout does not bound the complete
        # CircuitPython/Wi-Fi path. Do not interrupt visible animation with
        # keepalive/reconnect work; service the connection in an idle window.
        if not mqtt_animation_active:
            mqtt.poll(now, allow_connect=mqtt_allow_connect)
    if MATRIX_TELEMETRY_ENABLED:
        stage_durations["mqtt"] = elapsed_seconds(stage_started)
    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    if buttons is not None:
        events = buttons.poll(now)
        if events:
            _pending_button_events.extend(events)
        button_events = _pending_button_events
    else:
        button_events = ()
    if MATRIX_TELEMETRY_ENABLED:
        stage_durations["buttons"] = elapsed_seconds(stage_started)
    for event in button_events:
        if runtime_mode.mode == "normal" and event in ("up", "down"):
            display.adjust_brightness(1 if event == "up" else -1)
            continue
        if runtime_mode.handle(event, rotation, ticks_ms()):
            rendered_diagnostic_index = None
    if buttons is not None:
        _pending_button_events.clear()

    if runtime_mode.mode == "diagnostic":
        if rendered_diagnostic_index != runtime_mode.diagnostic_index:
            name, color = runtime_mode.diagnostic()
            print("DIAGNOSTIC", name)
            display.show_diagnostic(color)
            rendered_diagnostic_index = runtime_mode.diagnostic_index
        _sleep_interruptible(settings.FRAME_SECONDS)
        continue

    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    maintenance_resume = None
    maintenance_active = False
    animation_capable_screen = False
    candidate, candidate_phase = rotation.current(ticks_ms())
    fetch_due = ticks_ms() >= next_fetch
    boundary = last_visible_screen != candidate.get("id")
    task_unready = (candidate.get("kind") == "calendar_agenda"
                    and candidate.get("source") == "todoist"
                    and not display.tasks_ready(candidate, clock.date_text(now))
                    and ticks_ms() >= task_retry_at)
    # Weather is grouped by the scheduler, while the train and SL7 bus
    # introductions must transition directly into their departures boards.
    paired_followup = rotation.is_paired_transition(last_visible_screen, candidate)
    if (rotation.screens and not steam_train_test and not flash.active(now)
            and boundary and not paired_followup and (fetch_due or task_unready)
            and not rotation.is_maintenance_screen(candidate)):
        rotation.maintenance_slot(ticks_ms())
        candidate, candidate_phase = rotation.current(ticks_ms())
    maintenance_visible = rotation.is_static(candidate)
    if not rotation.screens:
        # Do not make the startup placeholder look like the disabled standalone
        # Today screen or the Next 24H forecast. The feed may still be loading.
        candidate = {"id": "startup-loading", "kind": "startup",
                     "title": "STARTING", "empty_state": "LOADING SCREENS",
                     "duration_seconds": 8}
        candidate_phase = 0
        maintenance_visible = True
    slot_key = (rotation.cycle_number, candidate.get("id"), rotation.started_at)
    if maintenance_visible and not steam_train_test and not flash.active(now):
        maintenance_active = True
        display.show(candidate, clock.text(now), clock_date=clock.date_text(now), phase=candidate_phase, now_epoch=clock.epoch(now))
        if rotation.screens:
            maintenance_resume = rotation.freeze(ticks_ms())
        if slot_key != last_maintenance_slot:
            if gc is not None and hasattr(gc, "collect"):
                gc.collect()
        if client is not None and fetch_due:
            # Acknowledge completed items only; retries stay in static windows.
            for key, url in list(rotation.pending_refresh.items()):
                if not url:
                    continue
                try:
                    client.acknowledge(url)
                    del rotation.pending_refresh[key]
                except Exception:
                    print("Static content acknowledgement deferred")
                    break
    # The browser simulator refreshes the renderer-neutral payload every
    # 30 seconds. Keep the physical board's departures data on the same
    # cadence even when that interval expires inside the paired train/rail
    # block; waiting for the next static maintenance page can leave one
    # timetable snapshot on the board for the entire 90-second rail screen.
    rail_refresh_visible = candidate.get("kind") in ("steam_train_intro", "rail_combined")
    should_fetch = (
        fetch_due
        and (maintenance_visible or rail_refresh_visible
             or (steam_train_test and not rotation.screens))
        and not flash.active(now)
    )
    if MATRIX_TELEMETRY_ENABLED:
        stage_durations["fetch_decision"] = elapsed_seconds(stage_started)
    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    if should_fetch:
        fetch_gc_restore = gc is not None and rail_gc_suspended
        if fetch_gc_restore:
            # The rail renderer disables automatic collection during motion.
            # A network refresh allocates a large payload, so run it with GC
            # enabled and restore the rail setting after the fetch completes.
            try:
                collect_gc_with_state(gc, enabled_after=True)
            except Exception as error:
                print("RAIL GC FETCH WINDOW FAILED; deferring feed refresh:", error)
                _sleep_interruptible(settings.FRAME_SECONDS)
                continue
        fetch_started = time.monotonic()
        fetch_started_ticks = ticks_ms()
        # Screen API calls are synchronous and can take multiple animation
        # frames. Freeze the selected screen phase for that interval so the
        # first post-fetch frame resumes where the last one left off.
        fetch_resume = None
        if rotation.screens and not flash.active(fetch_started):
            fetch_resume = rotation.freeze(ticks_ms())
        try:
            print("FETCH START")
            payload = fixture_payload(now) if client is None else client.fetch()
            screens = payload.get("screens")
            prepare_intro = getattr(display, "prepare_intro", None)
            if callable(prepare_intro):
                for intro in screens or ():
                    if (not isinstance(intro, dict)
                            or intro.get("kind") not in ("steam_train_intro", "bus_intro")):
                        continue
                    try:
                        if prepare_intro(intro):
                            print(
                                "INTRO SCENE PREPARED id={} kind={} heap_free={}".format(
                                    intro.get("id"), intro.get("kind"), _memory_free()
                                )
                            )
                    except Exception as error:
                        # Keep fetched screens usable if off-screen preparation
                        # cannot allocate; the renderer retains its normal fallback.
                        print("Intro scene preparation deferred:", error)
            display_config = payload.get("display")
            if (
                isinstance(display_config, dict)
                and "brightness_percent" in display_config
                and hasattr(display, "set_brightness_percent")
            ):
                display.set_brightness_percent(display_config["brightness_percent"])
            fetch_completed = time.monotonic()
            fetch_duration = elapsed_seconds(fetch_started_ticks)
            telemetry_fetches += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("FETCH OK screens={} duration={:.3f}".format(len(screens or []), fetch_duration))
            for candidate in screens or ():
                if (not isinstance(candidate, dict)
                        or candidate.get("id") != "departures"
                        or candidate.get("kind") != "rail_combined"):
                    continue
                service_times = []
                for service in candidate.get("services") or ():
                    if isinstance(service, dict):
                        service_times.append(str(service.get("time") or "--:--"))
                    if len(service_times) >= 3:
                        break
                print("DEPARTURE FEED stale={} services={} next_times={}".format(
                    bool(candidate.get("stale")),
                    len(candidate.get("services") or ()),
                    ",".join(service_times),
                ))
                break
            fetched_at = payload.get("clock_at") or payload.get("fetched_at")
            if fetched_at and (client is not None or not fixture_clock_synced):
                clock.sync(fetched_at, fetch_completed)
                fixture_clock_synced = True
            rotation.set_schedule_time(clock.date_text(fetch_completed), clock.text(fetch_completed))
            mqtt_screens.configure_recycling(payload.get("recycling"))
            epoch_now = _reminder_epoch(fetch_completed)
            last_recycling_date = clock.date_text(fetch_completed)
            rotation.update_sources(
                screens,
                mqtt_screens.effective_screens(epoch_now, last_recycling_date)
                if epoch_now is not None else [],
                ticks_ms(),
            )
            if fetch_resume is not None:
                rotation.resume(ticks_ms(), fetch_resume[0], fetch_resume[1])
            _apply_flash_config(payload, fetch_completed)
            transport_stale = False
        except Exception as error:
            fetch_completed = time.monotonic()
            fetch_duration = elapsed_seconds(fetch_started_ticks)
            telemetry_fetches += 1
            telemetry_fetch_failures += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            print("Screen fetch failed duration={:.3f}:".format(fetch_duration), error)
            transport_stale = bool(rotation.screens)
            if fetch_resume is not None:
                rotation.resume(ticks_ms(), fetch_resume[0], fetch_resume[1])
        finally:
            if fetch_gc_restore:
                try:
                    gc.disable()
                except Exception as error:
                    print("RAIL GC FETCH WINDOW RESTORE FAILED:", error)
        now = fetch_completed
        next_fetch = ticks_ms() + int(settings.POLL_SECONDS * 1000)
        if (
            animation_capable_screen
            and hasattr(display, "note_fetch_on_animation_capable_screen")
        ):
            display.note_fetch_on_animation_capable_screen()
        if MATRIX_TELEMETRY_ENABLED:
            stage_durations["fetch"] = elapsed_seconds(stage_started)

    if maintenance_active:
        now = time.monotonic()
        if ticks_ms() >= task_retry_at:
            for task in rotation.http_screens:
                if task.get("kind") == "calendar_agenda" and task.get("source") == "todoist":
                    try:
                        display.prepare_tasks(task, clock.text(now), clock.date_text(now))
                        prepared_task = task
                    except Exception:
                        task_retry_at = ticks_ms() + 30000
                        print("Task preparation deferred; retaining last usable scene")
                    break
        if maintenance_resume is not None:
            rotation.resume(ticks_ms(), maintenance_resume[0], maintenance_resume[1])
        last_maintenance_slot = (rotation.cycle_number, candidate.get("id"), rotation.started_at)

    if (MATRIX_RAIL_PREBUILD_EXPERIMENT and maintenance_active
            and settings.DISPLAY_BACKEND == "matrix" and not flash.active(now)):
        upcoming_rail = rotation.next_paired_rail_screen()
        prebuild_key = (
            rotation.cycle_number,
            candidate.get("id"),
            rotation.started_at,
            upcoming_rail.get("id") if upcoming_rail else None,
            id(upcoming_rail) if upcoming_rail else None,
        )
        if prebuild_key != rail_prebuild_last_slot:
            rail_prebuild_last_slot = prebuild_key
            print(
                "RAIL PREBUILD WINDOW cycle={} maintenance_id={} upcoming_id={} display_type={} prepare_available={}".format(
                    rotation.cycle_number,
                    candidate.get("id"),
                    upcoming_rail.get("id") if upcoming_rail else None,
                    type(display).__name__,
                    hasattr(display, "prepare_rail_scene"),
                )
            )
            if upcoming_rail is None:
                print("RAIL PREBUILD SKIP reason=no_future_pair")
                if hasattr(display, "discard_prepared_rail_scene"):
                    display.discard_prepared_rail_scene()
            elif hasattr(display, "prepare_rail_scene"):
                try:
                    display.prepare_rail_scene(
                        upcoming_rail,
                        clock.text(now),
                        MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES,
                        MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES,
                    )
                except Exception as error:
                    # On-demand construction remains the transition fallback.
                    print("RAIL PREBUILD FAILED; using on-demand build:", error)
            else:
                print("RAIL PREBUILD SKIP reason=renderer_unavailable")

    epoch_now = _reminder_epoch(now)
    recycling_date = clock.date_text(now)
    expired_mqtt = mqtt_screens.expire(epoch_now) if epoch_now is not None else []
    if epoch_now is not None and (expired_mqtt or recycling_date != last_recycling_date):
        rotation.update_sources(
            rotation.http_screens,
            mqtt_screens.effective_screens(epoch_now, recycling_date),
            ticks_ms(),
        )
        mqtt_screens_changed = True
    last_recycling_date = recycling_date

    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    if flash.active(now):
        screen, phase = flash.screen(), elapsed_seconds(flash_started_ticks)
    else:
        if flash.event is not None:
            flash.clear()
            if flash_resume is not None:
                rotation.resume(ticks_ms(), flash_resume[0], flash_resume[1])
                flash_resume = None
            last_render_key = None
            print("FLASH END")
        rotation.set_schedule_time(clock.date_text(now), clock.text(now))
        screen, phase = rotation.current(ticks_ms())
    if MATRIX_TELEMETRY_ENABLED:
        stage_durations["screen_select"] = elapsed_seconds(stage_started)
    screen = hardware_safe_screen(screen)
    if transport_stale and any(candidate is screen for candidate in rotation.http_screens):
        screen = dict(screen)
        screen["stale"] = True
        weather = screen.get("weather")
        if isinstance(weather, dict):
            weather = dict(weather)
            weather["stale"] = True
            screen["weather"] = weather
    if settings.DISPLAY_BACKEND == "matrix" and screen.get("kind") == "weather_sun":
        sun_gc_key = (screen.get("id"), rotation.cycle_number, rotation.started_at)
        if (sun_gc_completed_key != sun_gc_key
                and not display.animation_active(screen, phase)):
            collect = getattr(gc, "collect", None) if gc is not None else None
            if collect is not None:
                heap_before_gc = _memory_free()
                collect()
                sun_gc_completed_key = sun_gc_key
                if HEAP_DIAGNOSTICS_ENABLED:
                    print("SUN GC END reason=animation_complete heap_free_before={} heap_free_after={}".format(
                        heap_before_gc, _memory_free()
                    ))
    else:
        sun_gc_completed_key = None
    rail_screen = (
        settings.DISPLAY_BACKEND == "matrix"
        and isinstance(screen, dict)
        and screen.get("kind") == "rail_combined"
    )
    if gc is not None and rail_screen and not rail_gc_suspended:
        disable = getattr(gc, "disable", None)
        enable = getattr(gc, "enable", None)
        scene_ready = (
            hasattr(display, "rail_scene_ready")
            and display.rail_scene_ready(screen)
        )
        cold_build = not scene_ready
        prebuilt_scene = (
            hasattr(display, "rail_scene_prebuilt")
            and display.rail_scene_prebuilt(screen)
        )
        allow_build_gc = (
            MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT
            and cold_build
            and enable is not None
        )
        if cold_build and hasattr(display, "discard_prepared_rail_scene"):
            # Drop an obsolete hidden generation before the entry collection
            # or automatic-GC build so old and replacement scenes do not peak
            # together in the heap.
            display.discard_prepared_rail_scene(reason="on_demand_rebuild")
        gc_entry_started = ticks_ms()
        entry_collect = not allow_build_gc and not prebuilt_scene
        try:
            entry_collect = enter_rail_gc_window(
                gc,
                allow_during_build=allow_build_gc,
                collect_at_entry=entry_collect,
            )
        except Exception as error:
            if disable is not None:
                try:
                    disable()
                except Exception:
                    pass
            print("RAIL GC ENTRY FAILED; continuing with restored collector state:", error)
        gc_entry_duration = elapsed_seconds(gc_entry_started)
        rail_gc_suspended = True
        rail_gc_pause_active = False
        if HEAP_DIAGNOSTICS_ENABLED:
            print(
                "RAIL GC ENTER reason={} auto_gc_during_build={} entry_collect={} duration={:.3f}s heap_free={} heap_allocated={}".format(
                    "cold_scene_build" if cold_build else (
                        "prepared_scene" if prebuilt_scene else "scene_ready"
                    ),
                    allow_build_gc,
                    entry_collect,
                    gc_entry_duration,
                    _memory_free(),
                    _memory_allocated(),
                )
            )
    elif gc is not None and rail_screen and rail_gc_suspended:
        pause_now = (
            hasattr(display, "rail_gc_safe_to_collect")
            and display.rail_gc_safe_to_collect(screen, phase)
        )
        heap_before_gc = _memory_free()
        pressure_cooldown_elapsed = (
            rail_gc_last_pressure_collect is None
            or elapsed_seconds(rail_gc_last_pressure_collect, ticks_ms()) >= 5
        )
        pressure_due = (
            heap_before_gc is not None
            and heap_before_gc < RAIL_GC_MIN_FREE_BYTES
            and pressure_cooldown_elapsed
        )
        if (pause_now and not rail_gc_pause_active) or pressure_due:
            gc_reason = (
                "calling_end_pause"
                if pause_now
                else "heap_pressure_during_motion"
            )
            gc_started = ticks_ms()
            if HEAP_DIAGNOSTICS_ENABLED:
                print(
                    "RAIL GC START reason={} motion_active={} heap_free={}".format(
                        gc_reason, not pause_now, heap_before_gc
                    )
                )
            try:
                collect_gc_with_state(gc, enabled_after=False)
            except Exception as error:
                print("RAIL GC FAILED reason={} collector_state=disabled:".format(gc_reason), error)
            gc_duration = elapsed_seconds(gc_started)
            if pressure_due:
                rail_gc_last_pressure_collect = ticks_ms()
            if HEAP_DIAGNOSTICS_ENABLED:
                print(
                    "RAIL GC END reason={} duration={:.3f}s heap_free_before={} heap_free_after={}".format(
                        gc_reason, gc_duration, heap_before_gc, _memory_free()
                    )
                )
        rail_gc_pause_active = pause_now
    elif gc is not None and not rail_screen and rail_gc_suspended:
        gc_exit_started = ticks_ms()
        try:
            collect_gc_with_state(gc, enabled_after=True)
        except Exception as error:
            print("RAIL GC EXIT FAILED reason=leaving_rail collector_state=enabled:", error)
        finally:
            rail_gc_suspended = False
            rail_gc_pause_active = False
        if HEAP_DIAGNOSTICS_ENABLED:
            print("RAIL GC EXIT duration={:.3f}s heap_free={}".format(
                elapsed_seconds(gc_exit_started), _memory_free()
            ))
    if (screen.get("kind") == "calendar_agenda" and screen.get("source") == "todoist"
            and not display.tasks_ready(screen, clock.date_text(now))):
        # Never trigger an unexpected heavy build after entering an animated
        # task slot. Failed preparation is retried in a later static window.
        if prepared_task is not None and display.tasks_ready(prepared_task, clock.date_text(now)):
            screen = prepared_task
        else:
            screen = {"id": screen.get("id"), "kind": "message",
                      "title": "Tasks unavailable", "empty_state": "Tasks unavailable",
                      "duration_seconds": screen.get("duration_seconds", 8), "stale": True}
    frame_started = ticks_ms()
    current_preframe_ms = elapsed_seconds(loop_started, frame_started) * 1000.0
    rail_timing_before_show = None
    if isinstance(screen, dict) and screen.get("kind") == "rail_combined":
        rail_timing_before_show = (
            getattr(display, "_last_rail_update_seconds", 0.0),
            getattr(display, "_last_rail_refresh_seconds", 0.0),
            getattr(display, "_last_rail_heap_gain", None),
            last_rail_sleep_requested_ms,
            last_rail_preframe_ms,
        )
        last_rail_preframe_ms = current_preframe_ms
    else:
        last_rail_sleep_requested_ms = 0.0
        last_rail_preframe_ms = 0.0
    preframe_duration = current_preframe_ms / 1000.0 if MATRIX_TELEMETRY_ENABLED else 0.0
    render_key = (
        (screen.get("id"), screen.get("kind"))
        if isinstance(screen, dict)
        else (None, None)
    )
    log_screen_change = render_key != last_logged_screen_key
    instrument_render = MATRIX_TELEMETRY_ENABLED and render_key != last_render_key
    if HEAP_DIAGNOSTICS_ENABLED and log_screen_change and last_logged_screen_key is not None:
        screen_ended = ticks_ms()
        print(
            "SCREEN END id={} kind={} duration={:.1f}s heap_free={} allocated={} low_water={}".format(
                last_logged_screen_key[0],
                last_logged_screen_key[1],
                elapsed_seconds(last_logged_screen_started, screen_ended)
                if last_logged_screen_started is not None else 0.0,
                _memory_free(),
                _memory_allocated(),
                screen_heap_low_water,
            )
        )
        screen_heap_low_water = _memory_free()
    if log_screen_change:
        print(
            "SCREEN START id={} kind={} title={} heap_free={}".format(
                render_key[0], render_key[1], screen.get("title", ""), _memory_free()
            )
        )
    if instrument_render:
        render_started = ticks_ms()
        memory_before = _memory_free()
        root_before = _matrix_root_token()
        print(
            "RENDER START id={} kind={} index={} phase={} mode={} mem={}".format(
                render_key[0], render_key[1], rotation.index, phase, runtime_mode.mode, memory_before
            )
        )
    show_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    display.show(
        screen,
        clock.text(now),
        clock_date=clock.date_text(now),
        phase=_display_phase(screen, phase),
        now_epoch=clock.epoch(now),
    )
    show_duration = (
        elapsed_seconds(show_started) if MATRIX_TELEMETRY_ENABLED else 0.0
    )
    if instrument_render:
        memory_after = _memory_free()
        root_after = _matrix_root_token()
        render_duration = elapsed_seconds(render_started)
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
    if log_screen_change:
        base_display = getattr(display, "base", display)
        hardware_display = getattr(base_display, "display", None)
        root_group = getattr(hardware_display, "root_group", None)
        brightness = getattr(base_display, "brightness_percent", None)
        print(
            "SCREEN OK id={} kind={} heap_free={} root_set={} refresh={} brightness={}".format(
                render_key[0], render_key[1], _memory_free(), root_group is not None,
                getattr(base_display, "_last_present_refresh", None), brightness,
            )
        )
        last_logged_screen_key = render_key
        last_logged_screen_started = ticks_ms()
        screen_heap_low_water = _memory_free()
    last_visible_screen = screen.get("id")
    mqtt_screens_changed = False
    smooth_animation = (
        (settings.DISPLAY_BACKEND == "matrix" and screen.get("kind") == "flash")
        or _smooth_todoist(screen)
        or _smooth_departures(screen)
        or _smooth_queue(screen)
        or _smooth_steam_train(screen)
        or _smooth_bus_intro(screen)
        or _smooth_sun_weather(screen)
        or _smooth_today(screen)
        or _smooth_bin_collection(screen)
    )
    if smooth_animation:
        desired_cadence = display.animation_cadence(screen, phase)
        if isinstance(screen, dict) and screen.get("kind") == "rail_combined":
            if desired_cadence > 0:
                if frame_gap_exceeded(previous_rail_frame_started, frame_started):
                    (
                        previous_update,
                        previous_refresh,
                        previous_heap_gain,
                        previous_sleep_requested_ms,
                        previous_preframe_ms,
                    ) = (
                        rail_timing_before_show
                        if rail_timing_before_show is not None
                        else (0.0, 0.0, None, 0.0, 0.0)
                    )
                    gap_ms = frame_started - previous_rail_frame_started
                    preframe_ms = elapsed_seconds(loop_started, frame_started) * 1000.0
                    update_ms = previous_update * 1000.0
                    refresh_ms = previous_refresh * 1000.0
                    other_ms = (
                        gap_ms
                        - preframe_ms
                        - update_ms
                        - refresh_ms
                        - previous_sleep_requested_ms
                        - previous_preframe_ms
                    )
                    print(
                        "RAIL FRAME GAP gap_ms={} preframe_ms={:.1f} "
                        "last_preframe_ms={:.1f} "
                        "last_update_ms={:.1f} last_refresh_ms={:.1f} "
                        "sleep_req_ms={:.1f} other_ms={:.1f} "
                        "last_heap_gain={} phase={:.3f}".format(
                            gap_ms,
                            preframe_ms,
                            previous_preframe_ms,
                            update_ms,
                            refresh_ms,
                            previous_sleep_requested_ms,
                            other_ms,
                            previous_heap_gain,
                            phase,
                        )
                    )
                previous_rail_frame_started = frame_started
            else:
                previous_rail_frame_started = None
        else:
            previous_rail_frame_started = None
        if desired_cadence <= 0:
            pace_active = False
            pace_last_tick_started = None
            animation_cadence = None
            animation_deadline = None
            boundary_sleep = display.animation_sleep_seconds(screen, phase)
            duration = max(1.0, float(screen.get("duration_seconds") or 8))
            until_rotation = max(0.05, duration - max(0, phase))
            until_fetch = max(0.05, (next_fetch - ticks_ms()) / 1000.0)
            _sleep_interruptible(
                earliest_wake_seconds(until_rotation, until_fetch, boundary_sleep),
                service_mqtt=True,
            )
            continue
        cadence_changed = animation_cadence != desired_cadence
        if cadence_changed:
            was_active = pace_active
            animation_cadence = desired_cadence
            if was_active and hasattr(display, "note_cadence_switch"):
                display.note_cadence_switch()
        frame_seconds = 1.0 / desired_cadence
        after_render = ticks_ms()
        if not MATRIX_TELEMETRY_ENABLED:
            animation_deadline, remaining, _, _ = next_deadline(
                animation_deadline, ticks_ms(), desired_cadence, cadence_changed, 1000
            )
            last_rail_sleep_requested_ms = (
                max(0.0, remaining * 1000.0)
                if isinstance(screen, dict) and screen.get("kind") == "rail_combined"
                else 0.0
            )
            if remaining > 0:
                _sleep_interruptible(remaining)
            continue
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
            pace_frame_work_overrun_max = 0.0
            pace_show_total = 0.0
            pace_show_count = 0
            pace_show_max = 0.0
            if not instrument_render:
                pace_show_total += show_duration
                pace_show_count += 1
                pace_show_max = max(pace_show_max, show_duration)
        else:
            if pace_last_tick_started is not None:
                tick_interval = elapsed_seconds(pace_last_tick_started, frame_started)
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
        frame_work_duration = elapsed_seconds(frame_started, after_render)
        pace_frame_work_overrun_max = max(
            pace_frame_work_overrun_max,
            max(0.0, frame_work_duration - frame_seconds),
        )

        frame_sleep_duration = 0.0
        frame_sleep_requested = 0.0
        # Include telemetry/bookkeeping in the frame budget. Integer deadlines
        # avoid cumulative overhead drift; overdue deadlines rebase so there
        # is no burst of stale catch-up frames after a blocking operation.
        animation_deadline, remaining, _, _ = next_deadline(
            animation_deadline, ticks_ms(), desired_cadence, cadence_changed, 1000
        )
        if remaining > 0:
            last_rail_sleep_requested_ms = (
                frame_sleep_requested * 1000.0
                if isinstance(screen, dict) and screen.get("kind") == "rail_combined"
                else 0.0
            )
            pace_late_streak = 0
            frame_sleep_requested = remaining
            sleep_started = ticks_ms()
            _sleep_interruptible(remaining)
            frame_sleep_duration = elapsed_seconds(sleep_started)
        else:
            last_rail_sleep_requested_ms = 0.0
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
        report_now = ticks_ms()
        if _report_pace(report_now):
            pace_last_report = report_now
    elif settings.ANIMATE:
        previous_rail_frame_started = None
        pace_active = False
        pace_last_tick_started = None
        animation_cadence = None
        animation_deadline = None
        frame_seconds = settings.FRAME_SECONDS
        remaining = frame_seconds - elapsed_seconds(frame_started)
        if remaining > 0:
            _sleep_interruptible(remaining)
    else:
        previous_rail_frame_started = None
        pace_active = False
        pace_last_tick_started = None
        animation_cadence = None
        animation_deadline = None
        # Static pages must still rotate independently of the network poll.
        # Waking only at the next page/fetch boundary avoids repeatedly
        # rebuilding the complete HUB75 framebuffer, which can show as
        # horizontal flashes on long panel chains.
        duration = max(1.0, float(screen.get("duration_seconds") or 8))
        until_rotation = max(0.05, duration - max(0, phase))
        until_fetch = max(0.05, (next_fetch - ticks_ms()) / 1000.0)
        boundary_sleep = display.animation_sleep_seconds(screen, phase)
        _sleep_interruptible(earliest_wake_seconds(until_rotation, until_fetch, boundary_sleep), service_mqtt=True)
