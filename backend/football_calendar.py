"""Read-only Google Calendar fixture source for the public football PRE screen feed.

The SSM SecureString is the only place calendar identifiers, OAuth credentials,
and optional aliases live.  The provider never returns raw calendar events.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TEAM_NAMES = {"sporting_cp": "Sporting CP", "millwall": "Millwall FC"}
DEFAULT_ALIASES = {
    "sporting_cp": ("Sporting CP", "Sporting Clube de Portugal"),
    "millwall": ("Millwall FC", "Millwall"),
}
LONDON = ZoneInfo("Europe/London")
GOOGLE_API = "https://www.googleapis.com/calendar/v3/calendars/"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
MATCHUP = re.compile(r"^(.+?)\s+(vs?\.?|versus|@)\s+(.+?)$", re.IGNORECASE)
SAFE_TEXT = re.compile(r"^[^\x00-\x1f\x7f<>@/\\]+$")
MAX_PAGES_PER_CALENDAR = 3


def _clean_name(value):
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not (2 <= len(cleaned) <= 70) or not SAFE_TEXT.fullmatch(cleaned):
        return None
    return cleaned


def _request_json(url, data=None, headers=None):
    req = Request(url, data=data, headers=headers or {})
    with urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_ssm(parameter_name):
    import boto3
    value = boto3.client("ssm").get_parameter(Name=parameter_name, WithDecryption=True)
    return json.loads(value["Parameter"]["Value"])


def _credentials(raw):
    if not isinstance(raw, dict):
        raise ValueError("football calendar secret must contain a JSON object")
    for field in ("client_id", "client_secret", "refresh_token"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise ValueError("football calendar secret is missing OAuth credentials")
    calendars = raw.get("calendars")
    if not isinstance(calendars, dict) or not calendars:
        raise ValueError("football calendar secret needs team calendar mappings")
    if set(calendars) - set(TEAM_NAMES):
        raise ValueError("football calendar secret has unsupported teams")
    checked = {}
    for team, ids in calendars.items():
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, list) or not 1 <= len(ids) <= 4 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 254 for item in ids
        ):
            raise ValueError("football calendar IDs must be a non-empty array of identifiers")
        checked[team] = [item.strip() for item in ids]
    aliases = {}
    custom = raw.get("aliases", {})
    if not isinstance(custom, dict) or set(custom) - set(TEAM_NAMES):
        raise ValueError("football calendar aliases must be a team mapping")
    for team in TEAM_NAMES:
        extra = custom.get(team, [])
        if not isinstance(extra, list) or len(extra) > 8 or any(
            _clean_name(name) is None for name in extra
        ):
            raise ValueError("football calendar alias names must be bounded text")
        aliases[team] = {name.casefold() for name in DEFAULT_ALIASES[team] + tuple(extra)}
    return checked, aliases


def normalize_event(event, *, calendar_id, team_key, aliases, now, window_end):
    """Accept explicit LED metadata or an anchored team-v-opponent event title.

    Never infer a match from an arbitrary appointment or expose private details.
    Rescheduling keeps match_id stable: kickoff is a separate, updated field.
    """
    if not isinstance(event, dict) or event.get("status") == "cancelled":
        return None
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id or len(event_id) > 512:
        return None
    start = event.get("start")
    if not isinstance(start, dict) or not isinstance(start.get("dateTime"), str):
        return None  # all-day / floating-time calendar events are not kickoff times
    try:
        kickoff = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
    except ValueError:
        return None
    if kickoff.tzinfo is None or kickoff.utcoffset() is None:
        return None
    utc_kickoff = kickoff.astimezone(timezone.utc)
    if not now < utc_kickoff < window_end:
        return None

    private = (event.get("extendedProperties") or {}).get("private") or {}
    if not isinstance(private, dict):
        return None
    if private.get("led_team_key") and private["led_team_key"] != team_key:
        return None
    opponent = None
    home_away = None
    if private.get("led_team_key") == team_key:
        opponent = _clean_name(private.get("led_opponent"))
        home_away = private.get("led_home_away")
        if home_away not in (None, "home", "away", "unknown"):
            return None
    else:
        summary = event.get("summary")
        matched = MATCHUP.fullmatch(" ".join(summary.split())) if isinstance(summary, str) else None
        if matched:
            left, connector, right = matched.groups()
            left, right = _clean_name(left), _clean_name(right)
            if left and right:
                if left.casefold() in aliases and right.casefold() not in aliases:
                    opponent, home_away = right, "away" if connector == "@" else "home"
                elif right.casefold() in aliases and left.casefold() not in aliases and connector != "@":
                    opponent, home_away = left, "away"
    if not opponent or opponent.casefold() in aliases:
        return None
    match_id = hashlib.sha256(
        (calendar_id + "\x00" + event_id).encode("utf-8")
    ).hexdigest()[:32]
    team_name = TEAM_NAMES[team_key]
    return {
        "team_key": team_key,
        "team_name": team_name,
        "opponent_long_name": opponent,
        "display_fixture": team_name + " vs " + opponent,
        "home_away": home_away or "unknown",
        "kickoff": utc_kickoff.astimezone(LONDON).isoformat(),
        "match_id": match_id,
    }


class GoogleCalendarFixtureProvider:
    """Configurable, read-only Google Calendar OAuth source, poll-gated by Publisher."""

    def __init__(self, parameter_name, settings_loader=None, request_json=None):
        self.parameter_name = parameter_name
        self.settings_loader = settings_loader or (lambda: _read_ssm(parameter_name))
        self.request_json = request_json or _request_json

    def fetch(self, now, lookahead_days=45):
        if now.tzinfo is None:
            raise ValueError("calendar fetch requires timezone-aware current time")
        if not 1 <= lookahead_days <= 180:
            raise ValueError("invalid football calendar lookahead")
        now = now.astimezone(timezone.utc)
        end = now + timedelta(days=lookahead_days)
        raw = self.settings_loader()
        calendars, aliases = _credentials(raw)
        token = self.request_json(
            GOOGLE_TOKEN_URL,
            data=urlencode({
                "client_id": raw["client_id"],
                "client_secret": raw["client_secret"],
                "refresh_token": raw["refresh_token"],
                "grant_type": "refresh_token",
            }).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if not isinstance(token, dict) or not isinstance(token.get("access_token"), str):
            raise ValueError("Google Calendar OAuth refresh did not provide an access token")
        headers = {"Authorization": "Bearer " + token["access_token"]}
        fixtures = []
        for team_key, ids in calendars.items():
            candidates = []
            for calendar_id in ids:
                page_token = None
                for _ in range(MAX_PAGES_PER_CALENDAR):
                    params = {
                        "timeMin": now.isoformat().replace("+00:00", "Z"),
                        "timeMax": end.isoformat().replace("+00:00", "Z"),
                        "singleEvents": "true",
                        "orderBy": "startTime",
                        "maxResults": "250",
                        "fields": "nextPageToken,items(id,status,summary,start(dateTime,timeZone),extendedProperties(private))",
                    }
                    if page_token:
                        params["pageToken"] = page_token
                    url = GOOGLE_API + quote(calendar_id, safe="") + "/events?" + urlencode(params)
                    response = self.request_json(url, headers=headers)
                    if not isinstance(response, dict) or not isinstance(response.get("items"), list):
                        raise ValueError("Google Calendar returned an invalid event list")
                    for event in response["items"]:
                        fixture = normalize_event(
                            event, calendar_id=calendar_id, team_key=team_key,
                            aliases=aliases[team_key], now=now, window_end=end,
                        )
                        if fixture:
                            candidates.append(fixture)
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
                else:
                    # Never silently claim "next match" if earlier pages were incomplete.
                    raise ValueError("Google Calendar page limit reached")
            if candidates:
                fixtures.append(min(candidates, key=lambda row: row["kickoff"]))
        return fixtures
