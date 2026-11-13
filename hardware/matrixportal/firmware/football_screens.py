"""Validation and prompt snapshots for football MQTT providers."""

import json
import re

from mqtt_screens import _epoch


FOOTBALL_TEAMS = ("sporting_cp", "millwall", "portugal", "england")
FOOTBALL_STATUSES = ("PRE", "IN", "POST", "BYE", "NOT_FOUND", "UNKNOWN", "UNAVAILABLE")
FOOTBALL_TEAM_NAMES = {
    "sporting_cp": "Sporting CP", "millwall": "Millwall FC",
    "england": "England", "portugal": "Portugal",
}
FOOTBALL_TEAM_COLOUR_NAMES = {
    "sporting_cp": "Sporting CP", "millwall": "Millwall FC",
    "england": "England", "portugal": "Portugal",
}
# Full-intensity RGB primaries survive the MatrixPortal's one-bit-per-channel
# output. Only the tracked team's name receives this color; the rest is white.
FOOTBALL_TEAM_COLORS = {
    "sporting_cp": (0, 255, 0),
    "england": (255, 255, 255),
    "millwall": (0, 0, 255),
    "portugal": (255, 0, 0),
}
FOOTBALL_FIXTURE_TEXT_COLOR = (255, 255, 0)
FOOTBALL_TEAM_NAME_MAX_LENGTH = 16
LIVE_STALE_SECONDS = 600
GOALAPI_LIVE_STALE_SECONDS = 4 * 60 * 60
GOAL_FLASH_SECONDS = 8
SCREEN_DURATION_SECONDS = 20
FOOTBALL_DEFAULT_ANIMATION_SPEED = 80
FOOTBALL_PRE_CLEAR_SECONDS = 0.5
FOOTBALL_MIN_ANIMATION_SPEED = 20
FOOTBALL_MAX_ANIMATION_SPEED = 160
FOOTBALL_START_X = 256
FOOTBALL_END_X = 2
FOOTBALL_BALL_WIDTH = 16
FOOTBALL_TEXT_X = FOOTBALL_END_X + FOOTBALL_BALL_WIDTH + 4
FOOTBALL_LIVE_RIGHT_X = 184
FOOTBALL_LIVE_TEXT_MAX_CHARS = (FOOTBALL_LIVE_RIGHT_X - FOOTBALL_TEXT_X) // 6
FOOTBALL_VS_COLUMN = 10


def football_presentation_expired(screen, elapsed_seconds):
    """Hold a fresh in-progress match until it ends or its snapshot goes stale."""
    if isinstance(screen, dict) and screen.get("status") == "IN":
        return False
    duration = 20
    if isinstance(screen, dict):
        try:
            duration = float(screen.get("duration_seconds") or duration)
        except (TypeError, ValueError):
            pass
    return elapsed_seconds >= duration


def football_team_name_span(screen, line):
    """Return the tracked team-name span in a row, or None if absent."""
    team_key = screen.get("team_key")
    name = FOOTBALL_TEAM_COLOUR_NAMES.get(
        team_key, screen.get("team_name") or FOOTBALL_TEAM_NAMES.get(team_key, "")
    )
    if not isinstance(name, str) or not name.strip():
        return None
    row = str(line)
    row_upper = row.upper()
    name = name.strip().upper()
    candidates = (name, name.split(" ", 1)[0]) if " " in name else (name,)
    for candidate in candidates:
        start = row_upper.find(candidate)
        if start >= 0:
            return start, candidate, FOOTBALL_TEAM_COLORS.get(team_key)
    return None


