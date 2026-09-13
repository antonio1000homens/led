"""Todoist adapter for the renderer-neutral upcoming-events feed."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


TODOIST_FILTER_URL = "https://api.todoist.com/api/v1/tasks/filter"
DEFAULT_FILTER_QUERY = "date after: yesterday"
DEFAULT_TIMEZONE = "Europe/London"
DEFAULT_MAX_EVENTS = 6


class TodoistFeedUnavailable(RuntimeError):
    """Todoist could not provide usable upcoming-event data."""


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
        token,
        filter_query=DEFAULT_FILTER_QUERY,
        timezone_name=DEFAULT_TIMEZONE,
        max_events=DEFAULT_MAX_EVENTS,
        timeout=10,
        opener=None,
        utcnow=None,
    ):
        token = str(token or "").strip()
        if not token:
            raise ValueError("Todoist token is required")
        self.token = token
        self.filter_query = str(filter_query or DEFAULT_FILTER_QUERY).strip()
        if not self.filter_query:
            raise ValueError("Todoist filter query is required")
        self.timezone_name = timezone_name or DEFAULT_TIMEZONE
        _zone(self.timezone_name)
        self.max_events = max(1, int(max_events))
        self.timeout = timeout
        self.opener = opener or urlopen
        self.utcnow = utcnow or (lambda: datetime.now(timezone.utc))

    def _page(self, cursor=None):
        params = {"query": self.filter_query, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        request = Request(
            TODOIST_FILTER_URL + "?" + urlencode(params),
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/json",
                "User-Agent": "led-information-board/1.0",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
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
