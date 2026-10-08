"""CircuitPython client-side helpers for the renderer-neutral screen API.

The module keeps hardware imports lazy so its rotation and clock logic can be
unit-tested on CPython.
"""

from formatting import (
    CALLING_STATION_FONT_WIDTH,
    departure_scroll_duration,
    rail_calling_timing,
)
from matrix_config import CALLING_SCROLL_SPEED_OVERRIDE


def _valid_rail_presentation(value):
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("calling_text"), str):
        return False
    segments = value.get("calling_segments")
    if not isinstance(segments, (list, tuple)) or not segments:
        return False
    for segment in segments:
        if (
            not isinstance(segment, dict)
            or not isinstance(segment.get("text"), str)
            or segment.get("role") not in ("station", "detail")
        ):
            return False
    numeric_fields = (
        "calling_station_width_px",
        "calling_travel_seconds",
        "calling_cycle_seconds",
        "train_cycle_seconds",
        "effective_duration_seconds",
    )
    for field in numeric_fields:
        number = value.get(field)
        if not isinstance(number, (int, float)) or number != number:
            return False
    if (
        value["calling_station_width_px"] < 0
        or value["calling_travel_seconds"] < 0
        or value["calling_cycle_seconds"] <= 0
        or value["train_cycle_seconds"] < 0
        or value["effective_duration_seconds"] <= 0
    ):
        return False
    if value["calling_cycle_seconds"] < value["calling_travel_seconds"]:
        return False
    return True


def _http_date_timestamp(value):
    """Normalize an HTTP Date header without CPython-only datetime imports."""
    if not isinstance(value, str):
        return None
    try:
        parts = value.split()
        if len(parts) != 6 or parts[5] != "GMT":
            return None
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        month = months.index(parts[2]) + 1
        year, day = int(parts[3]), int(parts[1])
        hour, minute, second = (int(part) for part in parts[4].split(":"))
        if not (2022 <= year <= 9999 and 1 <= day <= _days_in_month(year, month)
                and 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return None
        return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
            year, month, day, hour, minute, second)
    except (ValueError, IndexError):
        return None


def _weekday_sunday_zero(year, month, day):
    """Return 0=Sunday .. 6=Saturday for a Gregorian date."""
    offsets = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    adjusted_year = year - 1 if month < 3 else year
    return (
        adjusted_year
        + adjusted_year // 4
        - adjusted_year // 100
        + adjusted_year // 400
        + offsets[month - 1]
        + day
    ) % 7


def _last_sunday(year, month):
    day = 31
    return day - _weekday_sunday_zero(year, month, day)


def _is_london_bst(year, month, day, hour):
    """British Summer Time runs 01:00 UTC last Sunday Mar to Oct."""
    if month < 3 or month > 10:
        return False
    if 3 < month < 10:
        return True
    boundary = _last_sunday(year, month)
    if month == 3:
        return day > boundary or (day == boundary and hour >= 1)
    return day < boundary or (day == boundary and hour < 1)


def _is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    return (31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month - 1]


def _shift_date(year, month, day, delta_days):
    """Shift a Gregorian date by a small integer number of days."""
    delta_days = int(delta_days or 0)
    while delta_days > 0:
        day += 1
        if day > _days_in_month(year, month):
            day = 1
            month += 1
            if month > 12:
                month = 1
                year += 1
        delta_days -= 1
    while delta_days < 0:
        day -= 1
        if day < 1:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
            day = _days_in_month(year, month)
        delta_days += 1
    return year, month, day


def _parse_utc_timestamp(value):
    if not isinstance(value, str) or len(value) < 19:
        raise ValueError("fetched_at must be an ISO UTC timestamp")
    try:
        year = int(value[0:4])
        month = int(value[5:7])
        day = int(value[8:10])
        hour = int(value[11:13])
        minute = int(value[14:16])
        second = int(value[17:19])
    except (TypeError, ValueError):
        raise ValueError("fetched_at must be an ISO UTC timestamp")
    return year, month, day, hour, minute, second


def _utc_epoch_from_parts(year, month, day, hour, minute, second):
    """Convert a validated UTC date/time tuple to Unix epoch seconds."""
    years = year - 1
    days = years * 365 + years // 4 - years // 100 + years // 400
    month_days = (31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31)
    days += sum(month_days[:month - 1]) + day - 1
    epoch_years = 1969
    epoch_days = epoch_years * 365 + epoch_years // 4 - epoch_years // 100 + epoch_years // 400
    return (days - epoch_days) * 86400 + hour * 3600 + minute * 60 + second


