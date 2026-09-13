from datetime import datetime, timezone
import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
import unittest

from todoist import (
    SSMParameterOAuthStore,
    TodoistFeedUnavailable,
    TodoistOAuthSession,
    TodoistProvider,
    normalize_task,
)


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
    def __init__(self, results=None):
        self.results = list(results or [])
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(result)


class FakeAuth:
    def __init__(self, token="secret-token", refreshed_token="refreshed-token"):
        self.token = token
        self.refreshed_token = refreshed_token
        self.calls = []

    def access_token(self, force_refresh=False):
        self.calls.append(force_refresh)
        return self.refreshed_token if force_refresh else self.token


class FakeStore:
    def __init__(self, payload):
        self.payload = dict(payload)
        self.saved = []

    def load(self):
        return dict(self.payload)

    def save(self, payload):
        self.payload = dict(payload)
        self.saved.append(dict(payload))


class FakeSSMClient:
    def __init__(self, payload):
        self.payload = dict(payload)
        self.get_calls = []
        self.put_calls = []

    def get_parameter(self, **kwargs):
        self.get_calls.append(kwargs)
        return {"Parameter": {"Value": json.dumps(self.payload)}}

    def put_parameter(self, **kwargs):
        self.put_calls.append(kwargs)
        self.payload = json.loads(kwargs["Value"])
        return {"Version": 2}


class TodoistOAuthTests(unittest.TestCase):
    def test_ssm_store_loads_decrypted_securestring_and_saves_standard_tier(self):
        client = FakeSSMClient({"client_id": "id", "client_secret": "secret"})
        store = SSMParameterOAuthStore("/led/todoist/oauth", client=client)
        self.assertEqual(store.load()["client_id"], "id")
        self.assertEqual(
            client.get_calls[0],
            {"Name": "/led/todoist/oauth", "WithDecryption": True},
        )
        store.save({"client_id": "id", "refresh_token": "rotated"})
        call = client.put_calls[0]
        self.assertEqual(call["Name"], "/led/todoist/oauth")
        self.assertEqual(call["Type"], "SecureString")
        self.assertEqual(call["Tier"], "Standard")
        self.assertTrue(call["Overwrite"])
        self.assertEqual(client.payload["refresh_token"], "rotated")

    def test_reuses_fresh_access_token_without_refresh(self):
        store = FakeStore(
            {
                "client_id": "id",
                "client_secret": "secret",
                "access_token": "still-valid",
                "refresh_token": "refresh",
                "expires_at": 5000,
            }
        )
        opener = FakeOpener([])
        session = TodoistOAuthSession(store, opener=opener, time_fn=lambda: 1000)
        self.assertEqual(session.access_token(), "still-valid")
        self.assertEqual(opener.requests, [])
        self.assertEqual(store.saved, [])

    def test_refresh_rotates_and_persists_refresh_token(self):
        store = FakeStore(
            {
                "client_id": "client-id",
                "client_secret": "client-secret",
                "access_token": "expired-access",
                "refresh_token": "old-refresh",
                "expires_at": 900,
            }
        )
        opener = FakeOpener(
            [{
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 3600,
                "token_type": "Bearer",
                "scope": "data:read",
            }]
        )
        session = TodoistOAuthSession(store, opener=opener, time_fn=lambda: 1000)
        self.assertEqual(session.access_token(), "new-access")
        self.assertEqual(store.payload["refresh_token"], "new-refresh")
        self.assertEqual(store.payload["expires_at"], 4600)
        request = opener.requests[0][0]
        form = parse_qs(request.data.decode("utf-8"))
        self.assertEqual(form["grant_type"], ["refresh_token"])
        self.assertEqual(form["client_id"], ["client-id"])
        self.assertEqual(form["client_secret"], ["client-secret"])
        self.assertEqual(form["refresh_token"], ["old-refresh"])

    def test_grace_window_retry_without_replacement_refresh_token_is_rejected(self):
        store = FakeStore(
            {
                "client_id": "id",
                "client_secret": "secret",
                "access_token": "expired",
                "refresh_token": "consumed-refresh",
                "expires_at": 0,
            }
        )
        opener = FakeOpener([{"access_token": "replacement-access", "expires_in": 3600}])
        session = TodoistOAuthSession(store, opener=opener, time_fn=lambda: 1000)
        with self.assertRaises(TodoistFeedUnavailable):
            session.access_token()
        self.assertEqual(store.saved, [])


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
        auth = FakeAuth()
        opener = FakeOpener([first, second])
        provider = TodoistProvider(
            auth,
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

    def test_401_forces_refresh_once_and_retries_with_new_access_token(self):
        unauthorized = HTTPError("https://api.todoist.com", 401, "Unauthorized", {}, None)
        auth = FakeAuth(token="expired-access", refreshed_token="fresh-access")
        opener = FakeOpener([unauthorized, {"results": [], "next_cursor": None}])
        provider = TodoistProvider(auth, opener=opener, utcnow=lambda: self.now)
        self.assertEqual(provider.fetch(), [])
        self.assertEqual(auth.calls, [False, True])
        self.assertEqual(opener.requests[0][0].get_header("Authorization"), "Bearer expired-access")
        self.assertEqual(opener.requests[1][0].get_header("Authorization"), "Bearer fresh-access")

    def test_failure_does_not_expose_access_token(self):
        auth = FakeAuth(token="very-secret-token")
        provider = TodoistProvider(auth, opener=FakeOpener([RuntimeError("boom")]))
        with self.assertRaises(TodoistFeedUnavailable) as caught:
            provider.fetch()
        self.assertNotIn("very-secret-token", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
