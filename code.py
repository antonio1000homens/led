"""MatrixPortal / Wokwi information-board entrypoint."""

import json
import os
import sys
import time

# Wokwi requires code.py at the project root, while implementation modules are
# grouped by responsibility in the repository. Physical-board staging flattens
# these directories back onto CIRCUITPY, where the extra paths are harmless.
for source_path in ("/hardware/matrixportal/firmware", "/shared", "hardware/matrixportal/firmware", "shared"):
    if source_path not in sys.path:
        sys.path.append(source_path)

from monotonic_clock import elapsed_seconds, ticks_ms
from board_health import BoardHealth, safe_snapshot_timestamp

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
from matrix_runtime import (
    RuntimeMode, collect_gc_with_state, enter_rail_gc_window,
    football_gc_safe_to_collect,
    christmas_gc_action, enter_christmas_gc_window,
    leave_christmas_gc_window, prepare_christmas_scene_gc,
)
from wifi_isolation_window import WifiIsolationWindow
from screen_client import ClockState, ScreenClient, ScreenRotation, attach_shared_weather
from christmas_tracker import with_christmas_tracker
from cron_schedule import cron_matches_local
from mqtt_screens import MqttScreenState, recycling_policy
from football_screens import FootballPresentationQueue, FootballScreenState
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
mqtt_screens_update_pending = False


def _apply_pending_mqtt_screen_updates(now):
    """Rebuild after a batch, outside the departures GC-suspended window."""
    global mqtt_screens_update_pending
    if not mqtt_screens_update_pending or rail_gc_suspended:
        return False
    epoch_now = _reminder_epoch(now)
    rotation.update_sources(
        rotation.http_screens,
        _effective_mqtt_screens(epoch_now),
        ticks_ms(),
    )
    mqtt_screens_update_pending = False
    return True


def _mqtt_connection_allowed(now):
    """Only start slow MQTT handshakes on the loading or a static page."""
    if not rotation.screens or flash.active(now):
        return False
    screen, phase = rotation.current(ticks_ms())
    return (
        rotation.is_maintenance_screen(screen)
        and not display.animation_active(screen, phase)
    )


def _sleep_interruptible(seconds, service_mqtt=False):
    """Sleep without changing render cadence, servicing requested I/O while idle."""
    global mqtt_screens_changed, mqtt_screens_update_pending
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
            mqtt_screens_changed = True
            mqtt_screens_update_pending = True
            return
        if service_mqtt and _service_reminder_clock(now):
            return
        if service_mqtt and mqtt is not None and now >= next_mqtt_poll:
            mqtt.poll(now, allow_connect=_mqtt_connection_allowed(now))
            _apply_pending_mqtt_screen_updates(now)
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
last_rotation_state_log = None
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
try:
    _session_suffix = os.urandom(4).hex()
except (AttributeError, NotImplementedError):
    _session_suffix = str(int(time.monotonic() * 1000))
board_health = BoardHealth(
    _session_suffix,
    getattr(settings, "FIRMWARE_REVISION", "led-health-v1"),
    getattr(settings, "BOARD_ID", "matrixportal-s3"),
) if getattr(settings, "MQTT_BOARD_TELEMETRY_ENABLED", False) else None


def _publish_board_health(now, force=False):
    if mqtt is None or board_health is None:
        return
    uptime = time.monotonic()
    if not force and not board_health.due(uptime):
        return
    try:
        payload = board_health.payload(uptime, clock.epoch(uptime), _memory_free())
        mqtt.publish_health(payload, uptime)
    except Exception as error:
        print("MQTT health snapshot skipped:", type(error).__name__)


def _checkpoint_board_health(stage, screen, now):
    if board_health is None:
        return
    if board_health.checkpoint(stage, screen, time.monotonic()):
        _publish_board_health(now, force=True)