def london_date_and_seconds_from_utc(value):
    """Convert an ISO UTC timestamp to London local date and seconds."""
    year, month, day, hour, minute, second = _parse_utc_timestamp(value)
    offset = 3600 if _is_london_bst(year, month, day, hour) else 0
    total = hour * 3600 + minute * 60 + second + offset
    day_delta, seconds = divmod(total, 86400)
    year, month, day = _shift_date(year, month, day, day_delta)
    return year, month, day, seconds


def london_seconds_from_utc(value):
    """Convert an ISO UTC timestamp to London seconds since local midnight."""
    return london_date_and_seconds_from_utc(value)[3]


class ClockState:
    """Advance backend-provided London date/time locally between API polls."""

    def __init__(self):
        self._date = None
        self._seconds = None
        self._epoch = None
        self._synced_at = None
        self._text_minute = None
        self._text_value = None
        self._date_day = None
        self._date_value = None

    def sync(self, fetched_at, now):
        year, month, day, hour, minute, second = _parse_utc_timestamp(fetched_at)
        local_year, local_month, local_day, seconds = london_date_and_seconds_from_utc(fetched_at)
        self._date = (local_year, local_month, local_day)
        self._seconds = seconds
        self._epoch = _utc_epoch_from_parts(year, month, day, hour, minute, second)
        self._synced_at = now
        self._text_minute = None
        self._text_value = None
        self._date_day = None
        self._date_value = None

    def epoch(self, now):
        """Return UTC epoch time derived from the last API timestamp."""
        if self._epoch is None or self._synced_at is None:
            return None
        # CircuitPython's 32-bit float cannot represent epoch seconds precisely.
        # Keep epoch arithmetic integral; only uptime/duration uses floats.
        return self._epoch + max(0, int(now - self._synced_at))

    def _parts(self, now):
        if self._date is None or self._seconds is None or self._synced_at is None:
            return None
        total = self._seconds + max(0, int(now - self._synced_at))
        day_delta, seconds = divmod(total, 86400)
        year, month, day = _shift_date(self._date[0], self._date[1], self._date[2], day_delta)
        return year, month, day, seconds

    def text(self, now):
        if self._date is None or self._seconds is None or self._synced_at is None:
            return "--:--"
        total = self._seconds + max(0, int(now - self._synced_at))
        minute_index = total // 60
        if minute_index != self._text_minute:
            seconds = total % 86400
            hour = seconds // 3600
            minute = (seconds % 3600) // 60
            self._text_value = "{:02d}:{:02d}".format(hour, minute)
            self._text_minute = minute_index
        return self._text_value

    def date_text(self, now):
        if self._date is None or self._seconds is None or self._synced_at is None:
            return ""
        total = self._seconds + max(0, int(now - self._synced_at))
        day_delta = total // 86400
        if day_delta != self._date_day:
            year, month, day = _shift_date(
                self._date[0], self._date[1], self._date[2], day_delta
            )
            self._date_value = "{:04d}-{:02d}-{:02d}".format(year, month, day)
            self._date_day = day_delta
        return self._date_value


