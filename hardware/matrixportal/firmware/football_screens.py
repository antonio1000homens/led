"""Validation and rotation snapshots for retained Team Tracker football MQTT."""

import json

from mqtt_screens import _epoch


FOOTBALL_TEAMS = ("sporting_cp", "millwall")
FOOTBALL_STATUSES = ("PRE", "IN", "POST", "BYE", "NOT_FOUND", "UNKNOWN", "UNAVAILABLE")
FOOTBALL_TEAM_NAMES = {"sporting_cp": "Sporting CP", "millwall": "Millwall FC"}
LIVE_STALE_SECONDS = 600
GOAL_FLASH_SECONDS = 8
SCREEN_DURATION_SECONDS = 20
FOOTBALL_INTRO_SECONDS = 6


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


def kickoff_datetime_label(kickoff):
    """Format a timezone-aware kickoff as the full UTC date and time."""
    if not isinstance(kickoff, str) or len(kickoff) < 20:
        return "FIXTURE TIME TBC"
    try:
        year, month, day = int(kickoff[:4]), int(kickoff[5:7]), int(kickoff[8:10])
        hour, minute = int(kickoff[11:13]), int(kickoff[14:16])
        second = int(kickoff[17:19])
        if (kickoff[4] != "-" or kickoff[7] != "-" or kickoff[10] != "T"
                or kickoff[13] != ":" or kickoff[16] != ":"):
            raise ValueError("timestamp")
        days_in_month = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
        if not (1 <= month <= 12 and 1 <= day <= days_in_month[month - 1]
                and year >= 1 and 0 <= hour <= 23 and 0 <= minute <= 59
                and 0 <= second <= 59):
            raise ValueError("timestamp")
        suffix = kickoff[19:]
        if suffix.startswith((".", ",")):
            position = 1
            while position < len(suffix) and suffix[position].isdigit():
                position += 1
            if position == 1:
                raise ValueError("timestamp")
            suffix = suffix[position:]
        if suffix == "Z":
            offset_minutes = 0
        elif len(suffix) == 6 and suffix[0] in ("+", "-") and suffix[3] == ":":
            offset_hour, offset_minute = int(suffix[1:3]), int(suffix[4:6])
            if offset_hour > 23 or offset_minute > 59:
                raise ValueError("timestamp")
            offset_minutes = (offset_hour * 60 + offset_minute) * (1 if suffix[0] == "+" else -1)
        else:
            raise ValueError("timestamp")
        utc_minutes = hour * 60 + minute - offset_minutes
        while utc_minutes < 0:
            utc_minutes += 1440
            day -= 1
            if day < 1:
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
                days_in_month = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
                day = days_in_month[month - 1]
        while utc_minutes >= 1440:
            utc_minutes -= 1440
            day += 1
            days_in_month = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                             31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
            if day > days_in_month[month - 1]:
                day = 1
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        months = ("January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December")
        utc_hour, utc_minute = divmod(utc_minutes, 60)
        return "{} {} {}, {:02d}:{:02d} UTC".format(
            day, months[month - 1], year, utc_hour, utc_minute
        )
    except (TypeError, ValueError, IndexError):
        return "FIXTURE TIME TBC"


def football_screen_lines(screen, now_epoch):
    """Return four compact rows suitable for the 256x32 display."""
    team = str(screen.get("team_name") or screen.get("team_key") or "FOOTBALL").upper()
    opponent = str(screen.get("opponent_long_name") or screen.get("opponent") or "").upper()
    fixture = screen.get("display_fixture")
    if not isinstance(fixture, str) or not fixture.strip():
        fixture = "{} VS {}".format(team, opponent) if opponent else team
    status = screen.get("status")
    competition = str(screen.get("competition") or "")
    if status == "PRE":
        return (
            "PRE",
            fixture,
            "KICKOFF: " + kickoff_datetime_label(screen.get("kickoff")),
            competition,
        )
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
                 "home_team", "away_team", "competition", "clock"):
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
            screen = {key: value for key, value in snapshot.items() if not key.startswith("_")}
            status = snapshot["status"]
            source_epoch = snapshot.get("_source_epoch")
            stale_live = (status == "IN" and (now_ms is None or source_epoch is None
                          or now_ms - source_epoch > LIVE_STALE_SECONDS * 1000))
            if stale_live:
                screen["status"] = "UNAVAILABLE"
                screen["home_score"] = None
                screen["away_score"] = None
                screen["clock"] = None
                screen["stale"] = True
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
            if status == "PRE":
                result.append({
                    "id": "football-intro-" + team_key,
                    "kind": "football_intro",
                    "title": "FOOTBALL",
                    "team_key": team_key,
                    "team_name": screen["title"],
                    "words": "MATCH DAY",
                    "duration_seconds": FOOTBALL_INTRO_SECONDS,
                    "source": "firmware",
                })
            result.append(screen)
        return result

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