mqtt_screens = MqttScreenState(
    getattr(settings, "MQTT_SCREENS_TOPIC", "led/screens/+")
)
football_screens = FootballScreenState(
    getattr(settings, "MQTT_FOOTBALL_TOPIC", "led/football/+"),
    enabled=getattr(settings, "MQTT_FOOTBALL_ENABLED", True),
)
football_presentations = FootballPresentationQueue()
active_football_screen = None
active_football_started = None
football_rotation_resume = None
football_pause_started = None
football_presentation_sequence = 0
last_recycling_date = None


def _effective_mqtt_screens(epoch_now):
    football = football_screens.screens(epoch_now)
    if epoch_now is None:
        return football
    return mqtt_screens.effective_screens(
        epoch_now, clock.date_text(time.monotonic())
    ) + football


def _reminder_epoch(now):
    epoch_now = clock.epoch(now)
    if epoch_now is None:
        system_epoch = time.time()
        epoch_now = system_epoch if system_epoch >= 1000000000 else None
    return epoch_now


def _flash_started(now):
    global flash_resume, last_render_key, flash_started_ticks, football_pause_started
    flash_started_ticks = ticks_ms()
    if flash_resume is None:
        active_presentation = globals().get("active_football_screen")
        resume_state = globals().get("football_rotation_resume")
        if active_presentation is not None and resume_state is not None:
            flash_resume = resume_state
            football_pause_started = flash_started_ticks
        else:
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


def _cancel_active_football():
    """Cancel a football prompt whose retained snapshot is no longer presentable."""
    global active_football_screen, active_football_started
    global football_rotation_resume, football_pause_started, flash_resume
    global last_render_key
    if active_football_screen is None:
        return False
    team_key = active_football_screen.get("team_key")
    if football_rotation_resume is not None:
        rotation.resume(
            ticks_ms(), football_rotation_resume[0], football_rotation_resume[1]
        )
    active_football_screen = None
    active_football_started = None
    football_rotation_resume = None
    football_pause_started = None
    flash_resume = None
    last_render_key = None
    print("FOOTBALL PRESENTATION CANCEL team={} reason=fixture_unavailable".format(
        team_key
    ))
    return True


