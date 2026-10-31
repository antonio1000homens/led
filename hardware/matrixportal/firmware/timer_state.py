"""Validated controller for retained Alexa timer snapshots (contract v1)."""

SCHEMA_VERSION = 1
MAX_TIMERS = 8
MAX_LABEL_LENGTH = 40
MAX_ID_LENGTH = 80
MAX_DURATION_SECONDS = 7 * 24 * 60 * 60
COMPLETION_HOLD_SECONDS = 3
UPSTREAM_STALE_AFTER_SECONDS = 600
MAX_PAYLOAD_CHARACTERS = 4096


def format_countdown(remaining_seconds):
    remaining = max(0, int(remaining_seconds))
    hours, tail = divmod(remaining, 3600)
    minutes, seconds = divmod(tail, 60)
    if hours:
        return "{}:{:02d}:{:02d}".format(hours, minutes, seconds)
    return "{:02d}:{:02d}".format(minutes, seconds)


def car_position(clock_left, car_width, progress):
    progress = min(1.0, max(0.0, float(progress or 0)))
    finish_x = max(0, int(clock_left) - int(car_width))
    return int(round(finish_x * progress))


def _number(value, minimum, maximum, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("{} must be numeric".format(name))
    value = float(value)
    if value != value or value < minimum or value > maximum:
        raise ValueError("{} outside bounds".format(name))
    return value


def iso_epoch(value):
    """Parse an ISO-8601 timestamp with an explicit UTC offset."""
    if not isinstance(value, str) or len(value) < 20 or len(value) > 35:
        raise ValueError("timestamp must include an offset")
    try:
        year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
        hour, minute, second = int(value[11:13]), int(value[14:16]), int(value[17:19])
        if (value[4] != "-" or value[7] != "-" or value[10] != "T"
                or value[13] != ":" or value[16] != ":"
                or value[19] not in ("+", "-", "Z", ".", ",")
                or not 1 <= year <= 9999):
            raise ValueError("timestamp must include an offset")
        offset_start = 19
        if value[offset_start:offset_start + 1] in (".", ","):
            offset_start += 1
            fraction_start = offset_start
            while offset_start < len(value) and value[offset_start].isdigit():
                offset_start += 1
            if offset_start == fraction_start:
                raise ValueError("invalid fractional seconds")
        offset = value[offset_start:]
        if offset == "Z":
            offset_seconds = 0
        else:
            if len(offset) != 6 or offset[3] != ":":
                raise ValueError("invalid offset")
            offset_hours, offset_minutes = int(offset[1:3]), int(offset[4:6])
            if offset_hours > 23 or offset_minutes > 59:
                raise ValueError("invalid offset")
            offset_seconds = offset_hours * 3600 + offset_minutes * 60
            if offset[0] == "-":
                offset_seconds = -offset_seconds
        if not (1 <= month <= 12 and 0 <= hour <= 23 and 0 <= minute <= 59
                and 0 <= second <= 59):
            raise ValueError("invalid timestamp fields")
        days_in_month = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                         else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        if not 1 <= day <= days_in_month[month - 1]:
            raise ValueError("invalid calendar date")
        years = year - 1
        days = years * 365 + years // 4 - years // 100 + years // 400
        days += sum(days_in_month[:month - 1]) + day - 1
        epoch_years = 1969
        epoch_days = epoch_years * 365 + epoch_years // 4 - epoch_years // 100 + epoch_years // 400
        return (days - epoch_days) * 86400 + hour * 3600 + minute * 60 + second - offset_seconds
    except (TypeError, IndexError):
        raise ValueError("invalid ISO-8601 timestamp")


def validate_snapshot(payload, topic_device):
    if (not isinstance(payload, dict)
            or isinstance(payload.get("schema_version"), bool)
            or payload.get("schema_version") != SCHEMA_VERSION):
        raise ValueError("unsupported timer schema")
    if not set(payload).issubset({"schema_version", "event", "source", "device", "published_at", "timers"}):
        raise ValueError("unexpected timer snapshot field")
    if payload.get("source") != "homeassistant" or payload.get("device") != topic_device:
        raise ValueError("timer source does not match topic")
    published_at = iso_epoch(payload.get("published_at"))
    event = payload.get("event")
    if event == "clear":
        if "timers" in payload:
            raise ValueError("clear snapshots must not include timers")
        return {"event": "clear", "published_at": published_at, "timers": []}
    if event != "upsert":
        raise ValueError("unknown timer event")
    timers = payload.get("timers")
    if not isinstance(timers, list) or not timers or len(timers) > MAX_TIMERS:
        raise ValueError("upsert timers must be a non-empty bounded list")
    normalized = []
    seen = set()
    for item in timers:
        if not isinstance(item, dict):
            raise ValueError("timer must be an object")
        if not set(item).issubset({"timer_id", "state", "ends_at", "started_at", "remaining_seconds", "duration_seconds", "label"}):
            raise ValueError("unexpected timer field")
        timer_id = item.get("timer_id")
        if not isinstance(timer_id, str) or not timer_id or len(timer_id) > MAX_ID_LENGTH:
            raise ValueError("invalid timer id")
        if any(ord(character) > 127 or not (character.isalnum() or character in "._:-")
               for character in timer_id):
            raise ValueError("timer id contains unsupported characters")
        if timer_id in seen:
            raise ValueError("duplicate timer id")
        seen.add(timer_id)
        state = item.get("state")
        if state not in ("running", "paused"):
            raise ValueError("invalid timer state")
        timer = {"timer_id": timer_id, "state": state}
        if "started_at" in item:
            timer["started_epoch"] = iso_epoch(item["started_at"])
        label = item.get("label", "")
        if not isinstance(label, str) or len(label) > MAX_LABEL_LENGTH:
            raise ValueError("invalid timer label")
        timer["label"] = label
        duration = item.get("duration_seconds")
        if duration is not None:
            timer["duration_seconds"] = _number(duration, 1, MAX_DURATION_SECONDS, "duration_seconds")
        if state == "running":
            if "remaining_seconds" in item or "ends_at" not in item:
                raise ValueError("running timer requires ends_at only")
            timer["ends_epoch"] = iso_epoch(item.get("ends_at"))
        else:
            if "ends_at" in item or "remaining_seconds" not in item:
                raise ValueError("paused timer requires remaining_seconds only")
            timer["remaining_seconds"] = _number(
                item.get("remaining_seconds"), 0, MAX_DURATION_SECONDS, "remaining_seconds"
            )
        normalized.append(timer)
    return {"event": event, "published_at": published_at, "timers": normalized}


class TimerState:
    """Complete-snapshot store and deterministic visible timer selection."""

    def __init__(self, device="living-room-alexa"):
        self.device = device
        self.published_at = None
        self.timers = []
        self.completed_id = None
        self.completed_until = None
        self.completed_until_monotonic = None
        self.observed_durations = {}
        self.epoch_anchor = None
        self.monotonic_anchor = None
        self.received_at = None
        self.selection = {}

    def accept(self, payload, now_epoch, now_monotonic=None):
        import json
        try:
            if isinstance(payload, (bytes, bytearray)):
                if len(payload) > MAX_PAYLOAD_CHARACTERS:
                    return False, "payload_too_large"
                payload = payload.decode("utf-8")
            if isinstance(payload, str):
                if len(payload) > MAX_PAYLOAD_CHARACTERS:
                    return False, "payload_too_large"
                payload = json.loads(payload)
            snapshot = validate_snapshot(payload, self.device)
        except (ValueError, TypeError, UnicodeError) as error:
            return False, str(error)
        if self.published_at is not None and snapshot["published_at"] <= self.published_at:
            return False, "out_of_order"
        reference_epoch = now_epoch
        if reference_epoch is None and self.epoch_anchor is not None and now_monotonic is not None:
            reference_epoch = self.epoch_anchor + now_monotonic - self.monotonic_anchor
        if reference_epoch is not None and snapshot["published_at"] > reference_epoch + 300:
            return False, "published_at_in_future"
        if snapshot["event"] == "upsert":
            for timer in snapshot["timers"]:
                if timer["state"] == "running":
                    if reference_epoch is None:
                        return False, "clock_not_synchronized"
                    if timer["ends_epoch"] <= reference_epoch:
                        return False, "expired_running_timer"
                    if timer["ends_epoch"] - reference_epoch > MAX_DURATION_SECONDS:
                        return False, "timer_end_outside_bounds"
                    if now_monotonic is not None:
                        timer["ends_monotonic"] = now_monotonic + (timer["ends_epoch"] - reference_epoch)
        self.published_at = snapshot["published_at"]
        self.timers = snapshot["timers"]
        self.received_at = now_monotonic
        active_ids = {timer["timer_id"] for timer in self.timers}
        self.observed_durations = {
            timer_id: duration for timer_id, duration in self.observed_durations.items()
            if timer_id in active_ids
        }
        if now_epoch is not None and now_monotonic is not None:
            self.epoch_anchor = now_epoch
            self.monotonic_anchor = now_monotonic
        if snapshot["event"] == "clear":
            self.observed_durations = {}
            self.completed_id = self.completed_until = self.completed_until_monotonic = None
        return True, "accepted"

    def selected(self, now_epoch, now_monotonic=None):
        stale = (self.received_at is not None and now_monotonic is not None
                 and now_monotonic - self.received_at >= UPSTREAM_STALE_AFTER_SECONDS)
        if self.completed_id is not None:
            use_monotonic = now_monotonic is not None and self.completed_until_monotonic is not None
            hold_until = self.completed_until_monotonic if use_monotonic else self.completed_until
            hold_now = now_monotonic if use_monotonic else now_epoch
            if hold_until is not None and hold_now is not None and hold_now < hold_until:
                result = self.selection
                result["timer_id"] = self.completed_id
                result["state"] = "complete"
                result["remaining_seconds"] = 0
                result["duration_seconds"] = 1
                result["progress"] = 1.0
                result["label"] = ""
                result["stale"] = stale
                return result
            self.completed_id = self.completed_until = self.completed_until_monotonic = None

        timer = None
        running_end = None
        for candidate in self.timers:
            if candidate["state"] != "running":
                continue
            end = candidate.get("ends_monotonic") if now_monotonic is not None else None
            if end is None:
                end = candidate["ends_epoch"]
            if timer is None or end < running_end:
                timer, running_end = candidate, end
        if timer is not None:
            current = now_monotonic if "ends_monotonic" in timer and now_monotonic is not None else now_epoch
            remaining = max(0, running_end - current)
            if remaining == 0:
                self.completed_id = timer["timer_id"]
                if now_monotonic is not None:
                    self.completed_until_monotonic = now_monotonic + COMPLETION_HOLD_SECONDS
                    self.completed_until = now_epoch
                else:
                    self.completed_until = now_epoch + COMPLETION_HOLD_SECONDS
                self.timers = [item for item in self.timers if item["timer_id"] != timer["timer_id"]]
                self.observed_durations.pop(timer["timer_id"], None)
                result = self.selection
                result["timer_id"] = timer["timer_id"]
                result["state"] = "complete"
                result["remaining_seconds"] = 0
                result["duration_seconds"] = timer.get("duration_seconds")
                result["progress"] = 1.0
                result["label"] = ""
                result["stale"] = stale
                return result
        else:
            for candidate in self.timers:
                if candidate["state"] == "paused" and (
                        timer is None or candidate["remaining_seconds"] < timer["remaining_seconds"]):
                    timer = candidate
            if timer is None:
                return None
            remaining = timer["remaining_seconds"]

        duration = timer.get("duration_seconds")
        if duration is None:
            duration = self.observed_durations.get(timer["timer_id"])
            if duration is None:
                # A zero-second paused snapshot has no historical duration;
                # use a one-second visual baseline so progress stays defined.
                duration = max(1, remaining)
                self.observed_durations[timer["timer_id"]] = duration
        else:
            self.observed_durations[timer["timer_id"]] = duration
        result = self.selection
        result["timer_id"] = timer["timer_id"]
        result["state"] = timer["state"]
        result["remaining_seconds"] = remaining
        result["duration_seconds"] = duration
        result["progress"] = min(1.0, max(0.0, 1.0 - remaining / duration))
        result["label"] = timer.get("label", "")
        result["stale"] = stale
        return result
