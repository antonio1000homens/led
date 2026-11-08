"""Validation and prompt snapshots for football MQTT providers."""

import json
import re

from mqtt_screens import _epoch


FOOTBALL_TEAMS = ("sporting_cp", "millwall")
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
GOAL_SCORE_CONFIRM_SECONDS = 120
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
    """Eight orientations, two full turns during the slide; frozen on arrival."""
    _, settled = football_slide_offset(phase, animation_speed)
    if settled:
        return 0
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
    source_updated = snapshot.get("_source_epoch")
    if source_updated is None:
        return True
    stale_after = LIVE_STALE_SECONDS
    if snapshot.get("source") == "nrwindsor" and snapshot.get("provider") == "goalapi":
        stale_after = GOALAPI_LIVE_STALE_SECONDS
    return now_ms - source_updated > stale_after * 1000


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
            updated = snapshot.get("_source_epoch") or snapshot.get("_published_epoch")
            if updated is not None and now_ms - updated > GOALAPI_LIVE_STALE_SECONDS * 1000:
                del self._teams[team_key]
                self._dynamic_flags.pop(team_key, None)

    def accept(self, topic, payload):
        if not self.enabled or not isinstance(topic, str) or not topic.startswith(self.prefix):
            return False
        incoming = _normalize(topic, payload, self.prefix)
        if incoming is None:
            return False
        self._prune_goalapi(incoming["_published_epoch"])
        team_key = incoming["team_key"]
        previous = self._teams.get(team_key)
        if previous is not None:
            if incoming["_published_epoch"] <= previous["_published_epoch"]:
                return False
        is_goal_api = (incoming.get("source") == "nrwindsor"
                       and incoming.get("provider") == "goalapi")
        if is_goal_api:
            recent_events = self._goal_events.get(team_key, ())
            event_id = incoming.get("event_id")
            source_epoch = incoming.get("_source_epoch")
            if event_id and any(event_id == prior_id for prior_id, _ in recent_events):
                return False
            latest_epoch = max((epoch for _, epoch in recent_events if epoch is not None),
                               default=None)
            if (source_epoch is not None and latest_epoch is not None
                    and source_epoch < latest_epoch):
                return False
        if incoming.get("status") == "POST":
            if previous is not None and previous.get("status") == "IN":
                previous_ids = {
                    previous.get(name) for name in (
                        "fixture_key", "match_id", "provider_match_id", "event_id"
                    ) if previous.get(name)
                }
                incoming_ids = {
                    incoming.get(name) for name in (
                        "fixture_key", "match_id", "provider_match_id", "event_id"
                    ) if incoming.get(name)
                }
                if not previous_ids.intersection(incoming_ids):
                    return False
                previous_source_epoch = previous.get("_source_epoch")
                incoming_source_epoch = incoming.get("_source_epoch")
                if (previous_source_epoch is not None
                        and (incoming_source_epoch is None
                             or incoming_source_epoch < previous_source_epoch)):
                    return False
            # A final result is an MQTT event, not durable board state. Show
            # it through the presentation queue, then forget it so it cannot
            # reappear on later rotation cycles or after reconnects.
            self._teams.pop(team_key, None)
            self._dynamic_flags.pop(team_key, None)
            return True
        same_fixture = bool(
            previous is not None
            and previous.get("fixture_key")
            and incoming.get("fixture_key") == previous.get("fixture_key")
            and incoming.get("status") == previous.get("status") == "IN"
        )
        item = dict(previous) if same_fixture else {}
        item.update(incoming)
        if same_fixture:
            for name in ("event_id", "event_type", "event_created_at",
                         "previous_home_score", "previous_away_score"):
                if incoming.get(name) is None:
                    item.pop(name, None)
            if incoming.get("_source_epoch") is None and previous.get("_source_epoch") is not None:
                item["_source_epoch"] = previous["_source_epoch"]
                item["source_updated_at"] = previous.get("source_updated_at")
            # Live providers frequently omit values held by the other feed.
            for name in ("clock", "home_score", "away_score", "competition",
                         "team_name", "opponent", "opponent_long_name",
                         "display_fixture", "home_team", "away_team",
                         "homeaway", "team_homeaway", "kickoff"):
                if incoming.get(name) is None and previous.get(name) is not None:
                    item[name] = previous[name]

            pending_until = previous.get("_goal_score_until")
            pending_score = previous.get("_goal_score")
            is_goal_api = (incoming.get("source") == "nrwindsor"
                           and incoming.get("provider") == "goalapi")
            event_type = str(incoming.get("event_type") or "").lower()
            incoming_score = (incoming.get("home_score"), incoming.get("away_score"))
            previous_score = (previous.get("home_score"), previous.get("away_score"))
            valid_incoming_score = all(type(value) is int for value in incoming_score)
            if (is_goal_api and valid_incoming_score
                    and event_type in ("goal.scored", "score.changed")
                    and incoming_score != previous_score):
                item["_goal_score"] = incoming_score
                item["_goal_score_until"] = (
                    incoming["_published_epoch"]
                    + GOAL_SCORE_CONFIRM_SECONDS * 1000
                )
            elif (is_goal_api and pending_until is not None
                    and incoming_score == previous_score):
                item["_goal_score"] = pending_score
                item["_goal_score_until"] = pending_until
            elif (not is_goal_api and pending_until is not None
                    and incoming["_published_epoch"] < pending_until
                    and incoming_score != pending_score):
                item["home_score"], item["away_score"] = pending_score
                item["_goal_score_until"] = pending_until
                item["_goal_score"] = pending_score
                item["_score_source"] = "goalapi_pending_confirmation"
            else:
                item.pop("_goal_score_until", None)
                item.pop("_goal_score", None)
                item["_score_source"] = incoming.get("provider")

            if not is_goal_api and incoming_score == pending_score:
                item.pop("_goal_score_until", None)
                item.pop("_goal_score", None)

            if (event_type == "goal.scored" and valid_incoming_score
                    and (all(type(value) is int for value in previous_score)
                         or all(type(value) is int for value in (
                             incoming.get("previous_home_score"),
                             incoming.get("previous_away_score"))))):
                goal_previous = previous_score
                if all(type(value) is int for value in (
                        incoming.get("previous_home_score"),
                        incoming.get("previous_away_score"))):
                    goal_previous = (incoming["previous_home_score"],
                                     incoming["previous_away_score"])
                home_delta = incoming_score[0] - goal_previous[0]
                away_delta = incoming_score[1] - goal_previous[1]
                if home_delta == 1 and away_delta == 0:
                    item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                    item["_goal_side"] = "home"
                elif away_delta == 1 and home_delta == 0:
                    item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                    item["_goal_side"] = "away"
            elif (not is_goal_api and valid_incoming_score
                  and all(type(value) is int for value in previous_score)
                  and incoming["_source_epoch"] is not None
                  and previous.get("_source_epoch") is not None
                  and incoming["_source_epoch"] > previous["_source_epoch"]
                  and incoming_score != previous_score):
                home_delta = incoming_score[0] - previous_score[0]
                away_delta = incoming_score[1] - previous_score[1]
                if home_delta == 1 and away_delta == 0:
                    item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                    item["_goal_side"] = "home"
                elif away_delta == 1 and home_delta == 0:
                    item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                    item["_goal_side"] = "away"
        else:
            item["_goal_until"] = None
            item["_goal_side"] = None
            item["_score_source"] = incoming.get("provider")
            if (is_goal_api and incoming.get("status") == "IN"
                    and incoming.get("event_type") in ("goal.scored", "score.changed")
                    and all(type(value) is int for value in (
                        incoming.get("home_score"), incoming.get("away_score")))):
                item["_goal_score"] = (incoming["home_score"], incoming["away_score"])
                item["_goal_score_until"] = (
                    incoming["_published_epoch"]
                    + GOAL_SCORE_CONFIRM_SECONDS * 1000
                )
                if (incoming.get("event_type") == "goal.scored"
                        and all(type(value) is int for value in (
                            incoming.get("previous_home_score"),
                            incoming.get("previous_away_score")))):
                    home_delta = incoming["home_score"] - incoming["previous_home_score"]
                    away_delta = incoming["away_score"] - incoming["previous_away_score"]
                    if home_delta == 1 and away_delta == 0:
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "home"
                    elif away_delta == 1 and home_delta == 0:
                        item["_goal_until"] = incoming["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                        item["_goal_side"] = "away"
        if is_goal_api:
            recent_events = self._goal_events.setdefault(team_key, [])
            recent_events.append((incoming.get("event_id"), incoming.get("_source_epoch")))
            if len(recent_events) > 64:
                del recent_events[:-64]
        self._teams[team_key] = item
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
        same_fixture = (previous is not None
                        and previous.get("fixture_key") == current.get("fixture_key")
                        and previous.get("status") == current.get("status"))
        score_changed = same_fixture and (
            (previous.get("home_score"), previous.get("away_score"))
            != (current.get("home_score"), current.get("away_score"))
        )
        screen["presentation_update"] = (
            "new_fixture_or_status" if not same_fixture
            else ("score_changed" if score_changed else "data_refresh")
        )
        return True, screen

    @staticmethod
    def _screen_from_snapshot(snapshot, now_epoch):
        status = snapshot["status"]
        if status not in ("PRE", "IN", "POST"):
            return None
        if status == "PRE" and not _has_fixture_data(snapshot):
            return None
        if football_post_expired(snapshot, now_epoch):
            return None
        now_ms = int(now_epoch * 1000) if now_epoch is not None else None
        screen = {key: value for key, value in snapshot.items() if not key.startswith("_")}
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
            live_ids = {
                presenting_screen.get(name) for name in (
                    "fixture_key", "match_id", "provider_match_id", "event_id"
                ) if presenting_screen.get(name)
            }
            incoming_ids = {
                item.get(name) for name in (
                    "fixture_key", "match_id", "provider_match_id", "event_id"
                ) if item.get(name)
            }
            live_source = presenting_screen.get("source_updated_at")
            incoming_source = item.get("_source_epoch")
            try:
                live_source = _epoch(live_source) if live_source is not None else None
            except (TypeError, ValueError):
                live_source = None
            if (item.get("status") != "POST"
                    or not live_ids.intersection(incoming_ids)
                    or live_source is None or incoming_source is None
                    or incoming_source <= live_source):
                self.last_update = "rejected_active_match_transition"
                return False
        accepted, screen = state.accept_for_presentation(topic, payload, now_epoch)
        if not accepted:
            self.last_update = "rejected"
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
        elif (screen.get("presentation_update") != "data_refresh"
              and not (presenting_screen is not None
                       and presenting_screen.get("team_key") == team_key
                       and presenting_screen.get("fixture_key") == screen.get("fixture_key"))):
            self.last_update = screen.get("presentation_update", "score_changed")
            self.schedule(team_key)
        elif (presenting_screen is not None
              and presenting_screen.get("team_key") == team_key
              and presenting_screen.get("fixture_key") == screen.get("fixture_key")):
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
        match_id = screen.get("match_id")
        for index, pending in enumerate(self._pending):
            if (isinstance(pending, dict)
                    and pending.get("team_key") == team_key
                    and pending.get("match_id") == match_id):
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