class ScreenRotation:
    """Rotate server-provided screens without resetting on every data poll."""

    def __init__(self):
        self.screens = []
        self.http_screens = []
        self.mqtt_screens = []
        self.index = 0
        self.started_at = None
        self._paused = None
        self.cycle_number = 0
        self._shown_once = {}

    def update(self, screens, now):
        """Replace the HTTP collection, retaining the legacy single-source API."""
        self.http_screens = self._prepare_screens(screens)
        self._rebuild(now)

    def update_sources(self, http_screens, mqtt_screens, now):
        """Replace both independent sources and derive their effective order."""
        self.http_screens = self._prepare_screens(http_screens)
        self.mqtt_screens = self._prepare_screens(mqtt_screens)
        self._rebuild(now)

    def _prepare_screens(self, screens):
        next_screens = []
        for source in (screens or []):
            if not isinstance(source, dict):
                continue
            screen = source
            services = source.get("services") or ()
            if source.get("kind") == "rail_combined" and services:
                presentation = source.get("rail_presentation")
                prepared = _valid_rail_presentation(presentation)
                # A board-local speed experiment invalidates backend speed-
                # dependent timings, but not the additive text/segment data.
                recalculate = CALLING_SCROLL_SPEED_OVERRIDE is not None or not prepared
                screen = dict(source)
                if recalculate:
                    scroll_speed = (
                        CALLING_SCROLL_SPEED_OVERRIDE
                        if CALLING_SCROLL_SPEED_OVERRIDE is not None
                        else screen.get("station_scroll_speed", 20)
                    )
                    if CALLING_SCROLL_SPEED_OVERRIDE is not None:
                        # Keep the renderer and locally recalculated timing on
                        # the same physical-board experiment speed.
                        screen["station_scroll_speed"] = scroll_speed
                    travel_seconds, calling_duration = rail_calling_timing(
                        services, scroll_speed,
                        font_width=CALLING_STATION_FONT_WIDTH,
                    )
                    calling_seconds = int(calling_duration + 0.999)
                    train_cycle_seconds = int(departure_scroll_duration(
                        len(services[1:]),
                        source.get("upcoming_train_pause_seconds", 2),
                    ) + 0.999)
                    duration = max(
                        1,
                        int(source.get("duration_seconds") or 8),
                        calling_seconds,
                        train_cycle_seconds,
                    )
                    screen["calling_seconds"] = duration
                    screen["summary_seconds"] = 0
                    screen["effective_duration_seconds"] = duration
                    if prepared:
                        presentation = dict(presentation)
                        presentation["calling_travel_seconds"] = travel_seconds
                        presentation["calling_cycle_seconds"] = calling_duration
                        presentation["calling_seconds"] = duration
                        presentation["summary_seconds"] = 0
                        presentation["effective_duration_seconds"] = duration
                        screen["rail_presentation"] = presentation
                    else:
                        screen.pop("rail_presentation", None)
                        screen["_calling_travel_seconds"] = travel_seconds
                else:
                    screen["calling_seconds"] = presentation.get("calling_seconds", presentation["effective_duration_seconds"])
                    screen["summary_seconds"] = presentation.get("summary_seconds", 0)
                    screen["effective_duration_seconds"] = presentation["effective_duration_seconds"]
            next_screens.append(screen)
        return next_screens

    def _rebuild(self, now):
        if self.screens:
            self.current(now)
        old_screens = self.screens
        old_index = self.index % len(old_screens) if old_screens else 0
        old_current = old_screens[old_index] if old_screens else None
        old_id = old_current.get("id") if old_current else None
        old_phase = (
            self._paused[1] if self._paused is not None
            else max(0, now - self.started_at) if self.started_at is not None
            else 0
        )
        mqtt = sorted(self.mqtt_screens, key=lambda screen: str(screen.get("id") or ""))
        next_screens = list(self.http_screens) + mqtt
        self.screens = next_screens
        if not next_screens:
            self.cycle_number = 0
            self.index = 0
            self.started_at = None
            return
        if old_current is None:
            self.index = 0
            self.started_at = now
            return
        for index, screen in enumerate(next_screens):
            if screen.get("id") == old_id:
                self.index = index
                self.started_at = now - old_phase
                return
        # The visible slot was removed. Select the next surviving old screen
        # in the former cycle and start it with a clean phase.
        for offset in range(1, len(old_screens) + 1):
            candidate_id = old_screens[(old_index + offset) % len(old_screens)].get("id")
            for index, screen in enumerate(next_screens):
                if screen.get("id") == candidate_id:
                    self.index = index
                    self.started_at = now
                    if self._paused is not None:
                        self._paused = (candidate_id, 0)
                    return
        self.index = min(old_index, len(next_screens) - 1)
        self.started_at = now
        if self._paused is not None:
            self._paused = (self.screens[self.index].get("id"), 0)

    def current(self, now):
        if not self.screens:
            return {
                "id": "unavailable",
                "kind": "message",
                "duration_seconds": 8,
                "title": "Display unavailable",
                "source": "unavailable",
                "stale": True,
            }, 0
        if self._paused is not None:
            paused_id, paused_phase = self._paused
            for index, screen in enumerate(self.screens):
                if screen.get("id") == paused_id:
                    self.index = index
                    return screen, paused_phase
            # The interrupted screen disappeared while an overlay was shown.
            self._paused = (self.screens[self.index % len(self.screens)].get("id"), 0)
            return self.screens[self.index % len(self.screens)], 0
        if self.started_at is None:
            self.started_at = now
        skipped = 0
        while True:
            screen = self.screens[self.index]
            interval = max(1, int(screen.get("display_every_cycles") or 1))
            once_key = (screen.get("joke") if screen.get("kind") == "dad_joke"
                        else screen.get("fact") if screen.get("kind") == "random_fact" else None)
            already_shown = once_key is not None and self._shown_once.get(screen.get("id")) == once_key
            if self.cycle_number % interval or already_shown:
                self._advance_screen()
                skipped += 1
                if skipped >= len(self.screens):
                    # All screens were suppressed. Avoid a tight infinite loop.
                    return {
                        "id": "unavailable", "kind": "message",
                        "duration_seconds": 8, "title": "Waiting for new content",
                        "source": "local", "stale": False,
                    }, 0
                continue
            skipped = 0
            duration = max(
                1.0,
                float(screen.get("effective_duration_seconds") or screen.get("duration_seconds") or 8),
            )
            if "_calling_travel_seconds" in screen:
                duration = max(1, duration, int(screen.get("duration_seconds") or 8))
            elapsed = max(0, now - self.started_at)
            if elapsed < duration:
                return screen, elapsed
            self.started_at += duration
            if once_key is not None:
                self._shown_once[screen.get("id")] = once_key
            self._advance_screen()

    def _advance_screen(self):
        self.index += 1
        if self.index >= len(self.screens):
            self.index = 0
            self.cycle_number += 1

    def next(self, now):
        """Move immediately to the next screen and restart its duration."""
        if not self.screens:
            return
        screen, _ = self.current(now)
        if screen.get("kind") in ("dad_joke", "random_fact"):
            self._shown_once[screen.get("id")] = (
                screen.get("joke") if screen.get("kind") == "dad_joke" else screen.get("fact")
            )
        self._advance_screen()
        self.started_at = now

    def pause(self, now):
        """Freeze rotation and return the interrupted screen/phase."""
        screen, phase = self.current(now)
        return screen, phase

    def freeze(self, now):
        """Pause normal rotation for an interrupting overlay."""
        screen, phase = self.current(now)
        self._paused = (screen.get("id"), phase)
        return screen, phase

    def resume(self, now, screen, phase):
        """Resume the captured screen without restarting the full rotation."""
        if not self.screens:
            self._paused = None
            return
        paused_state = self._paused
        paused_id = paused_state[0] if paused_state is not None else None
        self._paused = None
        screen_id = screen.get("id") if isinstance(screen, dict) else None
        if not any(candidate.get("id") == screen_id for candidate in self.screens):
            screen_id = paused_id
        for index, candidate in enumerate(self.screens):
            if candidate.get("id") == screen_id:
                self.index = index
                resumed_phase = paused_state[1] if screen_id == paused_id else phase
                self.started_at = float(now) - max(0, float(resumed_phase or 0))
                return


