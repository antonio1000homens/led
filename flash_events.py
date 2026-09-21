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
            end = value.find("Z", 20)
            if end < 0:
                end = value.find("+", 20)
            value = value[:end] if end >= 0 else value
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
    if not isinstance(event_id, str) or not event_id.strip() or payload.get("type") != "reminder":
        return None
    if not isinstance(label, str) or not label.strip():
        return None
    try:
        expires_at = _iso_epoch(payload.get("expires_at"))
        due_at = payload.get("due_at")
        if due_at is not None:
            _iso_epoch(due_at)
        if now is not None and expires_at <= float(now):
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

    def accept(self, payload, now, epoch_now=None):
        if not self.enabled:
            return False
        event = parse_flash_event(payload, epoch_now if epoch_now is not None else now)
        if event is None or event["id"] in self.seen:
            return False
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