if settings.MQTT_ENABLED and settings.MQTT_ENABLE_EXPERIMENTAL and not steam_train_test:
    from mqtt_client import FlashMqttClient

    def receive_mqtt(topic, payload):
        global mqtt_screens_changed, mqtt_screens_update_pending
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
        football_prefix = football_screens.prefix
        if topic.startswith(football_prefix):
            epoch_now = _reminder_epoch(now)
            if football_presentations.accept_snapshot(
                    football_screens, topic, payload, epoch_now):
                team_key = topic[len(football_prefix):]
                print("FOOTBALL UPDATE ACCEPTED team={} pending={}".format(
                    team_key, len(football_presentations)
                ))
                mqtt_screens_changed = True
                mqtt_screens_update_pending = True
            return
        epoch_now = _reminder_epoch(now)
        if epoch_now is None:
            print("MQTT screen ignored: clock not synchronized")
            return
        if mqtt_screens.accept(topic, payload, epoch_now):
            mqtt_screens_changed = True
            mqtt_screens_update_pending = True

    mqtt = FlashMqttClient(
        settings,
        receive_mqtt,
        startup_delay_seconds=settings.MQTT_STARTUP_DELAY_SECONDS,
        on_connecting=lambda: _checkpoint_board_health(
            "mqtt",
            rotation.current(ticks_ms())[0] if rotation.screens else None,
            time.monotonic(),
        ),
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
christmas_gc_suspended = False
rail_gc_pause_active = False
rail_gc_last_pressure_collect = None
sun_gc_completed_key = None
football_gc_last_key = None
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
RAIL_GC_CRITICAL_FREE_BYTES = 192 * 1024
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
    if _smooth_football(screen):
        return phase
    if screen.get("kind") == "calendar_agenda" and screen.get("source") == "todoist":
        return phase
    if _smooth_queue(screen):
        return phase
    if _smooth_sun_weather(screen):
        return phase
    if _smooth_bin_collection(screen):
        return phase
    if (settings.DISPLAY_BACKEND == "matrix"
            and screen.get("kind") in ("christmas_tracker_intro", "christmas_tracker")):
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


def _smooth_football(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "football_score"
    )


def _smooth_bin_collection(screen):
    return (
        settings.DISPLAY_BACKEND == "matrix"
        and screen.get("kind") == "bin_collection"
    )


def _smooth_christmas(screen):
    return settings.DISPLAY_BACKEND == "matrix" and screen.get("kind") in (
        "christmas_tracker_intro", "christmas_tracker"
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


def _screen_status_payload(screen, now):
    duration = max(
        1,
        int(screen.get("effective_duration_seconds") or screen.get("duration_seconds") or 8),
    )
    reported_at = clock.epoch(now)
    return json.dumps({
        "screen_id": str(screen.get("id") or ""),
        "screen_kind": str(screen.get("kind") or ""),
        "expected_duration_seconds": duration,
        "uptime_seconds": int(now),
        "reported_at_epoch": reported_at,
        "deadline_epoch": reported_at + duration if reported_at is not None else None,
    }, separators=(",", ":"))


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
            # Keep MQTT reads alive during stationary marquee pauses, but do
            # not begin a Wi-Fi/broker handshake inside the departures scene.
            # MiniMQTT connect can block for seconds and leave the rail display
            # frozen even though the calling-at text is between motion phases.
            mqtt_allow_connect = (
                mqtt_allow_connect
                and not mqtt_animation_active
                and mqtt_screen.get("kind") != "rail_combined"
            )
        if active_football_screen is not None and not flash.active(now):
            football_phase = elapsed_seconds(active_football_started)
            if display.animation_active(active_football_screen, football_phase):
                mqtt_animation_active = True
                mqtt_allow_connect = False
        # MiniMQTT's nominal socket timeout does not bound the complete
        # CircuitPython/Wi-Fi path. Do not interrupt visible animation with
        # keepalive/reconnect work; service the connection in an idle window.
        if not mqtt_animation_active:
            mqtt.poll(now, allow_connect=mqtt_allow_connect)
            _apply_pending_mqtt_screen_updates(time.monotonic())
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
            diagnostic_screen = {"id": "diagnostic", "kind": "diagnostic", "source": "local"}
            _checkpoint_board_health("diagnostic", diagnostic_screen, now)
            if board_health is not None:
                board_health.set_mode("diagnostic")
            print("DIAGNOSTIC", name)
            display.show_diagnostic(color)
            if board_health is not None:
                board_health.completed_render(
                    diagnostic_screen, time.monotonic(), clock.epoch(time.monotonic()), _memory_free(),
                )
            rendered_diagnostic_index = runtime_mode.diagnostic_index
        _sleep_interruptible(settings.FRAME_SECONDS)
        _publish_board_health(time.monotonic())
        continue

    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    maintenance_resume = None
    maintenance_active = False
    if not flash.active(now) and flash.event is None:
        if active_football_screen is not None:
            latest_football = football_screens.screen_for_team(
                active_football_screen.get("team_key"), _reminder_epoch(now)
            )
            if latest_football is None:
                _cancel_active_football()
            else:
                latest_football["id"] = active_football_screen.get("id")
                latest_football["ball_animation"] = active_football_screen.get(
                    "ball_animation", False
                )
                active_football_screen = latest_football
            active_elapsed = (elapsed_seconds(active_football_started)
                              if active_football_screen is not None else 0)
            active_duration = (float(active_football_screen.get("duration_seconds") or 20)
                               if active_football_screen is not None else 0)
            if (active_football_screen is not None
                    and active_elapsed >= active_duration):
                print("FOOTBALL PRESENTATION END team={}".format(
                    active_football_screen.get("team_key")
                ))
                active_football_screen = None
                active_football_started = None
                if football_rotation_resume is not None:
                    rotation.resume(
                        ticks_ms(), football_rotation_resume[0], football_rotation_resume[1]
                    )
                football_rotation_resume = None
            elif active_football_screen is not None:
                # The newest snapshot is now on the active card; do not replay
                # it as a second 20-second card after this one finishes.
                football_presentations.discard(
                    active_football_screen.get("team_key")
                )
        if active_football_screen is None:
            team_key = football_presentations.pop()
            if team_key is not None:
                epoch_now = _reminder_epoch(now)
                next_screen = football_screens.screen_for_team(team_key, epoch_now)
                if next_screen is not None:
                    football_presentation_sequence += 1
                    next_screen["id"] = "football-event-{}".format(
                        football_presentation_sequence
                    )
                    next_screen["ball_animation"] = True
                    football_rotation_resume = rotation.freeze(ticks_ms())
                    active_football_screen = next_screen
                    active_football_started = ticks_ms()
                    print("FOOTBALL PRESENTATION START team={} pending={}".format(
                        team_key, len(football_presentations)
                    ))
    if active_football_screen is not None and not flash.active(now):
        candidate = active_football_screen
        candidate_phase = elapsed_seconds(active_football_started)
    else:
        candidate, candidate_phase = rotation.current(ticks_ms())
    rotation_idle = candidate.get("id") == "schedule-idle"
    rotation_state_now = ticks_ms()
    if (last_rotation_state_log is None
            or rotation_state_now - last_rotation_state_log >= 60000):
        schedule_state = rotation.schedule_state()
        print(
            "ROTATION STATE http={} mqtt={} cycle={} active={} disabled={} windowed={} idle={} clock={}".format(
                schedule_state["http"], schedule_state["mqtt"],
                schedule_state["cycle"], schedule_state["active"],
                schedule_state["disabled"], schedule_state["windowed"],
                schedule_state["idle"], "ready" if clock.epoch(now) is not None else "unset",
            )
        )
        last_rotation_state_log = rotation_state_now
    fetch_due = ticks_ms() >= next_fetch
    boundary = last_visible_screen != candidate.get("id")
    task_unready = (candidate.get("kind") == "calendar_agenda"
                    and candidate.get("source") == "todoist"
                    and not display.tasks_ready(candidate, clock.date_text(now))
                    and ticks_ms() >= task_retry_at)
    # Weather is grouped by the scheduler, while the train and SL7 bus
    # introductions must transition directly into their departures boards.
    paired_followup = rotation.is_paired_transition(last_visible_screen, candidate)
    christmas_action = christmas_gc_action(
        candidate.get("kind"), christmas_gc_suspended, flash.active(now)
    )
    if christmas_action == "exit":
        try:
            leave_christmas_gc_window(gc)
        except Exception as error:
            print("CHRISTMAS GC EXIT FAILED collector_state=enabled:", error)
            if gc is not None and hasattr(gc, "enable"):
                gc.enable()
        christmas_gc_suspended = False
    if (rotation.screens and active_football_screen is None
            and not steam_train_test and not flash.active(now)
            and boundary and not paired_followup and (fetch_due or task_unready)
            and not rotation.is_maintenance_screen(candidate)):
        rotation.maintenance_slot(ticks_ms())
        candidate, candidate_phase = rotation.current(ticks_ms())
    maintenance_visible = rotation.is_static(candidate)
    if (boundary and not maintenance_visible
            and last_logged_screen_key is not None
            and last_logged_screen_key[1] == "bin_collection"
            and gc is not None and hasattr(gc, "collect")):
        try:
            _checkpoint_board_health("gc", candidate, now)
            gc_started = ticks_ms()
            heap_before_gc = _memory_free()
            gc.collect()
            print("BIN GC EXIT duration={:.3f}s heap_free_before={} heap_free_after={}".format(
                elapsed_seconds(gc_started), heap_before_gc, _memory_free()
            ))
        except Exception as error:
            print("BIN GC EXIT FAILED:", error)
    if (boundary and last_logged_screen_key is not None
            and last_logged_screen_key[1] in ("calendar_agenda", "theme_park_queues")
            and gc is not None and hasattr(gc, "collect")):
        try:
            _checkpoint_board_health("gc", candidate, now)
            gc_started = ticks_ms()
            heap_before_gc = _memory_free()
            gc.collect()
            print(
                "SCREEN GC EXIT id={} kind={} duration={:.3f}s heap_free_before={} heap_free_after={}".format(
                    last_logged_screen_key[0], last_logged_screen_key[1],
                    elapsed_seconds(gc_started), heap_before_gc, _memory_free(),
                )
            )
        except Exception as error:
            print("SCREEN GC EXIT FAILED id={} kind={}:".format(
                last_logged_screen_key[0], last_logged_screen_key[1]
            ), error)
    if not rotation.screens:
        # Do not make the startup placeholder look like the disabled standalone
        # Today screen or the Next 24H forecast. The feed may still be loading.
        candidate = {"id": "startup-loading", "kind": "startup",
                     "title": "STARTING", "empty_state": "LOADING SCREENS",
                     "duration_seconds": 8}
        candidate_phase = 0
        maintenance_visible = True
    # A maintenance slot is an identity, not a new slot on every resumed loop.
    # resume() adjusts started_at to preserve the fractional phase, so including
    # it here caused a full gc.collect() and rail prebuild attempt every frame.
    slot_key = (rotation.cycle_number, candidate.get("id"))
    if maintenance_visible and not steam_train_test and not flash.active(now):
        maintenance_active = True
        display.show(candidate, clock.text(now), clock_date=clock.date_text(now), phase=candidate_phase, now_epoch=clock.epoch(now))
        if mqtt is not None and candidate.get("id") == "startup-loading":
            # Keep the loading frame visible if the initial broker handshake
            # takes several seconds; do not move it into the animation loop.
            mqtt.poll(time.monotonic(), allow_connect=True)
            _apply_pending_mqtt_screen_updates(time.monotonic())
        if rotation.screens:
            maintenance_resume = rotation.freeze(ticks_ms())
        if slot_key != last_maintenance_slot:
            if gc is not None and hasattr(gc, "collect"):
                _checkpoint_board_health("gc", candidate, now)
                gc.collect()
    # Screen API refreshes replace payload objects and can require a complete
    # departures-scene rebuild. Keep synchronous fetches out of all live
    # animations; the next static slot is soon enough to apply new data.
    should_fetch = (
        fetch_due
        and (maintenance_visible or rotation_idle
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
                _checkpoint_board_health("gc", candidate, now)
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
            if gc is not None:
                gc.collect()
                print("FETCH GC free={}".format(_memory_free()))
            if board_health is not None:
                board_health.begin_fetch(time.monotonic())
            _checkpoint_board_health("fetch", candidate, now)
            print("FETCH START")
            payload = fixture_payload(now) if client is None else client.fetch()
            screens = with_christmas_tracker(payload.get("screens"))
            attach_shared_weather(screens, payload.get("weather"))
            christmas_policy = payload.get("christmas") or {}
            for scheduled_screen in screens:
                if scheduled_screen.get("kind") in ("christmas_tracker_intro", "christmas_tracker"):
                    scheduled_screen["schedule_windows"] = christmas_policy.get("schedule_windows", [])
                    scheduled_screen["schedule_enabled"] = christmas_policy.get("enabled", True)
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
            print("FETCH OK screens={} duration={:.3f} fetched_at={}".format(
                len(screens or []), fetch_duration,
                safe_snapshot_timestamp(payload.get("fetched_at")),
            ))
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
            if board_health is not None:
                board_health.fetch_result(fetch_completed, fetch_duration, screens)
            prepare_intro = getattr(display, "prepare_intro", None)
            if callable(prepare_intro):
                for intro in screens:
                    if (not isinstance(intro, dict)
                            or intro.get("kind") not in (
                                "steam_train_intro", "bus_intro",
                                "christmas_tracker_intro", "christmas_tracker"
                            )):
                        continue
                    try:
                        _checkpoint_board_health("build", intro, fetch_completed)
                        prepared = (
                            prepare_intro(intro, clock.date_text(fetch_completed))
                            if intro.get("kind") == "christmas_tracker"
                            else prepare_intro(intro)
                        )
                        if prepared:
                            if intro.get("kind") in ("christmas_tracker_intro", "christmas_tracker"):
                                prepare_christmas_scene_gc(gc)
                            print(
                                "INTRO SCENE PREPARED id={} kind={} heap_free={}".format(
                                    intro.get("id"), intro.get("kind"), _memory_free()
                                )
                            )
                    except Exception as error:
                        print("Intro scene preparation deferred:", error)
            rotation.set_schedule_time(clock.date_text(fetch_completed), clock.text(fetch_completed))
            rotation.set_schedule_epoch(clock.epoch(fetch_completed))
            mqtt_screens.configure_recycling(recycling_policy(payload))
            epoch_now = _reminder_epoch(fetch_completed)
            last_recycling_date = clock.date_text(fetch_completed)
            rotation.update_sources(
                screens,
                _effective_mqtt_screens(epoch_now)
                if epoch_now is not None else [],
                ticks_ms(),
            )
            schedule_state = rotation.schedule_state()
            print(
                "ROTATION STATE http={} mqtt={} cycle={} active={} disabled={} windowed={} idle={}".format(
                    schedule_state["http"], schedule_state["mqtt"],
                    schedule_state["cycle"], schedule_state["active"],
                    schedule_state["disabled"], schedule_state["windowed"],
                    schedule_state["idle"],
                )
            )
            if fetch_resume is not None:
                rotation.resume(ticks_ms(), fetch_resume[0], fetch_resume[1])
            _apply_flash_config(payload, fetch_completed)
            transport_stale = False
        except Exception as error:
            if board_health is not None:
                board_health.failure("fetch")
            _publish_board_health(time.monotonic(), force=True)
            fetch_completed = time.monotonic()
            fetch_duration = elapsed_seconds(fetch_started_ticks)
            telemetry_fetches += 1
            telemetry_fetch_failures += 1
            telemetry_fetch_total += fetch_duration
            telemetry_fetch_max = max(telemetry_fetch_max, fetch_duration)
            if board_health is not None:
                board_health.fetch_result(
                    fetch_completed, fetch_duration, error=type(error).__name__,
                    error_stage=(client.last_error_stage if client is not None else "publisher"),
                )
            failed_stage = client.last_error_stage if client is not None else "publisher"
            print("Screen fetch failed duration={:.3f} class={} stage={}".format(
                fetch_duration, type(error).__name__, failed_stage,
            ))
            _publish_board_health(fetch_completed, force=True)
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
        last_maintenance_slot = (rotation.cycle_number, candidate.get("id"))

    if (MATRIX_RAIL_PREBUILD_EXPERIMENT and maintenance_active
            and settings.DISPLAY_BACKEND == "matrix" and not flash.active(now)):
        upcoming_rail = rotation.next_paired_rail_screen()
        prebuild_key = (
            rotation.cycle_number,
            candidate.get("id"),
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
                    _checkpoint_board_health("build", upcoming_rail, now)
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
    football_stale_changed = football_screens.staleness_changed(epoch_now)
    if epoch_now is not None and (expired_mqtt or football_stale_changed or recycling_date != last_recycling_date):
        mqtt_screens_update_pending = True
        mqtt_screens_changed = True
    last_recycling_date = recycling_date

    stage_started = ticks_ms() if MATRIX_TELEMETRY_ENABLED else None
    if flash.active(now):
        screen, phase = flash.screen(), elapsed_seconds(flash_started_ticks)
    else:
        if flash.event is not None:
            flash.clear()
            if flash_resume is not None:
                if football_rotation_resume is None:
                    rotation.resume(ticks_ms(), flash_resume[0], flash_resume[1])
                flash_resume = None
            if football_pause_started is not None and active_football_screen is not None:
                active_football_started += ticks_ms() - football_pause_started
                football_pause_started = None
            last_render_key = None
            print("FLASH END")
            if (active_football_screen is not None
                    and football_screens.screen_for_team(
                        active_football_screen.get("team_key"), _reminder_epoch(now)
                    ) is None):
                _cancel_active_football()
        if active_football_screen is not None:
            screen = active_football_screen
            phase = elapsed_seconds(active_football_started)
        else:
            rotation.set_schedule_time(clock.date_text(now), clock.text(now))
            rotation.set_schedule_epoch(clock.epoch(now))
            screen, phase = rotation.current(ticks_ms())
    if MATRIX_TELEMETRY_ENABLED:
        stage_durations["screen_select"] = elapsed_seconds(stage_started)
    screen = hardware_safe_screen(screen)
    if board_health is not None:
        board_health.set_mode("normal")
    if transport_stale and any(candidate is screen for candidate in rotation.http_screens):
        screen = dict(screen)
        screen["stale"] = True
        weather = screen.get("weather")
        if isinstance(weather, dict):
            weather = dict(weather)
            weather["stale"] = True
            screen["weather"] = weather
    christmas_action = christmas_gc_action(
        screen.get("kind"), christmas_gc_suspended,
        bool(flash.active(now) and screen.get("kind") not in ("christmas_tracker_intro", "christmas_tracker")),
    )
    if settings.DISPLAY_BACKEND == "matrix" and christmas_action == "enter":
        try:
            enter_christmas_gc_window(gc)
        except Exception as error:
            print("CHRISTMAS GC ENTRY FAILED collector_state=unknown:", error)
            # Preserve the board's ability to reclaim memory even if the GC
            # state transition itself fails. Disabling here could turn a
            # recoverable allocation spike into a permanent display stall.
            if gc is not None and hasattr(gc, "enable"):
                try:
                    gc.enable()
                except Exception as enable_error:
                    print("CHRISTMAS GC ENABLE RETRY FAILED:", enable_error)
        christmas_gc_suspended = True
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
        emergency_due = (
            heap_before_gc is not None
            and heap_before_gc < RAIL_GC_CRITICAL_FREE_BYTES
        )
        collect_at_pause = pause_now and (
            not rail_gc_pause_active or pressure_due
        )
        if collect_at_pause or emergency_due:
            gc_reason = (
                "calling_end_pause"
                if pause_now
                else "critical_heap_during_motion"
            )
            gc_started = ticks_ms()
            if HEAP_DIAGNOSTICS_ENABLED:
                print(
                    "RAIL GC START reason={} motion_active={} heap_free={}".format(
                        gc_reason, not pause_now, heap_before_gc
                    )
                )
            try:
                _checkpoint_board_health("gc", screen, now)
                collect_gc_with_state(gc, enabled_after=False)
            except Exception as error:
                print("RAIL GC FAILED reason={} collector_state=disabled:".format(gc_reason), error)
            gc_duration = elapsed_seconds(gc_started)
            if pressure_due or emergency_due:
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
            _checkpoint_board_health("gc", screen, now)
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
        rail_display = getattr(display, "base", display)
        rail_timing_before_show = (
            getattr(rail_display, "_last_rail_update_seconds", 0.0),
            getattr(rail_display, "_last_rail_refresh_seconds", 0.0),
            getattr(rail_display, "_last_rail_heap_gain", None),
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
    _checkpoint_board_health("render", screen, now)
    try:
        display.show(
            screen,
            clock.text(now),
            clock_date=clock.date_text(now),
            phase=_display_phase(screen, phase),
            now_epoch=clock.epoch(now),
        )
    except Exception as error:
        if board_health is not None:
            board_health.failure("render")
        _publish_board_health(time.monotonic(), force=True)
        print("Screen render failed:", type(error).__name__)
        raise
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
    # Automatic GC is enabled outside the rail-only GC suppression window.
    # The settled football countdown is a safe time for one *explicit*
    # collection: both scene groups are stationary and the countdown has been
    # rendered. Do not collect during the 3.2 s roll/push or while a goal
    # highlight is animating. Key by rotation cycle/event ID, not phase or
    # countdown text, to avoid collecting on each one-second tick.
    if (settings.DISPLAY_BACKEND == "matrix"
            and gc is not None and hasattr(gc, "collect")
            and football_gc_safe_to_collect(
                screen, phase, display.animation_active(screen, phase)
            )):
        football_gc_key = (screen.get("id"), rotation.cycle_number)
        if football_gc_key != football_gc_last_key:
            # Record before collection: an unexpected failure should not
            # trigger an expensive retry every second on the visible screen.
            football_gc_last_key = football_gc_key
            try:
                _checkpoint_board_health("gc", screen, time.monotonic())
                football_gc_before = _memory_free()
                football_gc_started = ticks_ms()
                # Restore automatic collection even if gc.collect raises.
                collect_gc_with_state(gc, enabled_after=True)
                if HEAP_DIAGNOSTICS_ENABLED:
                    print(
                        "FOOTBALL GC settled id={} duration={:.3f}s "
                        "heap_free_before={} heap_free_after={} automatic_gc=enabled".format(
                            screen.get("id"),
                            elapsed_seconds(football_gc_started),
                            football_gc_before,
                            _memory_free(),
                        )
                    )
            except Exception as error:
                print("FOOTBALL GC FAILED; automatic GC restored:", error)
    if log_screen_change:
        base_display = getattr(display, "base", display)
        hardware_display = getattr(base_display, "display", None)
        root_group = getattr(hardware_display, "root_group", None)
        brightness = getattr(base_display, "brightness_percent", None)
        try:
            root_children = len(root_group) if root_group is not None else None
        except Exception:
            root_children = None
        print(
            "SCREEN OK id={} kind={} heap_free={} root_set={} root_children={} refresh={} brightness={}".format(
                render_key[0], render_key[1], _memory_free(), root_group is not None,
                root_children,
                getattr(base_display, "_last_present_refresh", None), brightness,
            )
        )
        last_logged_screen_key = render_key
        last_logged_screen_started = ticks_ms()
        screen_heap_low_water = _memory_free()
        if mqtt is not None and getattr(settings, "MQTT_BOARD_TELEMETRY_ENABLED", False):
            mqtt.publish_screen_status(_screen_status_payload(screen, now), now)
    if board_health is not None:
        board_health.completed_render(
            screen, time.monotonic(), clock.epoch(time.monotonic()), _memory_free(),
            rotation.cycle_number,
            getattr(getattr(display, "base", display), "brightness_percent", None),
            _matrix_root_token() is not None,
        )
    _publish_board_health(time.monotonic())
    last_visible_screen = screen.get("id")
    mqtt_screens_changed = False
    smooth_animation = (
        (settings.DISPLAY_BACKEND == "matrix" and screen.get("kind") == "flash")
        or _smooth_todoist(screen)
        or _smooth_departures(screen)
        or _smooth_queue(screen)
        or _smooth_steam_train(screen)
        or _smooth_bus_intro(screen)
        or _smooth_football(screen)
        or _smooth_sun_weather(screen)
        or _smooth_today(screen)
        or _smooth_bin_collection(screen)
        or _smooth_christmas(screen)
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
