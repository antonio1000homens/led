"""Backend-only fixtures: Google normalization, privacy, TTL and public PRE contract."""
import copy
from datetime import datetime, timedelta, timezone
import unittest
from urllib.parse import unquote

from football_calendar import (
    DEFAULT_ALIASES, GoogleCalendarFixtureProvider, normalize_event,
)
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import (
    RuntimeConfigValidationError, default_runtime_config, schema_metadata,
    validate_feed_patch, validate_runtime_config,
)


NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def event(event_id, title, start, **extras):
    data = {
        "id": event_id,
        "summary": title,
        "start": {"dateTime": start},
        "description": "PERSONAL PRIVATE DESCRIPTION",
        "location": "PRIVATE ADDRESS",
        "attendees": [{"email": "secret@example.com"}],
    }
    data.update(extras)
    return data


def secret():
    return {
        "client_id": "client-private",
        "client_secret": "secret-private",
        "refresh_token": "refresh-private",
        "calendars": {"sporting_cp": ["sporting-private@group.calendar.google.com"],
                      "millwall": ["millwall-private@group.calendar.google.com"]},
    }


class FakeHttp:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.fail = False

    def __call__(self, url, data=None, headers=None):
        self.calls.append((url, data, headers))
        if self.fail:
            raise OSError("google unavailable")
        if "oauth2.googleapis.com" in url:
            return {"access_token": "sensitive-access-token"}
        for key, values in self.responses.items():
            if key in unquote(url):
                return {"items": copy.deepcopy(values)}
        raise AssertionError("unexpected API request")


class MemoryStore:
    def __init__(self):
        self.state = {"version": 2, "feeds": {}}
        self.payload = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def publish(self, payload):
        self.payload = copy.deepcopy(payload)


class FakeRail:
    def fetch(self):
        return [{"time": "16:00", "destination": "Waterloo"}]


class FakeFootball:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def fetch(self, now, lookahead_days=45):
        self.calls.append((now, lookahead_days))
        value = next(self.results)
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def sanitized(team, kickoff, match_id="match"):
    return {
        "team_key": team,
        "team_name": "Sporting CP" if team == "sporting_cp" else "Millwall FC",
        "opponent_long_name": "FC Porto",
        "display_fixture": "Sporting CP vs FC Porto",
        "home_away": "home",
        "kickoff": kickoff,
        "match_id": match_id,
    }


