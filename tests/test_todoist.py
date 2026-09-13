from datetime import datetime, timezone
import json
from urllib.parse import parse_qs, urlparse
import unittest

from todoist import TodoistFeedUnavailable, TodoistProvider, normalize_task


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeOpener:
    def __init__(self, payloads=None, error=None):
        self.payloads = list(payloads or [])
        self.error = error
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if self.error is not None:
            raise self.error
        return FakeResponse(self.payloads.pop(0))


class TodoistProviderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 13, 11, 0, tzinfo=timezone.utc)

    def test_normalizes_timed_task_to_london_time(self):
        event = normalize_task(
            {"content": "Appointment", "due": {"date": "2026-09-13T12:30:00Z"}},
            now=self.now,
        )
        self.assertEqual(event["date_text"], "13/09")
        self.assertEqual(event["time_text"], "13:30")
        self.assertEqual(event["start"], "2026-09-13T13:30:00+01:00")

    def test_floating_time_uses_due_timezone_when_present(self):
        event = normalize_task(
            {"content": "Call", "due": {"date": "2026-09-13T15:00:00", "timezone": "Europe/Lisbon"}},
            now=self.now,
        )
        self.assertEqual(event["time_text"], "15:00")

    def test_all_day_today_is_retained(self):
        event = normalize_task(
            {"content": "Inset day", "due": {"date": "2026-09-13"}},
            now=self.now,
        )
        self.assertTrue(event["all_day"])
        self.assertEqual(event["time_text"], "ALL")

    def test_past_timed_and_undated_tasks_are_excluded(self):
        self.assertIsNone(normalize_task({"content": "Old", "due": {"date": "2026-09-13T10:00:00Z"}}, now=self.now))
        self.assertIsNone(normalize_task({"content": "No date"}, now=self.now))

    def test_paginates_sorts_and_limits_to_next_six(self):
        first = {
            "results": [
                {"content": "Later", "due": {"date": "2026-09-16T18:00:00+01:00"}},
                {"content": "Tomorrow", "due": {"date": "2026-09-14T09:00:00+01:00"}},
            ],
            "next_cursor": "cursor-2",
        }
        second = {
            "results": [
                {"content": "Today", "due": {"date": "2026-09-13T18:00:00+01:00"}},
                {"content": "All day", "due": {"date": "2026-09-15"}},
                {"content": "Five", "due": {"date": "2026-09-17T09:00:00+01:00"}},
                {"content": "Six", "due": {"date": "2026-09-18T09:00:00+01:00"}},
                {"content": "Seven", "due": {"date": "2026-09-19T09:00:00+01:00"}},
            ],
            "next_cursor": None,
        }
        opener = FakeOpener([first, second])
        provider = TodoistProvider(
            "secret-token",
            filter_query="date after: yesterday & #Home",
            opener=opener,
            utcnow=lambda: self.now,
        )
        events = provider.fetch()

        self.assertEqual(len(events), 6)
        self.assertEqual([event["title"] for event in events[:3]], ["Today", "Tomorrow", "All day"])
        self.assertEqual(len(opener.requests), 2)
        first_request = opener.requests[0][0]
        self.assertEqual(first_request.get_header("Authorization"), "Bearer secret-token")
        first_query = parse_qs(urlparse(first_request.full_url).query)
        self.assertEqual(first_query["query"], ["date after: yesterday & #Home"])
        second_query = parse_qs(urlparse(opener.requests[1][0].full_url).query)
        self.assertEqual(second_query["cursor"], ["cursor-2"])

    def test_failure_does_not_expose_token(self):
        provider = TodoistProvider("very-secret-token", opener=FakeOpener(error=RuntimeError("boom")))
        with self.assertRaises(TodoistFeedUnavailable) as caught:
            provider.fetch()
        self.assertNotIn("very-secret-token", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
