"""Independent, bounded ICS provider for the LED Cubs agenda.

Only normalised event titles and start times leave this module.  Private ICS
URLs are read from LED-account SSM SecureString parameters at fetch time.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from ipaddress import ip_address
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

LOCAL_ZONE = ZoneInfo("Europe/London")
MAX_ICS_BYTES = 1024 * 1024
MAX_EVENTS = 12
MAX_CACHE_EVENTS = 100
MAX_HORIZON_DAYS = 366
DAY_CODES = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _safe_url(url):
    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise ValueError("Cubs calendar requires a valid HTTPS endpoint")
    if hostname == "localhost" or hostname.endswith((".local", ".internal")):
        raise ValueError("Cubs calendar endpoint is not public")
    try:
        if not ip_address(hostname).is_global:
            raise ValueError("Cubs calendar endpoint is not public")
    except ValueError as error:
        if str(error) == "Cubs calendar endpoint is not public":
            raise
    return url


def _unescape(value):
    value = value.replace("\\n", "\n").replace("\\N", "\n")
    return value.replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _unfold(text):
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n ", "").replace("\n\t", "")


def _parse_date(value, tzid=None):
    if not value:
        return None
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        return datetime.strptime(value, "%Y%m%d").replace(tzinfo=LOCAL_ZONE)
    utc = value.endswith("Z")
    raw = value[:-1] if utc else value
    fmt = "%Y%m%dT%H%M%S" if len(raw) == 15 else "%Y%m%dT%H%M"
    try:
        parsed = datetime.strptime(raw, fmt)
        zone = timezone.utc if utc else ZoneInfo(tzid or "Europe/London")
        return parsed.replace(tzinfo=zone).astimezone(LOCAL_ZONE)
    except (ValueError, KeyError):
        return None


def _read_vevents(text):
    events = []
    current = None
    for line in _unfold(text).split("\n"):
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None and ":" in line:
            left, value = line.split(":", 1)
            parts = left.split(";")
            key = parts[0].upper()
            params = {}
            for param in parts[1:]:
                if "=" in param:
                    name, setting = param.split("=", 1)
                    params[name.upper()] = setting.strip('"')
            if key in ("EXDATE", "RDATE"):
                current.setdefault(key, []).extend(
                    (_parse_date(item, params.get("TZID")) for item in value.split(","))
                )
            elif key in ("DTSTART", "DTEND", "RECURRENCE-ID"):
                current[key] = _parse_date(value, params.get("TZID"))
                if key == "DTSTART":
                    current["ALL_DAY"] = params.get("VALUE") == "DATE" or len(value) == 8
            elif key in ("SUMMARY", "UID", "STATUS", "RRULE"):
                current[key] = _unescape(value).strip()
    return [event for event in events if event.get("DTSTART") is not None and (event.get("SUMMARY") or (event.get("RECURRENCE-ID") is not None and event.get("STATUS", "").upper() == "CANCELLED"))]


def _rule_matches(day, first, rule):
    interval = max(1, int(rule.get("INTERVAL", "1")))
    difference = (day - first).days
    if difference < 0:
        return False
    freq = rule.get("FREQ")
    if freq == "DAILY":
        matched = difference % interval == 0
    elif freq == "WEEKLY":
        weekdays = [DAY_CODES[code] for code in rule.get("BYDAY", "").split(",") if code in DAY_CODES]
        matched = (difference // 7) % interval == 0 and day.weekday() in (weekdays or [first.weekday()])
    elif freq == "MONTHLY":
        months = (day.year - first.year) * 12 + day.month - first.month
        values = [int(x) for x in rule.get("BYMONTHDAY", "").split(",") if x.lstrip("-").isdigit()]
        matched = months >= 0 and months % interval == 0 and day.day in (values or [first.day])
    elif freq == "YEARLY":
        years = day.year - first.year
        months = [int(x) for x in rule.get("BYMONTH", "").split(",") if x.isdigit()]
        days = [int(x) for x in rule.get("BYMONTHDAY", "").split(",") if x.isdigit()]
        matched = years >= 0 and years % interval == 0 and day.month in (months or [first.month]) and day.day in (days or [first.day])
    else:
        matched = difference == 0
    return matched


def _occurrences(event, now):
    start = event["DTSTART"]
    recurrence = event.get("RRULE")
    if not recurrence:
        yield start
        return
    try:
        rule = dict(item.split("=", 1) for item in recurrence.split(";") if "=" in item)
        count = max(0, min(100000, int(rule.get("COUNT", "100000"))))
        until = _parse_date(rule.get("UNTIL"))
        horizon = now + timedelta(days=MAX_HORIZON_DAYS)
        end_day = min(horizon.date(), until.date() if until else horizon.date())
        cursor = start.date()
        seen = 0
        # Hard bound prevents malformed recurrence rules from exhausting Lambda.
        for _ in range(365 * 60):
            if cursor > end_day or seen >= count:
                break
            if _rule_matches(cursor, start.date(), rule):
                # Calendar instances in local time stay at the same wall-clock hour
                # across British Summer Time transitions.
                occurrence = datetime.combine(cursor, start.time(), tzinfo=LOCAL_ZONE)
                if until is None or occurrence <= until:
                    seen += 1
                    yield occurrence
            cursor += timedelta(days=1)
    except (TypeError, ValueError, OverflowError):
        # Malformed recurrence must not cause an unbounded refresh or leak data.
        yield start


def parse_cubs_events(text, now=None, max_events=MAX_EVENTS):
    """Return public-safe, sorted upcoming agenda rows from ICS text."""
    now = (now or datetime.now(timezone.utc)).astimezone(LOCAL_ZONE)
    records = _read_vevents(text)
    exceptions = {}
    for event in records:
        recurrence_id = event.get("RECURRENCE-ID")
        if recurrence_id is not None:
            exceptions[(event.get("UID"), recurrence_id.astimezone(timezone.utc))] = event
    result = []
    seen = set()
    for event in records:
        if event.get("RECURRENCE-ID") is not None or event.get("STATUS", "").upper() == "CANCELLED":
            continue
        duration = (event.get("DTEND") or (event["DTSTART"] + timedelta(days=1 if event.get("ALL_DAY") else 0))) - event["DTSTART"]
        if duration.total_seconds() < 0:
            duration = timedelta(0)
        excluded = {entry.astimezone(timezone.utc) for entry in event.get("EXDATE", []) if entry}
        for original in _occurrences(event, now):
            instant = original.astimezone(timezone.utc)
            if instant in excluded:
                continue
            override = exceptions.get((event.get("UID"), instant))
            if override and override.get("STATUS", "").upper() == "CANCELLED":
                continue
            instance = override or event
            begins = instance["DTSTART"] if override else original
            ends = begins + duration
            if ends <= now and begins < now:
                continue
            if begins > now + timedelta(days=MAX_HORIZON_DAYS):
                continue
            local = begins.astimezone(LOCAL_ZONE)
            title = " ".join(instance["SUMMARY"].split())[:120]
            if not title:
                continue
            key = (title.casefold(), begins.astimezone(timezone.utc))
            if key in seen:
                continue
            seen.add(key)
            result.append({
                "start": local.date().isoformat() if instance.get("ALL_DAY") else local.isoformat(),
                "all_day": bool(instance.get("ALL_DAY")),
                "date_text": local.strftime("%d/%m"),
                "time_text": "" if instance.get("ALL_DAY") else local.strftime("%H:%M"),
                "title": title,
            })
    result.sort(key=lambda item: (item["start"][:10], item["time_text"], item["title"]))
    return result[:max(1, min(MAX_CACHE_EVENTS, max_events))]


class CubsCalendarProvider:
    """Fetch separately configured upstream feeds using only LED-account SSM."""

    def __init__(self, programme_parameter, events_parameter="", ssm=None, opener=None, utcnow=None):
        self.programme_parameter = programme_parameter
        self.events_parameter = events_parameter
        self.ssm = ssm
        self.opener = opener or urlopen
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))

    def _parameter(self, name):
        if not name:
            return ""
        if self.ssm is None:
            import boto3
            self.ssm = boto3.client("ssm")
        try:
            return self.ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
        except Exception:
            # Parameter values and upstream URLs must never enter logs.
            return ""

    def _download(self, url):
        _safe_url(url)
        try:
            with self.opener(Request(url, headers={"Accept": "text/calendar"}), timeout=12) as response:
                _safe_url(response.geturl())
                raw = response.read(MAX_ICS_BYTES + 1)
                if len(raw) > MAX_ICS_BYTES:
                    raise ValueError("Cubs ICS response exceeds maximum size")
                return raw.decode("utf-8-sig")
        except Exception:
            raise RuntimeError("Cubs ICS upstream fetch failed") from None

    def fetch(self):
        combined = []
        configured = False
        failed = False
        for name in (self.programme_parameter, self.events_parameter):
            url = self._parameter(name)
            if not url:
                continue
            configured = True
            try:
                combined.append(self._download(url))
            except Exception:
                failed = True
        if not configured:
            raise RuntimeError("Cubs ICS parameter not configured")
        if not combined:
            raise RuntimeError("All configured Cubs ICS feeds failed")
        # Combine before de-duplicating, retaining individual VEVENT boundaries.
        contents = "\n".join(combined)
        events = parse_cubs_events(contents, now=self.utcnow(), max_events=MAX_CACHE_EVENTS)
        if failed:
            raise RuntimeError("A configured Cubs ICS feed failed; retain previous cache")
        return events
