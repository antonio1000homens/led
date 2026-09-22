"""Todoist OAuth and upcoming-events adapter."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
import json
import time as time_module
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TODOIST_FILTER_URL = "https://api.todoist.com/api/v1/tasks/filter"
TODOIST_TOKEN_URL = "https://api.todoist.com/oauth/access_token"
DEFAULT_FILTER_QUERY = "date after: yesterday"
DEFAULT_TIMEZONE = "Europe/London"
DEFAULT_MAX_EVENTS = 6
TOKEN_REFRESH_MARGIN_SECONDS = 60


class TodoistFeedUnavailable(RuntimeError):
    """Todoist could not provide usable upcoming-event data."""


class SSMParameterOAuthStore:
    """Persist Todoist OAuth credentials in one SSM Standard SecureString parameter."""

    def __init__(self, parameter_name, client=None):
        self.parameter_name = str(parameter_name or "").strip()
        if not self.parameter_name:
            raise ValueError("Todoist OAuth SSM parameter name is required")
        if client is None:
            import boto3

            client = boto3.client("ssm")
        self.client = client

    def load(self):
        try:
            response = self.client.get_parameter(Name=self.parameter_name, WithDecryption=True)
            payload = json.loads((response.get("Parameter") or {}).get("Value") or "{}")
        except Exception as error:
            raise TodoistFeedUnavailable("Todoist OAuth credentials are unavailable") from error
        if not isinstance(payload, dict):
            raise TodoistFeedUnavailable("Todoist OAuth credentials are invalid")
        return payload

    def save(self, payload):
        try:
            self.client.put_parameter(
                Name=self.parameter_name,
                Value=json.dumps(payload, separators=(",", ":")),
                Type="SecureString",
                Tier="Standard",
                Overwrite=True,
            )
        except Exception as error:
            raise TodoistFeedUnavailable("Todoist OAuth token rotation could not be persisted") from error


# Compatibility alias while the publisher configuration name is migrated from the
# original Secrets Manager implementation. The implementation above uses SSM only.
SecretsManagerOAuthStore = SSMParameterOAuthStore


class TodoistOAuthSession:
    """Supply valid access tokens and persist every refresh-token rotation."""

    def __init__(self, store, opener=None, timeout=10, time_fn=None):
        self.store = store
        self.opener = opener or urlopen
        self.timeout = timeout
        self.time_fn = time_fn or time_module.time
        self._credentials = None

    def _load(self):
        if self._credentials is None:
            self._credentials = self.store.load()
        return self._credentials

    def _access_is_fresh(self, credentials):
        token = str(credentials.get("access_token") or "").strip()
        if not token:
            return False
        try:
            expires_at = float(credentials.get("expires_at"))
        except (TypeError, ValueError):
            return False
        return expires_at > float(self.time_fn()) + TOKEN_REFRESH_MARGIN_SECONDS

    def _refresh(self, credentials):
        client_id = str(credentials.get("client_id") or "").strip()
        client_secret = str(credentials.get("client_secret") or "").strip()
        refresh_token = str(credentials.get("refresh_token") or "").strip()
        if not client_id or not client_secret or not refresh_token:
            raise TodoistFeedUnavailable("Todoist OAuth authorization must be bootstrapped again")

        body = urlencode(
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
        ).encode("utf-8")
        request = Request(
            TODOIST_TOKEN_URL,
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "led-information-board/1.0",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as error:
            raise TodoistFeedUnavailable("Todoist OAuth refresh failed") from error

        access_token = str(payload.get("access_token") or "").strip() if isinstance(payload, dict) else ""
        replacement_refresh = str(payload.get("refresh_token") or "").strip() if isinstance(payload, dict) else ""
        if not access_token:
            raise TodoistFeedUnavailable("Todoist OAuth refresh returned no access token")
        if not replacement_refresh:
            # Todoist omits the replacement refresh token when an already-consumed
            # token is retried inside its grace window. Persisting the old token here
            # would make the next refresh unsafe and can trigger replay revocation.
            raise TodoistFeedUnavailable("Todoist OAuth refresh token rotation was not recoverable")
        try:
            expires_in = max(1, int(payload.get("expires_in") or 3600))
        except (TypeError, ValueError):
            expires_in = 3600

        updated = dict(credentials)
        updated.update(
            {
                "access_token": access_token,
                "refresh_token": replacement_refresh,
                "token_type": str(payload.get("token_type") or "Bearer"),
                "scope": str(payload.get("scope") or credentials.get("scope") or "data:read"),
                "expires_at": int(float(self.time_fn())) + expires_in,
            }
        )
        self.store.save(updated)
        self._credentials = updated
        return access_token

    def access_token(self, force_refresh=False):
        credentials = self._load()
        if not force_refresh and self._access_is_fresh(credentials):
            return str(credentials["access_token"])
        return self._refresh(credentials)


def _zone(name):
    try:
        return ZoneInfo(str(name or DEFAULT_TIMEZONE))
    except ZoneInfoNotFoundError as error:
        raise ValueError("Invalid Todoist display timezone") from error


def _parse_timed_due(value, due_timezone, display_zone):
    text = str(value or "").strip()
    if not text or "T" not in text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_zone(due_timezone) if due_timezone else display_zone)
    return parsed.astimezone(display_zone)


def normalize_task(task, now=None, timezone_name=DEFAULT_TIMEZONE):
    """Normalize one Todoist task, returning None when it is not upcoming."""
    if not isinstance(task, dict):
        return None
    due = task.get("due")
    if not isinstance(due, dict):
        return None
    raw_date = str(due.get("date") or "").strip()
    if not raw_date:
        return None

    display_zone = _zone(timezone_name)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    local_now = now.astimezone(display_zone)
    title = str(task.get("content") or "").strip() or "Untitled task"

    if "T" not in raw_date:
        try:
            due_date = date.fromisoformat(raw_date[:10])
        except ValueError:
            return None
        if due_date < local_now.date():
            return None
        effective = datetime.combine(due_date, time.min, tzinfo=display_zone)
        return {
            "start": due_date.isoformat(),
            "all_day": True,
            "date_text": due_date.strftime("%d/%m"),
            "time_text": "ALL",
            "title": title,
            "_sort": effective,
        }

    due_at = _parse_timed_due(raw_date, due.get("timezone"), display_zone)
    if due_at is None or due_at < local_now:
        return None
    return {
        "start": due_at.isoformat(),
        "all_day": False,
        "date_text": due_at.strftime("%d/%m"),
        "time_text": due_at.strftime("%H:%M"),
        "title": title,
        "_sort": due_at,
    }


class TodoistProvider:
    source = "todoist"

    def __init__(
        self,
        auth,
        filter_query=DEFAULT_FILTER_QUERY,
        timezone_name=DEFAULT_TIMEZONE,
        max_events=DEFAULT_MAX_EVENTS,
        timeout=10,
        opener=None,
        utcnow=None,
    ):
        if auth is None or not callable(getattr(auth, "access_token", None)):
            raise ValueError("Todoist OAuth session is required")
        self.auth = auth
        self.filter_query = str(filter_query or DEFAULT_FILTER_QUERY).strip()
        if not self.filter_query:
            raise ValueError("Todoist filter query is required")
        self.timezone_name = timezone_name or DEFAULT_TIMEZONE
        _zone(self.timezone_name)
        self.max_events = max(1, int(max_events))
        self.timeout = timeout
        self.opener = opener or urlopen
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))

    def _page(self, cursor=None, refreshed=False):
        params = {"query": self.filter_query, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        token = self.auth.access_token(force_refresh=refreshed)
        request = Request(
            TODOIST_FILTER_URL + "?" + urlencode(params),
            headers={
                "Authorization": "Bearer " + token,
                "Accept": "application/json",
                "User-Agent": "led-information-board/1.0",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 401 and not refreshed:
                return self._page(cursor, refreshed=True)
            raise TodoistFeedUnavailable("Todoist upcoming events are unavailable") from error
        except Exception as error:
            raise TodoistFeedUnavailable("Todoist upcoming events are unavailable") from error
        if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
            raise TodoistFeedUnavailable("Todoist returned an invalid task response")
        return payload

    def fetch(self):
        """Return the next scheduled tasks in chronological order."""
        tasks = []
        cursor = None
        seen_cursors = set()
        while True:
            payload = self._page(cursor)
            tasks.extend(payload.get("results") or [])
            cursor = payload.get("next_cursor")
            if not cursor:
                break
            if cursor in seen_cursors:
                raise TodoistFeedUnavailable("Todoist pagination did not advance")
            seen_cursors.add(cursor)

        now = self.utcnow()
        events = []
        for task in tasks:
            event = normalize_task(task, now=now, timezone_name=self.timezone_name)
            if event is not None:
                events.append(event)
        events.sort(key=lambda event: (event["_sort"], event["title"].casefold()))
        for event in events:
            event.pop("_sort", None)
        return events[: self.max_events]
