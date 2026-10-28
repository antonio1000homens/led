"""Validation and rotation snapshots for retained Team Tracker football MQTT."""

import json

from mqtt_screens import _epoch


FOOTBALL_TEAMS = ("sporting_cp", "millwall")
FOOTBALL_STATUSES = ("PRE", "IN", "POST", "BYE", "NOT_FOUND", "UNKNOWN", "UNAVAILABLE")
FOOTBALL_TEAM_NAMES = {"sporting_cp": "Sporting CP", "millwall": "Millwall FC"}
LIVE_STALE_SECONDS = 600
GOAL_FLASH_SECONDS = 8
SCREEN_DURATION_SECONDS = 20
FOOTBALL_SLIDE_SECONDS = 3.2
FOOTBALL_START_X = 256
FOOTBALL_END_X = 2
FOOTBALL_BALL_WIDTH = 16
FOOTBALL_TEXT_X = FOOTBALL_END_X + FOOTBALL_BALL_WIDTH + 4


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
        return "KO: {} {:02d} {} {:02d}:{:02d}".format(
            weekdays[weekday], day, months[month - 1], hour, minute
        )
    except (TypeError, ValueError, IndexError, OverflowError):
        return "KO: TBC"


def football_presentation_position(phase, animate=True):
    """Return the ball x coordinate and whether match text can be shown."""
    if not animate:
        return FOOTBALL_END_X, True
    try:
        elapsed = max(0.0, float(phase or 0))
    except (TypeError, ValueError):
        elapsed = 0.0
    travel = FOOTBALL_START_X - FOOTBALL_END_X
    x = max(FOOTBALL_END_X, FOOTBALL_START_X - int(travel * elapsed / FOOTBALL_SLIDE_SECONDS))
    return x, x == FOOTBALL_END_X


