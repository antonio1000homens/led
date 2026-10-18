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