class FootballCalendarTests(unittest.TestCase):
    def test_rejects_non_match_private_canceled_allday_float_and_out_of_window(self):
        aliases = {name.casefold() for name in DEFAULT_ALIASES["sporting_cp"]}
        source = event("a", "Meet Sporting CP at library", "2026-10-25T17:00:00+00:00")
        fixtures = [
            source,
            event("b", "Sporting CP vs Porto", "2026-10-25T17:00:00+00:00", status="cancelled"),
            event("c", "Sporting CP vs Porto", "2026-10-25T17:00:00"),
            {"id": "d", "summary": "Sporting CP vs Porto", "start": {"date": "2026-10-25"}},
            event("e", "Sporting CP vs Porto", "2026-10-23T17:00:00+01:00"),
            event("f", "Sporting CP vs Porto", "2026-12-30T17:00:00+00:00"),
            event("g", "Sporting CP vs bad@address.test", "2026-10-25T17:00:00+00:00"),
            event("h", "Sporting CP vs Sporting CP", "2026-10-25T17:00:00+00:00"),
        ]
        for item in fixtures:
            with self.subTest(item=item["id"]):
                self.assertIsNone(normalize_event(
                    item, calendar_id="private-id", team_key="sporting_cp",
                    aliases=aliases, now=NOW, window_end=NOW + timedelta(days=40)))

    def test_next_fixture_for_both_teams_and_dst_is_london_local(self):
        responses = {
            "sporting-private": [
                event("next", "Sporting CP vs FC Porto", "2026-10-25T16:00:00+00:00"),
                event("later", "Benfica vs Sporting CP", "2026-10-30T19:00:00+00:00"),
            ],
            "millwall-private": [
                event("next-millwall", "Millwall FC vs Leeds United", "2026-10-25T10:00:00+01:00"),
                event("later-millwall", "Derby County vs Millwall", "2026-10-29T19:00:00Z"),
            ],
        }
        http = FakeHttp(responses)
        provider = GoogleCalendarFixtureProvider(
            "/led/football/calendar", settings_loader=secret, request_json=http)
        result = provider.fetch(NOW)
        self.assertEqual([r["team_key"] for r in result], ["sporting_cp", "millwall"])
        self.assertEqual(result[0]["opponent_long_name"], "FC Porto")
        self.assertEqual(result[0]["kickoff"], "2026-10-25T16:00:00+00:00")
        self.assertEqual(result[1]["kickoff"], "2026-10-25T09:00:00+00:00")
        self.assertEqual(result[1]["home_away"], "home")
        self.assertEqual(len(result[0]["match_id"]), 32)
        raw_output = str(result)
        for forbidden in ("PERSONAL PRIVATE", "PRIVATE ADDRESS", "secret@example.com",
                          "refresh-private", "sporting-private"):
            self.assertNotIn(forbidden, raw_output)
        self.assertEqual(len(http.calls), 3)
        self.assertTrue(all("Bearer sensitive-access-token" in str(call[2])
                            for call in http.calls[1:]))

    def test_reschedule_keeps_identity_but_updates_kickoff(self):
        aliases = {name.casefold() for name in DEFAULT_ALIASES["sporting_cp"]}
        base = dict(calendar_id="fixture-calendar", team_key="sporting_cp",
                    aliases=aliases, now=NOW, window_end=NOW + timedelta(days=45))
        first = normalize_event(event("event-123", "Sporting CP vs Braga",
                                      "2026-10-27T20:00:00+00:00"), **base)
        moved = normalize_event(event("event-123", "Sporting CP vs Braga",
                                      "2026-10-28T21:00:00+00:00"), **base)
        another = normalize_event(event("event-456", "Sporting CP vs Braga",
                                        "2026-10-28T21:00:00+00:00"), **base)
        self.assertEqual(first["match_id"], moved["match_id"])
        self.assertNotEqual(first["kickoff"], moved["kickoff"])
        self.assertNotEqual(moved["match_id"], another["match_id"])

    def test_explicit_annotation_allows_custom_titles_but_not_wrong_team(self):
        aliases = {name.casefold() for name in DEFAULT_ALIASES["millwall"]}
        base = dict(calendar_id="private", team_key="millwall",
                    aliases=aliases, now=NOW, window_end=NOW + timedelta(days=45))
        item = event("1", "Cup 3rd round", "2026-10-31T15:00:00Z",
                     extendedProperties={"private": {
                         "led_team_key": "millwall", "led_opponent": "Arsenal",
                         "led_home_away": "away", "secret_note": "never expose"}})
        normalized = normalize_event(item, **base)
        self.assertEqual(normalized["opponent_long_name"], "Arsenal")
        self.assertEqual(normalized["home_away"], "away")
        self.assertNotIn("secret_note", normalized)
        item["extendedProperties"]["private"]["led_team_key"] = "sporting_cp"
        self.assertIsNone(normalize_event(item, **base))

    def test_invalid_secrets_fail_closed(self):
        for faulty in ({}, {"calendars": {"foo": "bar"}},
                       {**secret(), "calendars": {"unknown": ["id"]}},
                       {**secret(), "calendars": {"millwall": []}}):
            provider = GoogleCalendarFixtureProvider(
                "/led/football/calendar", settings_loader=lambda: faulty,
                request_json=FakeHttp({}))
            with self.assertRaises(ValueError):
                provider.fetch(NOW)

    def test_runtime_configuration_is_isolated_and_migrated(self):
        default = default_runtime_config({})
        self.assertFalse(default["feeds"]["football_fixtures"]["enabled"])
        self.assertEqual(default["feeds"]["football_fixtures"]["poll_seconds"], 900)
        self.assertEqual(default["feeds"]["calendar"]["visible_task_count"], 6)
        self.assertIn("football_fixtures", schema_metadata()["feeds"])
        old = copy.deepcopy(default)
        del old["feeds"]["football_fixtures"]
        upgraded = validate_runtime_config(old)
        self.assertFalse(upgraded["feeds"]["football_fixtures"]["enabled"])
        self.assertEqual(
            validate_feed_patch("football_fixtures", {"lookahead_days": 90}),
            {"lookahead_days": 90},
        )
        for value in (0, 181, True, "45"):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("football_fixtures", {"lookahead_days": value})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("football_fixtures", {"calendar_id": "secret"})

    def test_publisher_ttl_rollover_staleness_privacy_and_independence(self):
        now = [NOW]
        store = MemoryStore()
        config = PublisherConfig(
            bucket="test", national_rail_token="test", thorpe_park_source="off",
            weather_source="off", football_fixture_source="google_calendar")
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        runtime_store = StaticRuntimeConfigStore(runtime)
        provider = FakeFootball([
            [sanitized("sporting_cp", "2026-10-25T15:00:00+00:00"),
             sanitized("millwall", "2026-10-26T15:00:00+00:00", "second")],
            RuntimeError("Google outage with private details"),
            [sanitized("sporting_cp", "2026-10-29T20:00:00+00:00", "third")],
        ])

        def run():
            return Publisher(config, store, rail_provider=FakeRail(),
                             football_provider=provider, utcnow=lambda: now[0],
                             runtime_config_store=runtime_store).run()

        first = run()
        cards = [s for s in first["screens"] if s["kind"] == "football_score"]
        self.assertEqual(len(cards), 2)
        self.assertEqual([c["id"] for c in cards], ["football-sporting_cp", "football-millwall"])
        self.assertTrue(all(c["status"] == "PRE" and c["source"] == "google_calendar" for c in cards))
        self.assertFalse(any(k in cards[0] for k in ("home_score", "description", "location",
                                                     "attendees", "clock")))
        self.assertEqual(provider.calls[0][1], 45)
        now[0] += timedelta(minutes=2)
        self.assertEqual(len([s for s in run()["screens"] if s["kind"] == "football_score"]), 2)
        self.assertEqual(len(provider.calls), 1)
        now[0] += timedelta(minutes=14)
        failed = run()
        self.assertEqual(len(provider.calls), 2)
        self.assertTrue(next(s for s in failed["screens"]
                             if s["id"] == "football-sporting_cp")["stale"])
        self.assertIn("departures", [s["id"] for s in failed["screens"]])
        now[0] = datetime(2026, 10, 25, 16, tzinfo=timezone.utc)
        aged = run()
        self.assertIn("football-millwall", [s["id"] for s in aged["screens"]])
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(next(s for s in aged["screens"] if s["id"] == "football-sporting_cp")["match_id"], "third")
        self.assertEqual(len([s for s in aged["screens"] if s["kind"] == "football_score"]), 2)

    def test_cold_failure_respects_ttl_and_does_not_block_rail(self):
        store = MemoryStore()
        now = [NOW]
        config = PublisherConfig(bucket="test", national_rail_token="test",
                                 thorpe_park_source="off", weather_source="off")
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        football = FakeFootball([RuntimeError("google failure"), []])

        def run():
            return Publisher(config, store, rail_provider=FakeRail(),
                             football_provider=football, utcnow=lambda: now[0],
                             runtime_config_store=StaticRuntimeConfigStore(runtime)).run()

        self.assertIn("departures", [s["id"] for s in run()["screens"]])
        now[0] += timedelta(seconds=61)
        run()
        self.assertEqual(len(football.calls), 1)
        now[0] += timedelta(minutes=16)
        run()
        self.assertEqual(len(football.calls), 2)


if __name__ == "__main__":
    unittest.main()