def football_screen_lines(screen, now_epoch):
    """Return status-specific text rows for the 256x32 display."""
    team = str(screen.get("team_name") or screen.get("team_key") or "FOOTBALL").upper()
    opponent = str(screen.get("opponent_long_name") or screen.get("opponent") or "").upper()
    fixture = screen.get("display_fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        fixture = "{} VS {}".format(team, opponent) if opponent else team
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
        return fixture.upper(), kickoff_local_label(screen.get("kickoff"))
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
    if payload.get("schema_version") != 1 or payload.get("source") != "homeassistant":
        return None
    if payload.get("provider") != "teamtracker":
        return None
    if not isinstance(topic, str) or not topic.startswith(prefix):
        return None
    team_key = topic[len(prefix):]
    if team_key not in FOOTBALL_TEAMS or payload.get("team_key") != team_key:
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
    except (TypeError, ValueError):
        return None
    match_id = payload.get("match_id")
    if match_id is not None and not _short_text(match_id, 128):
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
    return result


class FootballScreenState:
    """Keep each club's latest valid snapshot without affecting MQTT cycle screens."""

    def __init__(self, topic_filter="led/football/+", enabled=True):
        if (not isinstance(topic_filter, str) or not topic_filter.endswith("/+")
                or "+" in topic_filter[:-1] or "#" in topic_filter):
            raise ValueError("MQTT_FOOTBALL_TOPIC must be a single-level wildcard")
        self.prefix = topic_filter[:-1]
        self.enabled = bool(enabled)
        self._teams = {}
        self._dynamic_flags = {}

    def accept(self, topic, payload):
        if not self.enabled or not isinstance(topic, str) or not topic.startswith(self.prefix):
            return False
        item = _normalize(topic, payload, self.prefix)
        if item is None:
            return False
        team_key = item["team_key"]
        previous = self._teams.get(team_key)
        if previous is not None:
            if item["_published_epoch"] <= previous["_published_epoch"]:
                return False
        item["_goal_until"] = None
        item["_goal_side"] = None
        if previous is not None and (
            previous.get("status") == "IN"
            and item.get("status") == "IN"
            and previous.get("match_id")
            and item.get("match_id") == previous.get("match_id")
            and previous.get("home_score") is not None
            and previous.get("away_score") is not None
            and item.get("home_score") is not None
            and item.get("away_score") is not None
            and item.get("_source_epoch") is not None
            and previous.get("_source_epoch") is not None
            and item["_source_epoch"] > previous["_source_epoch"]
        ):
            home_delta = item["home_score"] - previous["home_score"]
            away_delta = item["away_score"] - previous["away_score"]
            if home_delta == 1 and away_delta == 0:
                item["_goal_until"] = item["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                item["_goal_side"] = "home"
            elif away_delta == 1 and home_delta == 0:
                item["_goal_until"] = item["_published_epoch"] + GOAL_FLASH_SECONDS * 1000
                item["_goal_side"] = "away"
        self._teams[team_key] = item
        return True

    def screens(self, now_epoch):
        if not self.enabled:
            return []
        result = []
        now_ms = int(now_epoch * 1000) if now_epoch is not None else None
        for team_key in FOOTBALL_TEAMS:
            snapshot = self._teams.get(team_key)
            if snapshot is None:
                continue
            status = snapshot["status"]
            if status not in ("PRE", "IN", "POST"):
                continue
            if status == "PRE" and not _has_fixture_data(snapshot):
                continue
            screen = {key: value for key, value in snapshot.items() if not key.startswith("_")}
            source_epoch = snapshot.get("_source_epoch")
            stale_live = (status == "IN" and (now_ms is None or source_epoch is None
                          or now_ms - source_epoch > LIVE_STALE_SECONDS * 1000))
            if stale_live:
                screen["status"] = "UNAVAILABLE"
                screen["home_score"] = None
                screen["away_score"] = None
                screen["clock"] = None
                screen["stale"] = True
                continue
            else:
                screen["stale"] = False
            goal_until = snapshot.get("_goal_until")
            if goal_until is not None and now_ms is not None and now_ms < goal_until:
                screen["goal_side"] = snapshot.get("_goal_side")
                screen["goal_flash_active"] = True
            screen.update({
                "id": "football-" + team_key,
                "kind": "football_score",
                "title": screen.get("team_name") or FOOTBALL_TEAM_NAMES.get(team_key, "FOOTBALL"),
                "duration_seconds": SCREEN_DURATION_SECONDS,
                "source": "homeassistant_teamtracker",
            })
            result.append(screen)
        return result

    def screen_for_team(self, team_key, now_epoch):
        for screen in self.screens(now_epoch):
            if screen.get("team_key") == team_key:
                return screen
        return None

    def staleness_changed(self, now_epoch):
        """Signal only when a retained IN snapshot crosses the stale boundary."""
        if not self.enabled or now_epoch is None:
            return False
        now_ms = int(now_epoch * 1000)
        current = {}
        for team_key, snapshot in self._teams.items():
            stale = False
            if snapshot.get("status") == "IN":
                source_epoch = snapshot.get("_source_epoch")
                stale = (source_epoch is None
                         or now_ms - source_epoch > LIVE_STALE_SECONDS * 1000)
            goal_until = snapshot.get("_goal_until")
            goal_active = goal_until is not None and now_ms < goal_until
            current[team_key] = (stale, goal_active)
        if current == self._dynamic_flags:
            return False
        self._dynamic_flags = current
        return True


class FootballPresentationQueue:
    """Bound pending event presentations to one coalesced item per club."""

    def __init__(self):
        self._pending = []
        self._queued = set()
        self._shown_fixture = {}

    def accept_snapshot(self, state, topic, payload, now_epoch=None):
        """Queue only accepted updates that currently have a displayable screen."""
        if not state.accept(topic, payload):
            return False
        team_key = topic[len(state.prefix):]
        screen = state.screen_for_team(team_key, now_epoch)
        if screen is None:
            self.discard(team_key)
            self._shown_fixture.pop(team_key, None)
        else:
            fixture_key = (screen.get("match_id") or
                           (screen.get("kickoff"), screen.get("display_fixture"),
                            screen.get("opponent")))
            if self._shown_fixture.get(team_key) != fixture_key:
                self._shown_fixture[team_key] = fixture_key
                self.schedule(team_key)
        return True

    def discard(self, team_key):
        """Remove one club's pending presentation after its fixture disappears."""
        if team_key not in self._queued:
            return False
        self._pending = [pending for pending in self._pending if pending != team_key]
        self._queued.discard(team_key)
        return True

    def schedule(self, team_key):
        if team_key not in FOOTBALL_TEAMS or team_key in self._queued:
            return False
        self._pending.append(team_key)
        self._queued.add(team_key)
        return True

    def pop(self):
        if not self._pending:
            return None
        team_key = self._pending.pop(0)
        self._queued.discard(team_key)
        return team_key

    def __len__(self):
        return len(self._pending)

