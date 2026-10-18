"""Small five-field cron parser shared by the backend and MatrixPortal.

The supported syntax is numeric POSIX cron: ``*``, lists, ranges and steps.
Timezone conversion is deliberately outside this module; callers supply local
calendar fields (the LED application uses Europe/London).
"""


FIELD_RANGES = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))


def _field_values(text, minimum, maximum, sunday=False):
    values = set()
    for part in text.split(","):
        if not part:
            raise ValueError("empty cron list item")
        base, slash, step_text = part.partition("/")
        if slash:
            if not step_text.isdigit() or int(step_text) < 1:
                raise ValueError("cron step must be a positive integer")
            step = int(step_text)
        else:
            step = 1
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                raise ValueError("cron ranges must be numeric")
            start, end = int(start_text), int(end_text)
        else:
            if not base.isdigit():
                raise ValueError("cron values must be numeric")
            start = end = int(base)
            if slash:
                end = maximum
        if start < minimum or end > maximum or start > end:
            raise ValueError("cron value is outside its field range")
        for value in range(start, end + 1, step):
            values.add(0 if sunday and value == 7 else value)
    return values


def parse_cron_schedule(expression):
    """Validate and return the five sets of matching values."""
    if not isinstance(expression, str):
        raise ValueError("cron schedule must be text")
    expression = expression.strip()
    if not expression:
        return None
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("cron schedule must contain five fields")
    parsed = []
    for index, (text, bounds) in enumerate(zip(fields, FIELD_RANGES)):
        parsed.append(_field_values(text, bounds[0], bounds[1], sunday=index == 4))
    return tuple(parsed)


def cron_matches_local(expression, year, month, day, hour, minute):
    """Return whether a local date/time matches a validated cron schedule."""
    parsed = parse_cron_schedule(expression)
    if parsed is None:
        return True
    adjusted_year = year - 1 if month < 3 else year
    weekday = (adjusted_year + adjusted_year // 4 - adjusted_year // 100
               + adjusted_year // 400
               + (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)[month - 1] + day) % 7
    minute_values, hour_values, monthday_values, month_values, weekday_values = parsed
    if minute not in minute_values or hour not in hour_values or month not in month_values:
        return False
    dom_wild = expression.split()[2] == "*"
    dow_wild = expression.split()[4] == "*"
    dom_match = day in monthday_values
    dow_match = weekday in weekday_values
    if not dom_wild and not dow_wild:
        return dom_match or dow_match
    return dom_match and dow_match


def _days_before_year(year):
    prior = year - 1
    return prior * 365 + prior // 4 - prior // 100 + prior // 400


def _civil_from_days(days):
    """Return a Gregorian date for days since the Unix epoch."""
    days += _days_before_year(1970)
    low, high = 1, days // 365 + 2
    while low + 1 < high:
        middle = (low + high) // 2
        if _days_before_year(middle) <= days:
            low = middle
        else:
            high = middle
    year = low
    offset = days - _days_before_year(year)
    month_days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    month = 1
    while offset >= month_days[month - 1]:
        offset -= month_days[month - 1]
        month += 1
    return year, month, offset + 1


def _last_sunday(year, month):
    month_days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    day = month_days[month - 1]
    adjusted_year = year - 1 if month < 3 else year
    weekday = (adjusted_year + adjusted_year // 4 - adjusted_year // 100
               + adjusted_year // 400 + (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)[month - 1] + day) % 7
    return day - weekday


def _london_offset(epoch_minute):
    year, _, _ = _civil_from_days(epoch_minute // 1440)
    unix_epoch_day = _days_before_year(1970)
    start = (_days_before_year(year) - unix_epoch_day
             + sum((31, 28 + (1 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 0))[:2])
             + _last_sunday(year, 3) - 1) * 1440 + 60
    end = (_days_before_year(year) - unix_epoch_day
           + sum((31, 28 + (1 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 0), 31, 30, 31, 30, 31, 31, 30)[:9])
           + _last_sunday(year, 10) - 1) * 1440 + 60
    return 60 if start <= epoch_minute < end else 0


_PARSED_SCHEDULES = {}
_WINDOW_RESULT_CACHE = {}


def schedule_window_active(windows, epoch_seconds):
    """Whether a UTC instant lies in any Europe/London cron-start window."""
    if not windows:
        return True
    if isinstance(epoch_seconds, bool) or not isinstance(epoch_seconds, (int, float)):
        return False
    now = int(epoch_seconds // 60)
    try:
        cache_key = (repr(windows), now)
        if cache_key in _WINDOW_RESULT_CACHE:
            return _WINDOW_RESULT_CACHE[cache_key]
    except Exception:
        cache_key = None
    result = False
    for window in windows:
        if not isinstance(window, dict):
            continue
        try:
            expression = window["cron"]
            duration = window["duration_minutes"]
            if isinstance(duration, bool) or not isinstance(duration, int) or duration < 1:
                continue
            if expression not in _PARSED_SCHEDULES:
                if len(_PARSED_SCHEDULES) >= 128:
                    _PARSED_SCHEDULES.clear()
                _PARSED_SCHEDULES[expression] = parse_cron_schedule(expression)
            parsed = _PARSED_SCHEDULES[expression]
            if parsed is None:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        minute_values, hour_values, dom_values, month_values, dow_values = parsed
        local_now = now + _london_offset(now)
        local_day = local_now // 1440
        oldest_day = max((now - duration) // 1440 - 1, local_day - 32)
        for day in range(local_day, oldest_day - 1, -1):
            year, month, monthday = _civil_from_days(day)
            adjusted_year = year - 1 if month < 3 else year
            weekday = (adjusted_year + adjusted_year // 4 - adjusted_year // 100
                       + adjusted_year // 400
                       + (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)[month - 1] + monthday) % 7
            dom_wild = expression.split()[2] == "*"
            dow_wild = expression.split()[4] == "*"
            date_match = ((monthday in dom_values or weekday in dow_values)
                          if not dom_wild and not dow_wild
                          else monthday in dom_values and weekday in dow_values)
            if month in month_values and date_match:
                for hour in sorted(hour_values, reverse=True):
                    for minute in sorted(minute_values, reverse=True):
                        local_start = day * 1440 + hour * 60 + minute
                        for assumed_offset in (0, 60):
                            start = local_start - assumed_offset
                            age = now - start
                            if age < 0 or age >= duration:
                                continue
                            if _london_offset(start) == assumed_offset:
                                result = True
                                break
                        if result:
                            break
                    if result:
                        break
            if result:
                break
        if result:
            break
    if cache_key is not None:
        if len(_WINDOW_RESULT_CACHE) > 64:
            _WINDOW_RESULT_CACHE.clear()
        _WINDOW_RESULT_CACHE[cache_key] = result
    return result
