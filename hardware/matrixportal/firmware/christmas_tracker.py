"""Small, allocation-free helpers for the Christmas Tracker animation."""


SLEIGH_SLIDE_SECONDS = 3.0
CHRISTMAS_INTRO_SECONDS = 8
SLEIGH_START_X = 256
SLEIGH_END_X = 0
CHRISTMAS_SCREEN_SECONDS = 18
SNOW_FLAKE_X = (7, 23, 39, 55, 71, 87, 103, 119,
                135, 151, 167, 183, 199, 215, 231, 247)
SNOW_FLAKE_SPEED = (5, 7, 9, 6, 8, 10, 5, 7,
                    9, 6, 8, 10, 5, 7, 9, 6)
SNOW_FLAKE_START_Y = (0, 7, 15, 23, 3, 11, 19, 27,
                      4, 12, 20, 28, 1, 9, 17, 25)


def _leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _ordinal(year, month, day):
    """Return a Gregorian day ordinal without importing datetime on-device."""
    prior = year - 1
    total = prior * 365 + prior // 4 - prior // 100 + prior // 400
    month_days = (31, 29 if _leap_year(year) else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31)
    for index in range(month - 1):
        total += month_days[index]
    return total + day


def days_until_christmas(date_text):
    """Return days to Dec 25 from a London-local YYYY-MM-DD date string."""
    if not isinstance(date_text, str) or len(date_text) != 10:
        return None
    if date_text[4] != "-" or date_text[7] != "-":
        return None
    try:
        year = int(date_text[0:4])
        month = int(date_text[5:7])
        day = int(date_text[8:10])
    except (TypeError, ValueError):
        return None
    if year < 1 or not 1 <= month <= 12:
        return None
    month_days = (31, 29 if _leap_year(year) else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31)
    if not 1 <= day <= month_days[month - 1]:
        return None
    target_year = year + 1 if (month, day) > (12, 25) else year
    return _ordinal(target_year, 12, 25) - _ordinal(year, month, day)


def sleigh_x(phase):
    """Return the sleigh's left edge for a screen-relative phase in seconds."""
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    if elapsed >= SLEIGH_SLIDE_SECONDS:
        return SLEIGH_END_X
    return max(SLEIGH_END_X, SLEIGH_START_X - int(
        (SLEIGH_START_X - SLEIGH_END_X) * elapsed / SLEIGH_SLIDE_SECONDS
    ))


def snow_active(phase):
    try:
        return float(phase or 0) >= 0
    except (TypeError, ValueError):
        return False


def with_christmas_tracker(screens):
    """Append the firmware-owned sleigh intro and countdown/snow screens."""
    result = list(screens or ())
    intro = None
    tracker = None
    for index, screen in enumerate(result):
        if not isinstance(screen, dict):
            continue
        if screen.get("kind") == "christmas_tracker_intro":
            intro = index
        elif screen.get("kind") == "christmas_tracker":
            tracker = index
    if intro is None:
        entry = {
            "id": "christmas-tracker-intro",
            "kind": "christmas_tracker_intro",
            "title": "CHRISTMAS",
            "words": "HO HO HO...",
            "duration_seconds": CHRISTMAS_INTRO_SECONDS,
            "source": "firmware",
        }
        if tracker is None:
            result.append(entry)
            intro = len(result) - 1
        else:
            result.insert(tracker, entry)
            intro = tracker
            tracker += 1
    if tracker is None:
        result.insert(intro + 1, {
        "id": "christmas-tracker",
        "kind": "christmas_tracker",
        "title": "CHRISTMAS TRACKER",
        "duration_seconds": CHRISTMAS_SCREEN_SECONDS,
        "source": "firmware",
        })
    return result
