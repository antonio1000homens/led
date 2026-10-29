"""Compact, bounded MQTT health snapshots for the MatrixPortal loop."""

HEARTBEAT_SECONDS = 30
ERROR_CLASSES = frozenset({
    "OSError", "RuntimeError", "ValueError", "TypeError", "MemoryError",
    "ImportError", "AssertionError", "HTTPError", "URLError", "ConnectionError",
    "TimeoutError", "JSONDecodeError", "other",
})
_SAFE_TIMESTAMP_CHARS = frozenset("0123456789TtZz:.-+ ")


def safe_snapshot_timestamp(value):
    """Keep publisher-time diagnostics bounded and free of arbitrary text."""
    if not isinstance(value, str) or not value or len(value) > 32:
        return "unknown"
    if any(character not in _SAFE_TIMESTAMP_CHARS for character in value):
        return "unknown"
    return value


def _text(value, limit=48):
    if value is None:
        return ""
    value = str(value)
    return "".join(
        char for char in value
        if "0" <= char <= "9" or "A" <= char <= "Z" or "a" <= char <= "z" or char in "._-:"
    )[:limit]


def _source_timestamp(value):
    if not isinstance(value, str):
        return None
    if len(value) > 32 or not value or any(char not in "0123456789TtZz:.-+ " for char in value):
        return None
    return value if len(value) >= 10 else None


def safe_snapshot_timestamp(value):
    """Keep serial freshness diagnostics bounded and free of arbitrary text."""
    return _source_timestamp(value) or "unknown"


