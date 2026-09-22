"""CircuitPython client-side helpers for the renderer-neutral screen API.

The module keeps hardware imports lazy so its rotation and clock logic can be
unit-tested on CPython.
"""


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

    def sync(self, fetched_at, now):
        year, month, day, hour, minute, second = _parse_utc_timestamp(fetched_at)
        _, _, _, seconds = london_date_and_seconds_from_utc(fetched_at)
        self._date = (year, month, day)
        self._seconds = seconds
        self._epoch = _utc_epoch_from_parts(year, month, day, hour, minute, second)
        self._synced_at = now

    def epoch(self, now):
        """Return UTC epoch time derived from the last API timestamp."""
        if self._epoch is None or self._synced_at is None:
            return None
        return self._epoch + max(0, now - self._synced_at)

    def _parts(self, now):
        if self._date is None or self._seconds is None or self._synced_at is None:
            return None
        total = self._seconds + max(0, int(now - self._synced_at))
        day_delta, seconds = divmod(total, 86400)
        year, month, day = _shift_date(self._date[0], self._date[1], self._date[2], day_delta)
        return year, month, day, seconds

    def text(self, now):
        parts = self._parts(now)
        if parts is None:
            return "--:--"
        seconds = parts[3]
        hour = seconds // 3600
        minute = (seconds % 3600) // 60
        return "{:02d}:{:02d}".format(hour, minute)

    def date_text(self, now):
        parts = self._parts(now)
        if parts is None:
            return ""
        return "{:04d}-{:02d}-{:02d}".format(parts[0], parts[1], parts[2])


class ScreenRotation:
    """Rotate server-provided screens without resetting on every data poll."""

    def __init__(self):
        self.screens = []
        self.index = 0
        self.started_at = None

    def update(self, screens, now):
        next_screens = [screen for screen in (screens or []) if isinstance(screen, dict)]
        if not next_screens:
            return
        current_id = None
        if self.screens:
            current_id = self.screens[self.index % len(self.screens)].get("id")
        self.screens = next_screens
        if self.started_at is None:
            self.index = 0
            self.started_at = now
            return
        if current_id:
            for index, screen in enumerate(self.screens):
                if screen.get("id") == current_id:
                    self.index = index
                    return
        self.index = min(self.index, len(self.screens) - 1)

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
        if self.started_at is None:
            self.started_at = now
        while True:
            screen = self.screens[self.index]
            duration = max(
                1,
                int(screen.get("effective_duration_seconds") or screen.get("duration_seconds") or 8),
            )
            elapsed = max(0, now - self.started_at)
            if elapsed < duration:
                return screen, elapsed
            self.started_at += duration
            self.index = (self.index + 1) % len(self.screens)

    def next(self, now):
        """Move immediately to the next screen and restart its duration."""
        if not self.screens:
            return
        self.current(now)
        self.index = (self.index + 1) % len(self.screens)
        self.started_at = now

    def pause(self, now):
        """Freeze rotation and return the interrupted screen/phase."""
        screen, phase = self.current(now)
        return screen, phase

    def resume(self, now, screen, phase):
        """Resume the captured screen without restarting the full rotation."""
        if not self.screens:
            return
        screen_id = screen.get("id") if isinstance(screen, dict) else None
        for index, candidate in enumerate(self.screens):
            if candidate.get("id") == screen_id:
                self.index = index
                self.started_at = float(now) - max(0, float(phase or 0))
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
            return payload
        finally:
            if response is not None:
                response.close()
