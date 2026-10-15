"""Shared time filtering for train and bus departure rows."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


LONDON = ZoneInfo("Europe/London")


def _clock(value):
    try:
        return time.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def _service_datetime(value, now):
    clock = _clock(value)
    if clock is None:
        return None
    local_now = now.astimezone(LONDON)
    candidate = datetime.combine(local_now.date(), clock, LONDON)
    # National Rail provides a clock time without a date. A time more than
    # twelve hours behind the current clock belongs to the next service day.
    if candidate < local_now and local_now - candidate > timedelta(hours=12):
        candidate += timedelta(days=1)
    return candidate


def filter_train_services(services, now, limit=None):
    """Drop past train rows unless the feed gives a future revised time."""
    local_now = now.astimezone(LONDON)
    result = []
    for service in services or ():
        scheduled = _service_datetime(service.get("time"), now)
        status = str(service.get("status") or "").strip()
        expected = _service_datetime(status, now)
        if expected is not None:
            if expected >= local_now:
                result.append(service)
            continue
        # "Delayed" has no usable arrival/departure estimate. Retaining it
        # after the scheduled time can leave a departed train on the board
        # until the upstream feed changes. A future scheduled time remains
        # visible below; a future revised time was handled above.
        if scheduled is None or scheduled >= local_now:
            result.append(service)
    if limit is not None:
        result = result[:max(0, int(limit))]
    return result

