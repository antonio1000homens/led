"""Hardware-independent validation and lifecycle for transient flash events."""

from __future__ import annotations

import json


def _days_before_year(year):
    years = year - 1
    return years * 365 + years // 4 - years // 100 + years // 400


def _iso_epoch(value):
    if not isinstance(value, str) or len(value) < 20:
        raise ValueError("timestamp must be ISO-8601")
    try:
        year, month, day = int(value[0:4]), int(value[5:7]), int(value[8:10])
        hour, minute, second = int(value[11:13]), int(value[14:16]), int(value[17:19])
        if value[19] == ".":
            zone_start = len(value)
            for marker in ("Z", "+", "-"):
                end = value.find(marker, 20)
                if end >= 0:
                    zone_start = min(zone_start, end)
            value = value[:19] + value[zone_start:]
        zone = value[19:]
        if zone == "Z":
            offset = 0
        elif len(zone) == 6 and zone[0] in ("+", "-") and zone[3] == ":":
            offset = (int(zone[1:3]) * 60 + int(zone[4:6])) * 60
            if zone[0] == "-":
                offset = -offset
        else:
            raise ValueError
        if not 1 <= month <= 12 or not 1 <= day <= 31 or hour > 23 or minute > 59 or second > 59:
            raise ValueError
    except (TypeError, ValueError, IndexError):
        raise ValueError("timestamp must be ISO-8601")
    days = _days_before_year(year) - _days_before_year(1970)
    month_days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    days += sum(month_days[:month - 1]) + day - 1
    return days * 86400 + hour * 3600 + minute * 60 + second - offset


def parse_flash_event(payload, now=None):
    """Return a safe normalized event, or ``None`` for invalid/expired input."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, UnicodeError):
            return None
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeError):
            return None
    if not isinstance(payload, dict):
        return None
    event_id = payload.get("id")
    label = payload.get("label")
    if (
        not isinstance(event_id, str)
        or not event_id.strip()
        or payload.get("type") != "reminder"
        or payload.get("event") not in ("due", "scheduled")
    ):
        return None
    if not isinstance(label, str) or not label.strip():
        return None
    try:
        expires_at = _iso_epoch(payload.get("expires_at"))
        due_at = payload.get("due_at")
        if due_at is not None:
            due_epoch = _iso_epoch(due_at)
            if expires_at <= due_epoch:
                return None
        elif payload.get("event") == "scheduled":
            return None
        if now is not None and expires_at <= int(now):
            return None
    except (TypeError, ValueError):
        return None
    return {
        "id": event_id.strip(),
        "type": "reminder",
        "label": label.strip(),
        "due_at": due_at,
        "expires_at": payload["expires_at"],
        "source": str(payload.get("source") or "unknown"),
    }


class FlashState:
    """Deduplicate events and keep the active event's replacement semantics."""

    def __init__(self, duration_seconds=5, enabled=False, seen_limit=32):
        self.enabled = bool(enabled)
        self.duration_seconds = max(1, int(duration_seconds or 5))
        self.seen_limit = max(1, int(seen_limit))
        self.seen = []
        self.event = None
        self.started_at = None
        self.pending = None
        self.last_published = None

    def accept(self, payload, now, epoch_now=None):
        if not self.enabled:
            return False
        if isinstance(payload, (str, bytes, bytearray)):
            try:
                payload = json.loads(payload if isinstance(payload, str) else payload.decode("utf-8"))
            except (ValueError, UnicodeError):
                return False
        if not isinstance(payload, dict):
            return False
        snapshot = payload.get("event") in ("scheduled", "clear")
        if snapshot:
            if payload.get("type") != "reminder" or epoch_now is None:
                return False
            try:
                published = _iso_epoch(payload.get("published_at"))
            except ValueError:
                return False
            if self.last_published is not None and published < self.last_published:
                return False
            if payload.get("event") == "clear":
                self.last_published = published
                self.pending = None
                return False
        event = parse_flash_event(payload, epoch_now if epoch_now is not None else now)
        if event is None:
            return False
        if snapshot:
            self.last_published = published
            self.pending = event if event["id"] not in self.seen else None
            return self.tick(now, epoch_now)
        if event["id"] in self.seen:
            return False
        # Legacy due messages also obey due_at whenever a clock is available.
        if epoch_now is not None and event["due_at"] is not None:
            self.pending = event
            return self.tick(now, epoch_now)
        return self._start(event, now)

    def tick(self, now, epoch_now):
        """Fire the cached occurrence using the local clock, without network I/O."""
        if not self.enabled or self.pending is None or epoch_now is None:
            return False
        event = self.pending
        if _iso_epoch(event["expires_at"]) <= epoch_now:
            self.pending = None
            return False
        if _iso_epoch(event["due_at"]) > epoch_now:
            return False
        self.pending = None
        if event["id"] in self.seen:
            return False
        return self._start(event, now)

    def _start(self, event, now):
        self.seen.append(event["id"])
        del self.seen[:-self.seen_limit]
        self.event = event
        self.started_at = float(now)
        return True

    def configure(self, enabled=None, duration_seconds=None):
        """Apply public runtime settings without changing transport settings."""
        if enabled is not None:
            self.enabled = bool(enabled)
        if duration_seconds is not None:
            try:
                self.duration_seconds = max(1, int(duration_seconds))
            except (TypeError, ValueError):
                pass
        if not self.enabled:
            self.clear()
            self.pending = None

    def active(self, now):
        return self.event is not None and float(now) - self.started_at < self.duration_seconds

    def screen(self):
        if self.event is None:
            return None
        event = self.event
        return {
            "id": "flash-" + event["id"],
            "kind": "flash",
            "title": "REMINDER",
            "label": event["label"],
            "due_at": event.get("due_at"),
            "duration_seconds": self.duration_seconds,
            "source": event.get("source", "unknown"),
        }

    def clear(self):
        self.event = None
        self.started_at = None