class ScreenClient:
    """Fetch `/api/screens` from the LAN backend using CircuitPython Wi-Fi."""

    def __init__(self, settings, session=None):
        self.settings = settings
        self.session = session
        self._managed_session = session is None

    def _ensure_session(self):
        if not self._managed_session:
            return

        import time
        import rtc
        import wifi

        if not wifi.radio.connected:
            wifi.radio.connect(self.settings.WIFI_SSID, self.settings.WIFI_PASSWORD)

        if self.session is None:
            import adafruit_connection_manager
            import adafruit_ntp
            import adafruit_requests

            pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
            # ESP32-S3 RTC time is lost on power removal. Set it before TLS
            # certificate validation, otherwise HTTPS fails with an mbedTLS
            # certificate-time error on a freshly powered board.
            if time.localtime().tm_year < 2022:
                print("Setting system time from NTP")
                ntp = adafruit_ntp.NTP(pool, tz_offset=0, cache_seconds=3600)
                rtc.RTC().datetime = ntp.datetime
            ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
            try:
                with open("/gtsr4.pem", "r") as certificate:
                    ssl_context.load_verify_locations(cadata=certificate.read())
                print("Loaded GTS Root R4 certificate")
            except (AttributeError, OSError, TypeError) as error:
                print("GTS Root R4 certificate unavailable:", error)
            self.session = adafruit_requests.Session(pool, ssl_context)

    def fetch(self):
        self._ensure_session()
        base = str(self.settings.SCREEN_API_URL).rstrip("/")
        if not base:
            raise ValueError("SCREEN_API_URL is required for api mode")
        response = None
        try:
            response = self.session.get(base + "/api/screens")
            status_code = getattr(response, "status_code", None)
            if status_code is not None:
                if status_code < 200 or status_code >= 300:
                    raise ValueError("Screen API returned HTTP {}".format(status_code))
            else:
                # Keep compatibility with the CPython test double and
                # requests-like sessions that expose raise_for_status().
                response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("screens"), list):
                raise ValueError("Invalid screen API response")
            # fetched_at is the screen-data age, not the current wall clock.
            # The response Date advances even while that payload is cached.
            headers = getattr(response, "headers", {}) or {}
            clock_at = _http_date_timestamp(headers.get("date") or headers.get("Date"))
            if clock_at:
                payload["clock_at"] = clock_at
            return payload
        finally:
            if response is not None:
                response.close()
