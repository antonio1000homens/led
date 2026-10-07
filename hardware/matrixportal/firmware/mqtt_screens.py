"""Validation and expiry state for retained MQTT cycle screens."""

import json


def _leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _epoch(value):
    """Parse ISO-8601 with Z or an explicit offset into integer UTC milliseconds."""
    if not isinstance(value, str) or len(value) < 20:
        raise ValueError("timestamp")
    try:
        year, month, day = int(value[:4]), int(value[5:7]), int(value[8:10])
        hour, minute, second = int(value[11:13]), int(value[14:16]), int(value[17:19])
        if value[4] != "-" or value[7] != "-" or value[10] != "T" or value[13] != ":" or value[16] != ":":
            raise ValueError("timestamp")
        days_month = (31, 29 if _leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        if not (1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= days_month[month - 1]
                and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            raise ValueError("timestamp")
        suffix = value[19:]
        fraction_ms = 0
        if suffix[:1] in (".", ","):
            index = 1
            while index < len(suffix) and suffix[index].isdigit():
                index += 1
            fraction = suffix[1:index]
            if not fraction:
                raise ValueError("timestamp")
            fraction_ms = int((fraction + "00")[:3])
            suffix = suffix[index:]
        offset = 0
        if suffix == "Z":
            pass
        elif len(suffix) == 6 and suffix[0] in ("+", "-") and suffix[3] == ":":
            oh, om = int(suffix[1:3]), int(suffix[4:6])
            if oh > 23 or om > 59:
                raise ValueError("timestamp")
            offset = (oh * 3600 + om * 60) * (1 if suffix[0] == "+" else -1)
        else:
            raise ValueError("timestamp")
        years = year - 1
        days = years * 365 + years // 4 - years // 100 + years // 400
        days += sum(days_month[:month - 1]) + day - 1
        epoch_years = 1969
        epoch_days = epoch_years * 365 + epoch_years // 4 - epoch_years // 100 + epoch_years // 400
        seconds = (days - epoch_days) * 86400 + hour * 3600 + minute * 60 + second - offset
        return seconds * 1000 + fraction_ms
    except (TypeError, ValueError, IndexError):
        raise ValueError("timestamp")


def _positive_finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        number = float(value)
        return number > 0 and number == number and number != float("inf")
    except (TypeError, ValueError, OverflowError):
        return False


def _valid_screen(screen, slot):
    if not isinstance(screen, dict):
        return False
    if not isinstance(screen.get("id"), str) or not screen["id"].strip() or screen["id"] != slot:
        return False
    if screen.get("kind") != "bin_collection" or not _positive_finite(screen.get("duration_seconds")):
        return False
    if not _positive_finite(screen.get("slide_speed")):
        return False
    date = screen.get("collection_date")
    if not isinstance(date, str) or len(date) != 10:
        return False
    try:
        _epoch(date + "T00:00:00Z")
    except ValueError:
        return False
    collections = screen.get("collections")
    if not isinstance(collections, list) or not 1 <= len(collections) <= 2:
        return False
    collection_ids = []
    for item in collections:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            return False
        if not isinstance(item.get("label"), str) or not item["label"].strip():
            return False
        if item["id"] in collection_ids:
            return False
        collection_ids.append(item["id"])
    return isinstance(screen.get("title"), str) and bool(screen["title"].strip())


class MqttScreenState:
    """Keep per-slot ordering metadata and active renderer payload snapshots."""

    PREFIX = "led/screens/"

    def __init__(self, topic_filter="led/screens/+"):
        if (
            not isinstance(topic_filter, str)
            or not topic_filter.endswith("/+")
            or "+" in topic_filter[:-1]
            or "#" in topic_filter
        ):
            raise ValueError("MQTT_SCREENS_TOPIC must be a single-level wildcard")
        self.prefix = topic_filter[:-1]
        self._slots = {}
        self._published = {}

    def accept(self, topic, payload, now_epoch):
        """Accept a slot update; invalid or expired messages leave state intact."""
        if not isinstance(topic, str) or not topic.startswith(self.prefix):
            return False
        slot = topic[len(self.prefix):]
        if not slot or not slot.strip() or any(char in slot for char in ("/", "+", "#", "\x00")):
            return False
        try:
            if isinstance(payload, (bytes, bytearray)):
                payload = payload.decode("utf-8")
            message = json.loads(payload) if isinstance(payload, str) else payload
            version = message.get("schema_version") if isinstance(message, dict) else None
            if not isinstance(message, dict) or isinstance(version, bool) or not isinstance(version, int) or version != 1:
                return False
            event = message.get("event")
            if event not in ("upsert", "clear"):
                return False
            published = _epoch(message.get("published_at"))
            if slot in self._published and published < self._published[slot]:
                return False
            screen = None
            expires = None
            if event == "upsert":
                expires = _epoch(message.get("expires_at"))
                if expires <= int(now_epoch) * 1000 or not _valid_screen(message.get("screen"), slot):
                    return False
                screen = message["screen"]
            previous = self._slots.get(slot)
            if published == self._published.get(slot) and (
                previous is None and screen is None
                or previous is not None and previous == (expires, screen)
            ):
                return False
            self._published[slot] = published
            if event == "clear":
                self._slots.pop(slot, None)
            else:
                self._slots[slot] = (expires, screen)
            return True
        except (ValueError, TypeError, UnicodeError, OverflowError):
            return False

    def expire(self, now_epoch):
        removed = []
        for slot, (expires, _) in tuple(self._slots.items()):
            if int(now_epoch) * 1000 >= expires:
                del self._slots[slot]
                removed.append(slot)
        return removed

    def screens(self, now_epoch):
        self.expire(now_epoch)
        return [self._slots[slot][1] for slot in sorted(self._slots)]