def kickoff_countdown(kickoff, now_epoch):
    if not kickoff:
        return "FIXTURE TIME TBC"
    if now_epoch is None:
        return "CLOCK SYNCING"
    try:
        remaining = (_epoch(kickoff) // 1000) - int(now_epoch)
    except (TypeError, ValueError):
        return "FIXTURE TIME TBC"
    if remaining < 0:
        return "AWAITING LIVE UPDATE"
    if remaining < 60:
        return "KICKOFF IN {}S".format(remaining)
    minutes = (remaining + 59) // 60
    if minutes < 60:
        return "KICKOFF IN {}M".format(minutes)
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return "KICKOFF IN {}H {:02d}M".format(hours, minutes)
    days, hours = divmod(hours, 24)
    return "KICKOFF IN {}D {}H".format(days, hours)


def _days_since_epoch(year, month, day):
    prior = year - 1
    ordinal = prior * 365 + prior // 4 - prior // 100 + prior // 400
    month_days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    ordinal += sum(month_days[:month - 1]) + day - 1
    epoch_prior = 1969
    epoch_ordinal = epoch_prior * 365 + epoch_prior // 4 - epoch_prior // 100 + epoch_prior // 400
    return ordinal - epoch_ordinal


def _civil_from_days(days):
    """Convert days since 1970-01-01 to Gregorian year/month/day."""
    shifted = days + 719468
    era = (shifted if shifted >= 0 else shifted - 146096) // 146097
    day_of_era = shifted - era * 146097
    year_of_era = (day_of_era - day_of_era // 1460 + day_of_era // 36524
                   - day_of_era // 146096) // 365
    year = year_of_era + era * 400
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    month_part = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * month_part + 2) // 5 + 1
    month = month_part + (3 if month_part < 10 else -9)
    year += 1 if month <= 2 else 0
    return year, month, day


def _last_sunday(year, month):
    month_days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                  31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    last_day = month_days[month - 1]
    weekday = (_days_since_epoch(year, month, last_day) + 3) % 7
    return last_day - ((weekday + 1) % 7)


def kickoff_local_label(kickoff):
    """Format a timezone-aware kickoff in Europe/London without zoneinfo."""
    try:
        epoch_seconds = _epoch(kickoff) // 1000
        utc_days = epoch_seconds // 86400
        utc_year, _, _ = _civil_from_days(utc_days)
        dst_start = _days_since_epoch(utc_year, 3, _last_sunday(utc_year, 3)) * 86400 + 3600
        dst_end = _days_since_epoch(utc_year, 10, _last_sunday(utc_year, 10)) * 86400 + 3600
        is_bst = dst_start <= epoch_seconds < dst_end
        local_seconds = epoch_seconds + (3600 if is_bst else 0)
        local_days, seconds_today = divmod(local_seconds, 86400)
        year, month, day = _civil_from_days(local_days)
        hour, seconds_today = divmod(seconds_today, 3600)
        minute = seconds_today // 60
        weekday = (local_days + 3) % 7
        weekdays = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
        months = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                  "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
        return "{} {:02d} {} {:02d}:{:02d}".format(
            weekdays[weekday], day, months[month - 1], hour, minute
        )
    except (TypeError, ValueError, IndexError, OverflowError):
        return "TIME TBC"


def football_slide_seconds(animation_speed=None):
    """Return slide duration from the configured pixel-per-second speed."""
    try:
        speed = int(animation_speed)
    except (TypeError, ValueError, OverflowError):
        speed = FOOTBALL_DEFAULT_ANIMATION_SPEED
    if not FOOTBALL_MIN_ANIMATION_SPEED <= speed <= FOOTBALL_MAX_ANIMATION_SPEED:
        speed = FOOTBALL_DEFAULT_ANIMATION_SPEED
    return FOOTBALL_START_X / float(speed)


def football_presentation_position(phase, animate=True, animation_speed=None):
    """Return the ball x coordinate and whether match text can be shown."""
    if not animate:
        return FOOTBALL_END_X, True
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    travel = FOOTBALL_START_X - FOOTBALL_END_X
    duration = football_slide_seconds(animation_speed)
    x = max(FOOTBALL_END_X, FOOTBALL_START_X - int(travel * elapsed / duration))
    return x, x == FOOTBALL_END_X


def football_entry_phase(phase, status):
    """Leave a short clear gap before a PRE card starts sliding in."""
    if status != "PRE":
        return phase
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    return max(0.0, elapsed - FOOTBALL_PRE_CLEAR_SECONDS)



def football_due_in(kickoff, now_epoch):
    """Compact absolute-time PRE countdown for the right side of the board.

    Show whole days at or above 24 hours; below that, show the clock
    countdown without days. Seconds appear only above 60 seconds.
    """
    if not kickoff or now_epoch is None:
        return "TBC"
    try:
        remaining = max(0, (_epoch(kickoff) // 1000) - int(now_epoch))
    except (ValueError, TypeError):
        return "TBC"
    if remaining == 0:
        return "DUE NOW"
    if remaining <= 60:
        return "UNDER 1 MIN"
    if remaining >= 86400:
        days = remaining // 86400
        return "{} {}".format(days, "DAY" if days == 1 else "DAYS")
    if remaining > 3600:
        hours, rest = divmod(remaining, 3600)
        minutes, seconds = divmod(rest, 60)
        return "{:02d}H {:02d}M {:02d}S".format(hours, minutes, seconds)
    minutes, seconds = divmod(remaining, 60)
    return "{:02d}M {:02d}S".format(minutes, seconds)


def football_countdown_x(value, width=256, cell_width=6):
    """Right-align countdown glyphs without a fixed x minimum.

    Character cell width matches the display's 5x7 label font with its
    one-pixel spacing. A large day count may reach further left, but must
    never be clipped at the right edge.
    """
    return max(0, int(width) - len(str(value)) * int(cell_width))


def football_slide_offset(phase, animation_speed=None):
    """Translate whole 256x32 match scene from the right to x=0."""
    x, settled = football_presentation_position(
        phase, animate=True, animation_speed=animation_speed,
    )
    return x - FOOTBALL_END_X, settled


def football_roll_frame(phase, animation_speed=None):
    """Return the rolling ball orientation throughout a PRE presentation.

    Keep the original two-turn slide cadence, then continue rolling at the
    same rate while the settled kickoff countdown is visible.
    """
    try:
        elapsed = max(0.0, float(phase or 0))
    except (ValueError, TypeError):
        elapsed = 0.0
    return int(elapsed * 16 / football_slide_seconds(animation_speed)) % 8


def _normalize_fixture_separator(fixture):
    """Align VS at one character column and preserve a clear right-side gap."""
    fixture = fixture.upper()
    separator = re.search(r"\s*VS\s*", fixture)
    if separator is None:
        return fixture
    left = fixture[:separator.start()].strip()
    right = fixture[separator.end():].strip()
    padding = max(1, FOOTBALL_VS_COLUMN - len(left))
    return "{}{}VS {}".format(left, " " * padding, right)


def football_screen_lines(screen, now_epoch):
    """Return status-specific text rows for the 256x32 display."""
    team = str(screen.get("team_name") or screen.get("team_key") or "FOOTBALL").upper()
    opponent = str(screen.get("opponent_long_name") or screen.get("opponent") or "").upper()
    fixture = screen.get("display_fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        fixture = "{} VS {}".format(team, opponent) if opponent else team
    fixture = _normalize_fixture_separator(fixture)
    status = screen.get("status")
    competition = str(screen.get("competition") or "")
    if status == "PRE":
        team_side = str(screen.get("team_homeaway") or screen.get("homeaway") or "home").lower()
        if not isinstance(screen.get("display_fixture"), str) or not screen.get("display_fixture", "").strip():
            if opponent:
                fixture = ("{} VS {}".format(opponent, team) if team_side in ("away", "a")
                           else "{} VS {}".format(team, opponent))
            else:
                fixture = team
        return _normalize_fixture_separator(fixture), kickoff_local_label(screen.get("kickoff"))
    elif status in ("IN", "POST"):
        home = str(screen.get("home_team") or "HOME").upper()
        away = str(screen.get("away_team") or "AWAY").upper()
        home_score, away_score = screen.get("home_score"), screen.get("away_score")
        if home_score is None or away_score is None:
            detail = "SCORE UNAVAILABLE"
        else:
            detail = "{} {} - {} {}".format(home, home_score, away_score, away)
    elif status == "BYE":
        detail = "NO FIXTURE"
    elif status == "NOT_FOUND":
        detail = "NO FIXTURE FOUND"
    elif status == "UNKNOWN":
        detail = "STATUS UNKNOWN"
    else:
        detail = "SCORE UNAVAILABLE"
    if status == "IN":
        live_clock = screen.get("clock")
        footer = "LIVE {}".format(live_clock) if live_clock else "LIVE"
    elif status == "POST":
        footer = "FULL TIME"
    elif status == "UNAVAILABLE" and screen.get("stale"):
        footer = "LIVE DATA STALE"
    else:
        footer = competition
    return team, fixture, detail, footer


def _short_text(value, maximum=100):
    return isinstance(value, str) and 0 < len(value.strip()) <= maximum


def _valid_team_key(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 48:
        return False
    for char in value:
        if not ("a" <= char <= "z" or "0" <= char <= "9" or char in "_-"):
            return False
    return True


def _score(value):
    return (value is None or
            (type(value) is int and 0 <= value <= 99))


def _has_fixture_data(screen):
    fixture = screen.get("display_fixture")
    if isinstance(fixture, str) and fixture.strip():
        return True
    return bool(
        isinstance(screen.get("team_name"), str) and screen["team_name"].strip()
        and isinstance(screen.get("opponent_long_name") or screen.get("opponent"), str)
        and (screen.get("opponent_long_name") or screen.get("opponent")).strip()
    )


def _live_stale(snapshot, now_ms):
    if now_ms is None:
        return True
    providers = snapshot.get("_provider_source_epochs")
    if isinstance(providers, dict) and providers:
        for provider, source_updated in providers.items():
            stale_after = (GOALAPI_LIVE_STALE_SECONDS
                           if provider == "goalapi" else LIVE_STALE_SECONDS)
            if (source_updated is not None
                    and now_ms - source_updated <= stale_after * 1000):
                return False
        return True
    source_updated = snapshot.get("_source_epoch")
    if source_updated is None:
        return True
    stale_after = LIVE_STALE_SECONDS
    if snapshot.get("source") == "nrwindsor" and snapshot.get("provider") == "goalapi":
        stale_after = GOALAPI_LIVE_STALE_SECONDS
    return now_ms - source_updated > stale_after * 1000


def _session_details(snapshot):
    kickoff = snapshot.get("_kickoff_epoch")
    if kickoff is None and snapshot.get("kickoff") is not None:
        try:
            kickoff = _epoch(snapshot.get("kickoff"))
        except (TypeError, ValueError):
            kickoff = None
    fixture_date = snapshot.get("fixture_date")
    fixture_key = snapshot.get("fixture_key")
    if (not isinstance(fixture_date, str) and isinstance(fixture_key, str)):
        parts = fixture_key.split("|")
        if len(parts) >= 2:
            fixture_date = parts[1]
    if not isinstance(fixture_date, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", fixture_date):
        fixture_date = None
    if fixture_date is None and kickoff is not None:
        fixture_date = _epoch_date(kickoff)
    opponent = snapshot.get("opponent_long_name") or snapshot.get("opponent")
    if isinstance(opponent, str):
        opponent = re.sub(r"\b(football club|fc|afc)\b", " ", opponent.lower())
        opponent = re.sub(r"[^a-z0-9]+", " ", opponent).strip()
    else:
        opponent = None
    ids = tuple(snapshot.get(name) for name in
                ("fixture_key", "match_id", "provider_match_id") if snapshot.get(name))
    return fixture_date, kickoff, opponent, ids


def _epoch_date(epoch):
    # Keep this compatible with CircuitPython's small datetime implementation.
    try:
        from time import gmtime
        value = gmtime(int(epoch / 1000))
        return "%04d-%02d-%02d" % (value.tm_year, value.tm_mon, value.tm_mday)
    except (ImportError, AttributeError, OverflowError, ValueError):
        return None


def _same_match_session(previous, incoming):
    """Compare match lifecycle evidence; provider IDs are hints, not join keys."""
    if previous is None or incoming is None:
        return False
    old_date, old_kickoff, old_opponent, old_ids = _session_details(previous)
    new_date, new_kickoff, new_opponent, new_ids = _session_details(incoming)
    close_kickoff = (old_kickoff is not None and new_kickoff is not None
                     and abs(old_kickoff - new_kickoff) <= 15 * 60 * 1000)
    if old_date and new_date and old_date != new_date and not close_kickoff:
        return False
    if old_kickoff is not None and new_kickoff is not None:
        # Provider kickoff values for one match should be close. A different
        # kickoff is a session rollover even when it is a same-day doubleheader.
        if abs(old_kickoff - new_kickoff) > 15 * 60 * 1000:
            return False
    if old_opponent and new_opponent and old_opponent != new_opponent:
        return False
    if old_ids and new_ids and set(old_ids).intersection(new_ids):
        return True
    if (old_kickoff is not None and new_kickoff is not None
            and abs(old_kickoff - new_kickoff) <= 15 * 60 * 1000):
        return True
    if old_date and new_date and old_date == new_date and old_opponent and new_opponent:
        return True
    # If one provider omits the stable fixture metadata, only overlap the
    # current team session when its source event time is near the active event.
    old_source, new_source = previous.get("_source_epoch"), incoming.get("_source_epoch")
    return (old_source is not None and new_source is not None
            and abs(old_source - new_source) <= 4 * 60 * 60 * 1000)


def _strong_same_match_session(previous, incoming):
    old_date, old_kickoff, old_opponent, old_ids = _session_details(previous)
    new_date, new_kickoff, new_opponent, new_ids = _session_details(incoming)
    close_kickoff = (old_kickoff is not None and new_kickoff is not None
                     and abs(old_kickoff - new_kickoff) <= 15 * 60 * 1000)
    if old_date and new_date and old_date != new_date and not close_kickoff:
        return False
    if (old_kickoff is not None and new_kickoff is not None and not close_kickoff):
        return False
    if old_opponent and new_opponent and old_opponent != new_opponent:
        return False
    if old_ids and new_ids and set(old_ids).intersection(new_ids):
        return True
    if close_kickoff:
        return True
    return bool(old_date and old_date == new_date and old_opponent and new_opponent
                and old_opponent == new_opponent)


def _is_later_match(previous, incoming):
    old_date, old_kickoff, old_opponent, _ = _session_details(previous)
    new_date, new_kickoff, new_opponent, _ = _session_details(incoming)
    if old_date and new_date and new_date > old_date:
        return True
    if (old_kickoff is not None and new_kickoff is not None
            and new_kickoff - old_kickoff > 15 * 60 * 1000):
        return True
    old_source, new_source = previous.get("_source_epoch"), incoming.get("_source_epoch")
    return bool(old_opponent and new_opponent and old_opponent != new_opponent
                and old_source is not None and new_source is not None
                and new_source > old_source)


def _normalize(topic, payload, prefix="led/football/"):
    if isinstance(payload, (bytes, bytearray)):
        try:
            payload = payload.decode("utf-8")
        except UnicodeError:
            return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except (ValueError, UnicodeError):
            return None
    if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int:
        return None
    if payload.get("schema_version") != 1:
        return None
    source = payload.get("source")
    provider = payload.get("provider")
    homeassistant_teamtracker = source == "homeassistant" and provider == "teamtracker"
    nrwindsor_goalapi = source == "nrwindsor" and provider == "goalapi"
    if not (homeassistant_teamtracker or nrwindsor_goalapi):
        return None
    if not isinstance(topic, str) or not topic.startswith(prefix):
        return None
    team_key = topic[len(prefix):]
    if not _valid_team_key(team_key) or payload.get("team_key") != team_key:
        return None
    if homeassistant_teamtracker and team_key not in FOOTBALL_TEAMS:
        return None
    status = payload.get("status")
    if status not in FOOTBALL_STATUSES:
        return None
    try:
        published = _epoch(payload.get("published_at"))
        source_updated = payload.get("source_updated_at")
        if source_updated is not None:
            _epoch(source_updated)
        kickoff = payload.get("kickoff")
        if kickoff is not None:
            _epoch(kickoff)
        post_expires_at = payload.get("post_expires_at")
        if post_expires_at is not None:
            _epoch(post_expires_at)
    except (TypeError, ValueError):
        return None
    match_id = payload.get("match_id")
    if match_id is not None and not _short_text(match_id, 128):
        return None
    fixture_key = payload.get("fixture_key")
    if fixture_key is not None and not _short_text(fixture_key, 128):
        return None
    for name in ("provider_match_id", "event_id", "event_type"):
        value = payload.get(name)
        if value is not None and not _short_text(value, 128):
            return None
    for name in ("team_name", "opponent", "opponent_long_name", "display_fixture",
                 "home_team", "away_team", "homeaway", "team_homeaway",
                 "competition", "clock"):
        value = payload.get(name)
        if value is not None and (not isinstance(value, str) or len(value) > 120):
            return None
    for name in ("home_score", "away_score", "team_score", "opponent_score"):
        if not _score(payload.get(name)):
            return None
    result = dict(payload)
    result["team_key"] = team_key
    result["_published_epoch"] = published
    result["_source_epoch"] = _epoch(source_updated) if source_updated is not None else None
    result["_kickoff_epoch"] = _epoch(kickoff) if kickoff is not None else None
    result["fixture_key"] = fixture_key or match_id
    return result


def football_post_expired(screen, now_epoch):
    """Fail closed when a POST event lacks a verifiable local expiry."""
    if screen.get("status") != "POST":
        return False
    expiry = screen.get("post_expires_at")
    if expiry is None or now_epoch is None:
        return True
    try:
        return int(now_epoch * 1000) >= _epoch(expiry)
    except (TypeError, ValueError):
        return True


def _valid_final(snapshot):
    try:
        expiry = _epoch(snapshot.get("post_expires_at"))
    except (TypeError, ValueError):
        return False
    return (snapshot.get("status") == "POST"
            and type(snapshot.get("home_score")) is int
            and type(snapshot.get("away_score")) is int
            and snapshot.get("_source_epoch") is not None
            and snapshot.get("_published_epoch") is not None
            and expiry > snapshot.get("_published_epoch"))


class FootballScreenState:
    """Keep each topic's latest valid snapshot without affecting MQTT cycle screens."""

    def __init__(self, topic_filter="led/football/+", enabled=True):
        if (not isinstance(topic_filter, str) or not topic_filter.endswith("/+")
                or "+" in topic_filter[:-1] or "#" in topic_filter):
            raise ValueError("MQTT_FOOTBALL_TOPIC must be a single-level wildcard")
        self.prefix = topic_filter[:-1]
        self.enabled = bool(enabled)
        self._teams = {}
        self._dynamic_flags = {}
        self._goal_events = {}
        self._finished_sessions = {}
        self.last_decision = "none"

    def _prune_goalapi(self, now_ms):
        if now_ms is None:
            return
        for team_key, events in tuple(self._goal_events.items()):
            recent = [event for event in events
                      if event[1] is None
                      or now_ms - event[1] <= GOALAPI_LIVE_STALE_SECONDS * 1000]
            if recent:
                self._goal_events[team_key] = recent
            else:
                del self._goal_events[team_key]
        for team_key, snapshot in tuple(self._teams.items()):
            if snapshot.get("source") != "nrwindsor" or snapshot.get("provider") != "goalapi":
                continue
            if _live_stale(snapshot, now_ms):
                del self._teams[team_key]
                self._dynamic_flags.pop(team_key, None)

    def accept(self, topic, payload):
        self.last_decision = "rejected"
        if not self.enabled or not isinstance(topic, str) or not topic.startswith(self.prefix):
            self.last_decision = "invalid_topic_or_disabled"
            return False
        incoming = _normalize(topic, payload, self.prefix)
        if incoming is None:
            self.last_decision = "invalid_snapshot"
            return False
        self._prune_goalapi(incoming["_published_epoch"])
        team_key = incoming["team_key"]
        previous = self._teams.get(team_key)
        is_goal_api = (incoming.get("source") == "nrwindsor"
                       and incoming.get("provider") == "goalapi")
        event_id = incoming.get("event_id")
        event_type = str(incoming.get("event_type") or "").lower()
        source_epoch = incoming.get("_source_epoch")
        finished = self._finished_sessions.get(team_key)
        if incoming.get("status") == "IN" and finished is not None:
            if (_same_match_session(finished, incoming)
                    or not _is_later_match(finished, incoming)):
                self.last_decision = "late_live_after_post_rejected"
                return False
        if is_goal_api:
            recent_events = self._goal_events.get(team_key, ())
            if event_id and any(event_id == prior_id for prior_id, _ in recent_events):
                self.last_decision = "duplicate_goalapi_event"
                return False
            latest_epoch = max((epoch for _, epoch in recent_events if epoch is not None),
                               default=None)
            if (source_epoch is not None and latest_epoch is not None
                    and source_epoch <= latest_epoch):
                self.last_decision = "out_of_order_goalapi_event"
                return False
        same_session = previous is not None and _same_match_session(previous, incoming)
        incoming_score = (incoming.get("home_score"), incoming.get("away_score"))
        valid_incoming_score = all(type(value) is int for value in incoming_score)
        if (same_session and is_goal_api and incoming.get("status") == "IN"
                and event_type in ("goal.scored", "score.changed")
                and valid_incoming_score and source_epoch is not None
                and incoming_score != (previous.get("home_score"),
                                       previous.get("away_score"))
                and previous.get("_accepted_score_epoch") is not None
                and source_epoch <= previous.get("_accepted_score_epoch")
                and ((event_type == "goal.scored"
                         and sum(incoming_score) < sum((previous.get("home_score"),
                                                        previous.get("away_score"))))
                     or (event_type == "score.changed"
                         and previous.get("_teamtracker_score") is not None
                         and sum(previous.get("_teamtracker_score"))
                             > sum(previous.get("_goal_authoritative_score") or
                                   (previous.get("home_score"), previous.get("away_score")))
                         and previous.get("_teamtracker_source_epoch") is not None
                         and source_epoch <= previous.get("_teamtracker_source_epoch")))):
            self.last_decision = "out_of_order_goalapi_score"
            return False
        if previous is not None and previous.get("status") == "IN":
            old_kickoff = previous.get("_kickoff_epoch")
            old_session_start = previous.get("_session_started_epoch")
            incoming_kickoff = incoming.get("_kickoff_epoch")
            # A delayed event carrying the previous fixture's kickoff or source
            # timestamp must not roll a newer live team session backwards.
            if (incoming.get("status") == "IN" and old_kickoff is not None
                    and incoming_kickoff is not None and incoming_kickoff < old_kickoff):
                self.last_decision = "stale_fixture_session"
                return False
            if (incoming.get("status") == "IN" and old_session_start is not None
                    and source_epoch is not None and source_epoch < old_session_start
                    and not same_session and incoming_kickoff == old_kickoff):
                self.last_decision = "stale_fixture_event"
                return False
            if incoming.get("status") == "POST":
                if (not same_session
                        or (source_epoch is not None
                            and previous.get("_source_epoch") is not None
                            and source_epoch <= previous.get("_source_epoch"))):
                    self.last_decision = "post_wrong_or_stale_session"
                    return False
            elif (incoming.get("status") != "IN"
                  and not _live_stale(previous, incoming["_published_epoch"])):
                self.last_decision = "live_status_regression_rejected"
                return False
            session_source = previous.get("_session_started_source_epoch")
            kickoff_epoch = previous.get("_kickoff_epoch")
            if (incoming.get("status") == "IN" and source_epoch is not None
                    and session_source is not None and source_epoch < session_source
                    and not _strong_same_match_session(previous, incoming)
                    and (kickoff_epoch is None or source_epoch < kickoff_epoch)):
                self.last_decision = "ambiguous_old_event_rejected"
                return False
        if incoming.get("status") == "POST":
            if not _valid_final(incoming):
                self.last_decision = "invalid_final_result"
                return False
            # A final result is a one-shot presentation, never a retained live
            # snapshot. It is accepted only for the current team session.
            self._finished_sessions[team_key] = {
                name: incoming.get(name) for name in (
                    "team_key", "fixture_key", "match_id", "provider_match_id",
                    "kickoff", "_kickoff_epoch", "fixture_date", "opponent",
                    "opponent_long_name", "_source_epoch", "_published_epoch",
                    "source_updated_at",
                )
            }
            self._teams.pop(team_key, None)
            self._dynamic_flags.pop(team_key, None)
            self.last_decision = "post_accepted"
            return True
        if previous is not None and previous.get("status") == "IN" and not same_session:
            # A genuinely later live fixture starts a fresh, bounded session.
            previous_stale = _live_stale(previous, incoming["_published_epoch"])
            if incoming.get("status") != "IN" and not previous_stale:
                self.last_decision = "session_transition_rejected"
                return False
            if (incoming.get("status") == "IN" and source_epoch is not None
                    and previous.get("_session_started_epoch") is not None
                    and source_epoch < previous["_session_started_epoch"]
                    and (old_kickoff is None or incoming_kickoff is None
                         or incoming_kickoff <= old_kickoff)):
                self.last_decision = "stale_fixture_event"
                return False
            previous = None
            self._goal_events.pop(team_key, None)

        if same_session:
            provider = "goalapi" if is_goal_api else "teamtracker"
            provider_epochs = dict(previous.get("_provider_source_epochs") or {})
            prior_provider_epoch = provider_epochs.get(provider)
            if (source_epoch is not None and prior_provider_epoch is not None
                    and source_epoch <= prior_provider_epoch):
                self.last_decision = "out_of_order_provider_update"
                return False
            item = dict(previous)
            item.pop("_last_score_decision", None)
            clear_fixture_data = (incoming.get("status") == "PRE"
                                  and not _has_fixture_data(incoming))
            if clear_fixture_data:
                for name in ("team_name", "opponent", "opponent_long_name",
                             "display_fixture", "kickoff"):
                    item[name] = None
            item.update({key: value for key, value in incoming.items()
                         if not key.startswith("_") and value is not None})
            # Preserve richer fixture metadata from the other feed when a
            # snapshot omits those values or supplies only a short alias.
            for name in ("clock", "competition", "team_name", "opponent",
                         "opponent_long_name", "display_fixture", "home_team",
                         "away_team", "homeaway", "team_homeaway", "kickoff",
                         "fixture_date"):
                if (not clear_fixture_data and incoming.get(name) is None
                        and previous.get(name) is not None):
                    item[name] = previous[name]
            provider_epochs[provider] = source_epoch
            item["_provider_source_epochs"] = provider_epochs
            if (source_epoch is not None
                    and (previous.get("_source_epoch") is None
                         or source_epoch >= previous.get("_source_epoch"))):
                item["_source_epoch"] = source_epoch
                item["source_updated_at"] = incoming.get("source_updated_at")
            else:
                item["_source_epoch"] = previous.get("_source_epoch")
                item["source_updated_at"] = previous.get("source_updated_at")
            item["_published_epoch"] = max(
                previous.get("_published_epoch", 0), incoming["_published_epoch"])
            item["published_at"] = incoming.get("published_at")
            incoming_score = (incoming.get("home_score"), incoming.get("away_score"))
            previous_score = (previous.get("home_score"), previous.get("away_score"))
            valid_score = all(type(value) is int for value in incoming_score)
            goal_score = previous.get("_goal_score")
            authoritative_score = previous.get("_goal_authoritative_score")
            if is_goal_api and valid_score and event_type in ("goal.scored", "score.changed"):
                item["home_score"], item["away_score"] = incoming_score
                item["_goal_authoritative_score"] = incoming_score
                item["_goal_score"] = incoming_score
                item["_score_source"] = "goalapi"
                if (item.get("_accepted_score_epoch") is None
                        or source_epoch is None
                        or source_epoch >= item.get("_accepted_score_epoch")):
                    item["_accepted_score_epoch"] = source_epoch
                    item["_accepted_score_source"] = "goalapi"
                if event_type == "goal.scored":
                    old_score = (incoming.get("previous_home_score"),
                                 incoming.get("previous_away_score"))
                    if not all(type(value) is int for value in old_score):
                        old_score = previous_score
                    if (old_score[0] is not None and incoming_score[0] == old_score[0] + 1
                            and incoming_score[1] == old_score[1]):
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "home"
                    elif (old_score[1] is not None and incoming_score[1] == old_score[1] + 1
                          and incoming_score[0] == old_score[0]):
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "away"
                else:
                    item["_goal_until"] = None
                    item["_goal_side"] = None
            elif not is_goal_api and valid_score:
                if incoming_score != previous_score:
                    item["_goal_until"] = None
                    item["_goal_side"] = None
                if (incoming_score == previous_score
                        and (incoming_score == authoritative_score
                             or incoming_score == goal_score)):
                    item["_goal_score_confirmed"] = True
                    item["_score_source"] = "teamtracker"
                    item.pop("_goal_score", None)
                    if (source_epoch is not None
                            and (item.get("_accepted_score_epoch") is None
                                 or source_epoch > item["_accepted_score_epoch"])):
                        item["_accepted_score_epoch"] = source_epoch
                        item["_accepted_score_source"] = "teamtracker"
                elif authoritative_score is not None:
                    old_tracker = previous.get("_teamtracker_score")
                    old_tracker_epoch = previous.get("_teamtracker_source_epoch")
                    advanced = (old_tracker is not None and source_epoch is not None
                                and old_tracker_epoch is not None
                                and source_epoch > old_tracker_epoch
                                and (incoming_score[0] > old_tracker[0]
                                     or incoming_score[1] > old_tracker[1]))
                    if advanced:
                        item["home_score"], item["away_score"] = incoming_score
                        item["_score_source"] = "teamtracker"
                        if (item.get("_accepted_score_epoch") is None
                                or source_epoch > item["_accepted_score_epoch"]):
                            item["_accepted_score_epoch"] = source_epoch
                            item["_accepted_score_source"] = "teamtracker"
                    else:
                        item["home_score"], item["away_score"] = previous_score
                        item["_score_source"] = previous.get("_score_source") or "goalapi_protected"
                        item["_last_score_decision"] = "teamtracker_rollback_ignored"
                else:
                    item["home_score"], item["away_score"] = incoming_score
                    item["_score_source"] = "teamtracker"
                    if (source_epoch is not None
                            and (item.get("_accepted_score_epoch") is None
                                 or source_epoch > item["_accepted_score_epoch"])):
                        item["_accepted_score_epoch"] = source_epoch
                        item["_accepted_score_source"] = "teamtracker"
                item["_teamtracker_score"] = incoming_score
                item["_teamtracker_source_epoch"] = source_epoch
                if (incoming_score != previous_score
                        and all(type(value) is int for value in previous_score)
                        and item.get("_score_source") == "teamtracker"
                        and source_epoch is not None):
                    home_delta = incoming_score[0] - (previous_score[0] or 0)
                    away_delta = incoming_score[1] - (previous_score[1] or 0)
                    if home_delta == 1 and away_delta == 0:
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "home"
                    elif away_delta == 1 and home_delta == 0:
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "away"
            else:
                # No score in this update: preserve both feeds' accepted score.
                item["home_score"], item["away_score"] = previous_score
            item["_session_started_epoch"] = previous.get("_session_started_epoch")
            item["_session_started_source_epoch"] = (
                previous.get("_session_started_source_epoch") or
                (source_epoch if incoming.get("status") == "IN" else None))
        else:
            item = dict(incoming)
            provider = "goalapi" if is_goal_api else "teamtracker"
            item["_provider_source_epochs"] = {provider: source_epoch}
            item["_session_started_epoch"] = (
                incoming.get("_kickoff_epoch") or source_epoch)
            item["_session_started_source_epoch"] = (
                source_epoch if incoming.get("status") == "IN" else None)
            item["_score_source"] = provider
            if all(type(value) is int for value in (
                    incoming.get("home_score"), incoming.get("away_score"))):
                item["_accepted_score_epoch"] = source_epoch
                item["_accepted_score_source"] = provider
            if is_goal_api and incoming.get("status") == "IN":
                initial_score = (incoming.get("home_score"), incoming.get("away_score"))
                if (event_type in ("goal.scored", "score.changed")
                        and all(type(value) is int for value in initial_score)):
                    item["_goal_authoritative_score"] = initial_score
                    item["_goal_score"] = initial_score
                    item["_accepted_score_epoch"] = source_epoch
                    item["_accepted_score_source"] = "goalapi"
                    if event_type == "goal.scored":
                        old_score = (incoming.get("previous_home_score"),
                                     incoming.get("previous_away_score"))
                        if (all(type(value) is int for value in old_score)
                                and initial_score[0] == old_score[0] + 1
                                and initial_score[1] == old_score[1]):
                            item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                            item["_goal_side"] = "home"
                        elif (all(type(value) is int for value in old_score)
                              and initial_score[1] == old_score[1] + 1
                              and initial_score[0] == old_score[0]):
                            item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                            item["_goal_side"] = "away"
            elif not is_goal_api:
                item["_teamtracker_score"] = (incoming.get("home_score"),
                                               incoming.get("away_score"))
                item["_teamtracker_source_epoch"] = source_epoch
        if is_goal_api:
            recent_events = self._goal_events.setdefault(team_key, [])
            recent_events.append((event_id, source_epoch))
            if len(recent_events) > 64:
                del recent_events[:-64]
        self._teams[team_key] = item
        if not same_session:
            self.last_decision = "new_match_session"
        elif is_goal_api and event_type == "score.changed":
            self.last_decision = "goalapi_score_correction"
        elif is_goal_api and event_type == "goal.scored":
            self.last_decision = "goalapi_goal_applied"
        elif not is_goal_api and valid_incoming_score:
            if item.get("_last_score_decision"):
                self.last_decision = item["_last_score_decision"]
            elif item.get("_score_source") == "goalapi_protected":
                self.last_decision = "teamtracker_rollback_ignored"
            elif item.get("_goal_score_confirmed"):
                self.last_decision = "teamtracker_score_confirmed"
            else:
                self.last_decision = "teamtracker_score_applied"
        else:
            self.last_decision = "match_snapshot_merged"
        return True

    def accept_for_presentation(self, topic, payload, now_epoch=None):
        """Accept a snapshot and return its display event or state refresh."""
        item = _normalize(topic, payload, self.prefix)
        team_key = item["team_key"] if item is not None else None
        previous = self._teams.get(team_key) if team_key is not None else None
        if item is None or not self.accept(topic, payload):
            return False, None
        if item.get("status") == "POST":
            # POST is intentionally not retained in _teams. The accepted MQTT
            # payload itself is the one-shot presentation.
            return True, self._screen_from_snapshot(item, now_epoch)
        screen = self.screen_for_team(item["team_key"], now_epoch)
        if screen is None:
            return True, None
        current = self._teams.get(item["team_key"], item)
        same_session = (previous is not None
                        and previous.get("status") == current.get("status")
                        and _same_match_session(previous, current))
        score_changed = same_session and (
            (previous.get("home_score"), previous.get("away_score"))
            != (current.get("home_score"), current.get("away_score"))
        )
        screen["presentation_update"] = (
            "new_fixture_or_status" if not same_session
            else ("score_changed" if score_changed else "data_refresh")
        )
        return True, screen

    @staticmethod
    def _screen_from_snapshot(snapshot, now_epoch):
        status = snapshot["status"]
        if status not in ("PRE", "IN", "POST"):
            return None
        if status == "POST" and not _valid_final(snapshot):
            return None
        if status == "PRE" and not _has_fixture_data(snapshot):
            return None
        if football_post_expired(snapshot, now_epoch):
            return None
        now_ms = int(now_epoch * 1000) if now_epoch is not None else None
        screen = {key: value for key, value in snapshot.items() if not key.startswith("_")}
        screen["score_source"] = snapshot.get("_score_source")
        stale_live = status == "IN" and _live_stale(snapshot, now_ms)
        if stale_live:
            screen["status"] = "UNAVAILABLE"
            screen["home_score"] = None
            screen["away_score"] = None
            screen["clock"] = None
            screen["stale"] = True
            return None
        screen["stale"] = False
        goal_until = snapshot.get("_goal_until")
        if goal_until is not None and now_ms is not None and now_ms < goal_until:
            screen["goal_side"] = snapshot.get("_goal_side")
            screen["goal_flash_active"] = True
        screen.update({
            "id": "football-" + snapshot["team_key"],
            "kind": "football_score",
            "title": screen.get("team_name") or FOOTBALL_TEAM_NAMES.get(snapshot["team_key"], "FOOTBALL"),
            "duration_seconds": SCREEN_DURATION_SECONDS,
            "source": "{}_{}".format(screen.get("source"), screen.get("provider")),
        })
        return screen

    def has_live_match(self, now_epoch):
        """Use fresh IN snapshots from any team to choose the fast MQTT cadence.

        PRE is not live; POST stays in the normal rotation until its local
        expiry. Stale snapshots must not leave the device polling quickly.
        """
        if not self.enabled or now_epoch is None:
            return False
        now_ms = int(now_epoch * 1000)
        self._prune_goalapi(now_ms)
        return any(
            item.get("status") == "IN" and not _live_stale(item, now_ms)
            for item in self._teams.values()
        )

    def screens(self, now_epoch):
        if not self.enabled:
            return []
        result = []
        now_ms = int(now_epoch * 1000) if now_epoch is not None else None
        self._prune_goalapi(now_ms)
        for team_key, snapshot in self._teams.items():
            screen = self._screen_from_snapshot(snapshot, now_epoch)
            if screen is not None:
                result.append(screen)
        return result

    def rotation_screens(self, now_epoch):
        """Return fresh live matches as cycle screens.

        PRE fixtures are supplied by the calendar feed. POST results are
        one-shot MQTT presentations and are never stored in the rotation.
        """
        result = []
        for screen in self.screens(now_epoch):
            if screen.get("status") != "IN":
                continue
            screen = dict(screen)
            screen["id"] = "football-live-{}".format(screen["team_key"])
            result.append(screen)
        return result

    def screen_for_team(self, team_key, now_epoch):
        for screen in self.screens(now_epoch):
            if screen.get("team_key") == team_key:
                return screen
        return None

    def clear_live(self):
        """Forget cached live snapshots after a prolonged MQTT outage."""
        removed = []
        for team_key, snapshot in tuple(self._teams.items()):
            if snapshot.get("status") == "IN":
                removed.append(team_key)
                del self._teams[team_key]
                self._dynamic_flags.pop(team_key, None)
                self._goal_events.pop(team_key, None)
        return removed

    def staleness_changed(self, now_epoch):
        """Signal on live staleness, goal expiry, or final-result expiry changes."""
        if not self.enabled or now_epoch is None:
            return False
        now_ms = int(now_epoch * 1000)
        self._prune_goalapi(now_ms)
        current = {}
        for team_key, snapshot in self._teams.items():
            stale = False
            if snapshot.get("status") == "IN":
                stale = _live_stale(snapshot, now_ms)
            goal_until = snapshot.get("_goal_until")
            goal_active = goal_until is not None and now_ms < goal_until
            post_expired = football_post_expired(snapshot, now_epoch)
            current[team_key] = (stale, goal_active, post_expired)
        if current == self._dynamic_flags:
            return False
        self._dynamic_flags = current
        return True


class FootballPresentationQueue:
    """Queue live team refreshes and new POST screens deferred by a flash."""

    def __init__(self):
        self._pending = []
        self.last_update = "none"

    def accept_snapshot(self, state, topic, payload, now_epoch=None,
                        presenting_screen=None):
        """Accept updates and queue one-shot POST presentations."""
        item = _normalize(topic, payload, state.prefix)
        if item is None:
            self.last_update = "rejected"
            return False
        # Protect the screen currently on the matrix as well as the state cache.
        # A POST may arrive after a reconnect or state-cache reset, when
        # FootballScreenState no longer has the IN snapshot to compare against.
        if (presenting_screen is not None
                and presenting_screen.get("team_key") == item.get("team_key")
                and presenting_screen.get("status") == "IN"
                and item.get("status") != "IN"):
            live_source = presenting_screen.get("source_updated_at")
            incoming_source = item.get("_source_epoch")
            try:
                live_source = _epoch(live_source) if live_source is not None else None
            except (TypeError, ValueError):
                live_source = None
            if (item.get("status") != "POST"
                    or not _same_match_session(presenting_screen, item)
                    or live_source is None or incoming_source is None
                    or incoming_source <= live_source):
                self.last_update = "rejected_active_match_transition"
                return False
        accepted, screen = state.accept_for_presentation(topic, payload, now_epoch)
        if not accepted:
            self.last_update = state.last_decision
            return False
        team_key = topic[len(state.prefix):]
        if screen is None:
            self.last_update = "unavailable"
            self.discard(team_key)
        elif screen.get("status") == "POST":
            if screen.get("presentation_update") == "data_refresh":
                self.last_update = "post_refresh"
            else:
                self.last_update = "post_event"
                self.schedule_screen(screen)
        elif screen.get("status") == "IN" and screen.get("presentation_update") == "new_fixture_or_status":
            self._pending = [
                pending for pending in self._pending
                if not (isinstance(pending, dict)
                        and pending.get("team_key") == team_key
                        and pending.get("status") == "POST"
                        and not _same_match_session(pending, screen))
            ]
            if not (presenting_screen is not None
                    and presenting_screen.get("team_key") == team_key
                    and _same_match_session(presenting_screen, screen)):
                self.last_update = screen.get("presentation_update")
                self.schedule(team_key)
            else:
                self.last_update = "active_data_refresh"
        elif (screen.get("presentation_update") != "data_refresh"
              and not (presenting_screen is not None
                       and presenting_screen.get("team_key") == team_key
                       and _same_match_session(presenting_screen, screen))):
            self.last_update = screen.get("presentation_update", "score_changed")
            self.schedule(team_key)
        elif (presenting_screen is not None
              and presenting_screen.get("team_key") == team_key
              and _same_match_session(presenting_screen, screen)):
            self.last_update = (
                "active_score_refresh"
                if screen.get("presentation_update") == "score_changed"
                else "active_data_refresh"
            )
        else:
            self.last_update = screen.get("presentation_update", "data_refresh")
        return True

    def discard(self, team_key):
        """Remove deferred prompts for a club whose fixture is unavailable."""
        before = len(self._pending)
        self._pending = [
            pending for pending in self._pending
            if (pending.get("team_key") if isinstance(pending, dict) else pending) != team_key
        ]
        return len(self._pending) != before

    def discard_live(self, team_key):
        """Remove a deferred live prompt without dropping a queued final result."""
        before = len(self._pending)
        self._pending = [
            pending for pending in self._pending
            if not (
                (pending.get("team_key") == team_key
                 and pending.get("status") == "IN")
                if isinstance(pending, dict)
                else pending == team_key
            )
        ]
        return len(self._pending) != before

    def schedule_screen(self, screen):
        """Keep the latest pending result once per team/match until eligible."""
        team_key = screen.get("team_key")
        if not _valid_team_key(team_key):
            return False
        for index, pending in enumerate(self._pending):
            if (isinstance(pending, dict)
                    and pending.get("team_key") == team_key
                    and pending.get("status") == "POST"
                    and _same_match_session(pending, screen)):
                try:
                    pending_epoch = _epoch(pending.get("published_at"))
                    incoming_epoch = _epoch(screen.get("published_at"))
                except (TypeError, ValueError):
                    return False
                if incoming_epoch >= pending_epoch:
                    self._pending[index] = screen
                return True
        self._pending.append(screen)
        return True

    def schedule(self, team_key):
        if not _valid_team_key(team_key):
            return False
        if team_key in self._pending:
            return True
        self._pending.append(team_key)
        return True

    def pop(self, now_epoch=None):
        while self._pending:
            pending = self._pending.pop(0)
            if isinstance(pending, dict) and football_post_expired(pending, now_epoch):
                continue
            return pending
        return None

    def __len__(self):
        return len(self._pending)