class BoardHealth:
    """Keep one bounded snapshot; callers publish only at safe loop points."""

    def __init__(self, session_id, firmware_revision="led-health-v1", board_id="matrixportal-s3"):
        self.session_id = _text(session_id, 32) or "unknown"
        self.firmware_revision = _text(firmware_revision, 32) or "unknown"
        self.sequence = 0
        self.last_report = None
        self.state = {
            "schema_version": 1,
            "board_id": _text(board_id, 32) or "matrixportal-s3",
            "firmware_revision": self.firmware_revision,
            "session_id": self.session_id,
            "sequence": 0,
            "stage": "startup",
            "stage_started_uptime_seconds": 0,
            "runtime_mode": "normal",
            "attempted_screen_id": "",
            "attempted_screen_kind": "",
            "attempted_source": "",
            "last_screen_id": "",
            "last_screen_kind": "",
            "last_source": "",
            "last_render_uptime_seconds": None,
            "screen_started_uptime_seconds": None,
            "expected_duration_seconds": 0,
            "uptime_seconds": 0,
            "clock_synchronized": False,
            "reported_at_epoch": None,
            "free_heap_bytes": None,
            "heap_low_water_bytes": None,
            "fetch_failures": 0,
            "render_failures": 0,
            "fetch_duration_seconds": None,
            "last_fetch_attempt_uptime_seconds": None,
            "last_fetch_success_uptime_seconds": None,
            "last_fetch_successful": None,
            "last_fetch_error_class": "",
            "last_fetch_error_stage": "",
            "feed_health": [],
            "cycle_number": 0,
            "brightness_percent": None,
            "root_group_set": None,
        }
        self.heap_low_water = None
        self.stage_started = 0

    def checkpoint(self, stage, screen=None, uptime=None):
        if screen is None:
            screen = {
                "id": self.state["attempted_screen_id"],
                "kind": self.state["attempted_screen_kind"],
                "source": self.state["attempted_source"],
            }
        elif not isinstance(screen, dict):
            screen = {}
        previous = (
            self.state["stage"], self.state["attempted_screen_id"],
            self.state["attempted_screen_kind"], self.state["attempted_source"],
        )
        self.state["stage"] = _text(stage, 24) or "unknown"
        if previous[0] != self.state["stage"]:
            self.stage_started = uptime if uptime is not None else self.state["uptime_seconds"]
        self.state["stage_started_uptime_seconds"] = int(self.stage_started)
        self.state["attempted_screen_id"] = _text(screen.get("id"))
        self.state["attempted_screen_kind"] = _text(screen.get("kind"))
        self.state["attempted_source"] = _text(screen.get("source"))
        return previous != (
            self.state["stage"], self.state["attempted_screen_id"],
            self.state["attempted_screen_kind"], self.state["attempted_source"],
        )

    def completed_render(self, screen, uptime, epoch, free_heap, cycle=0, brightness=None, root_set=None):
        screen = screen if isinstance(screen, dict) else {}
        screen_id = _text(screen.get("id"))
        if screen_id != self.state["last_screen_id"]:
            self.state["screen_started_uptime_seconds"] = int(uptime)
        self.state["expected_duration_seconds"] = max(
            1, int(screen.get("effective_duration_seconds") or screen.get("duration_seconds") or 8)
        )
        self.state["last_screen_id"] = screen_id
        self.state["last_screen_kind"] = _text(screen.get("kind"))
        self.state["last_source"] = _text(screen.get("source"))
        self.state["last_render_uptime_seconds"] = int(uptime)
        self.state["cycle_number"] = max(0, int(cycle or 0))
        self.state["brightness_percent"] = brightness
        self.state["root_group_set"] = bool(root_set) if root_set is not None else None
        self.state["clock_synchronized"] = epoch is not None
        self.heap(free_heap)

    def heap(self, free_heap):
        if free_heap is not None:
            free_heap = int(free_heap)
            self.state["free_heap_bytes"] = free_heap
            if self.heap_low_water is None or free_heap < self.heap_low_water:
                self.heap_low_water = free_heap
            self.state["heap_low_water_bytes"] = self.heap_low_water

    def set_mode(self, mode):
        self.state["runtime_mode"] = _text(mode, 16) or "normal"

    def failure(self, stage):
        key = "fetch_failures" if stage == "fetch" else "render_failures"
        self.state[key] += 1
        self.checkpoint(stage, {
            "id": self.state["attempted_screen_id"],
            "kind": self.state["attempted_screen_kind"],
            "source": self.state["attempted_source"],
        })

    def fetch_result(self, uptime, duration, feeds=None, error=None, error_stage=None):
        self.state["fetch_duration_seconds"] = round(float(duration), 3)
        self.state["last_fetch_error_class"] = (
            str(error) if str(error) in ERROR_CLASSES else "other"
        )
        if error:
            self.state["last_fetch_successful"] = False
            self.state["last_fetch_error_stage"] = (
                _text(error_stage, 24) if error_stage in (
                    "session_setup", "connection_setup", "response_headers",
                    "tls_setup", "response_body", "publisher",
                ) else "unknown"
            )
            self.failure("fetch")
            return
        self.state["last_fetch_successful"] = True
        self.state["last_fetch_success_uptime_seconds"] = int(uptime)
        self.state["last_fetch_error_class"] = ""
        self.state["last_fetch_error_stage"] = ""
        summary = []
        if isinstance(feeds, dict):
            for name, value in feeds.items():
                if len(summary) >= 8:
                    break
                if isinstance(value, dict):
                    entry = {
                        "source": _text(name, 24),
                        "stale": bool(value.get("stale", False)),
                    }
                    timestamp = _source_timestamp(
                        value.get("fetched_at") or value.get("refreshed_at") or value.get("updated_at")
                    )
                    if timestamp:
                        entry["refreshed_at"] = timestamp
                    summary.append(entry)
        elif isinstance(feeds, list):
            statuses = {}
            for value in feeds:
                if not isinstance(value, dict):
                    continue
                name = _text(value.get("source"), 24)
                if not name:
                    continue
                entry = statuses.setdefault(name, {"stale": False})
                entry["stale"] = entry["stale"] or bool(value.get("stale", False))
                timestamp = _source_timestamp(
                    value.get("fetched_at") or value.get("refreshed_at") or value.get("updated_at")
                )
                if timestamp:
                    entry["refreshed_at"] = timestamp
            for name, status in statuses.items():
                if len(summary) >= 8:
                    break
                entry = {"source": name}
                entry.update(status)
                summary.append(entry)
        self.state["feed_health"] = summary

    def begin_fetch(self, uptime):
        self.state["last_fetch_attempt_uptime_seconds"] = int(uptime)

    def due(self, uptime):
        return self.last_report is None or uptime - self.last_report >= HEARTBEAT_SECONDS

    def payload(self, uptime, epoch, free_heap):
        self.sequence += 1
        self.state["sequence"] = self.sequence
        self.state["uptime_seconds"] = int(uptime)
        self.state["clock_synchronized"] = epoch is not None
        self.state["reported_at_epoch"] = int(epoch) if epoch is not None else None
        self.heap(free_heap)
        self.last_report = uptime
        # A small fixed set of fields keeps CircuitPython allocations bounded.
        import json
        return json.dumps(self.state, separators=(",", ":"))
