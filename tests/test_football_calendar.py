"""Backend-only fixtures: Google normalization, privacy, TTL and public PRE contract."""
import copy
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote

from football_calendar import (
    DEFAULT_ALIASES, GoogleCalendarFixtureProvider, PublicICalFixtureProvider,
    PUBLIC_ICAL_CALENDARS, normalize_event,
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

    def fetch(self, now, lookahead_days=45, enabled_teams=None):
        self.calls.append((now, lookahead_days, enabled_teams))
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
        self.assertNotIn("football-millwall", [s["id"] for s in aged["screens"]])
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(next(s for s in aged["screens"] if s["id"] == "football-sporting_cp")["match_id"], "third")
        self.assertEqual(len([s for s in aged["screens"] if s["kind"] == "football_score"]), 1)

    def test_kickoff_refreshes_next_fixture_before_ttl_and_throttles_failure(self):
        now = [NOW]
        store = MemoryStore()
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        provider = FakeFootball([
            [sanitized("sporting_cp", "2026-10-24T12:05:00+00:00", "first")],
            [sanitized("sporting_cp", "2026-10-24T12:10:00+00:00", "second")],
            RuntimeError("calendar unavailable"),
        ])
        publisher = Publisher(
            PublisherConfig(bucket="test", national_rail_token="test", thorpe_park_source="off",
                            weather_source="off", football_fixture_source="google_calendar"),
            store, rail_provider=FakeRail(), football_provider=provider,
            utcnow=lambda: now[0], runtime_config_store=StaticRuntimeConfigStore(runtime),
        )
        def fixture_ids():
            return [s["match_id"] for s in publisher.run()["screens"] if s["kind"] == "football_score"]

        self.assertEqual(fixture_ids(), ["first"])
        now[0] += timedelta(minutes=4)
        self.assertEqual(fixture_ids(), ["first"])
        self.assertEqual(len(provider.calls), 1)
        now[0] += timedelta(minutes=1)
        self.assertEqual(fixture_ids(), ["second"])
        self.assertEqual(len(provider.calls), 2)
        now[0] += timedelta(minutes=5)
        self.assertEqual(fixture_ids(), [])
        self.assertEqual(len(provider.calls), 3)
        now[0] += timedelta(minutes=1)
        self.assertEqual(fixture_ids(), [])
        self.assertEqual(len(provider.calls), 3)

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


    def test_cached_expired_fixture_does_not_reappear_during_provider_outage(self):
        store = MemoryStore()
        now = [NOW]
        config = PublisherConfig(bucket="test", national_rail_token="test",
                                 thorpe_park_source="off", weather_source="off")
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        football = FakeFootball([
            [sanitized("sporting_cp", "2026-10-24T13:00:00+00:00", "past-soon"),
             sanitized("millwall", "2026-10-30T19:45:00+00:00", "next-millwall")],
            RuntimeError("provider outage"),
        ])

        def run():
            return Publisher(config, store, rail_provider=FakeRail(),
                             football_provider=football, utcnow=lambda: now[0],
                             runtime_config_store=StaticRuntimeConfigStore(runtime)).run()

        run()
        now[0] += timedelta(hours=2)
        payload = run()
        cards = [s for s in payload["screens"] if s["kind"] == "football_score"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["team_key"], "millwall")
        self.assertTrue(cards[0]["stale"])
        self.assertEqual(len(football.calls), 2)

    def test_duplicate_fixture_entries_never_make_duplicate_public_cards(self):
        store = MemoryStore()
        config = PublisherConfig(bucket="test", national_rail_token="test",
                                 thorpe_park_source="off", weather_source="off")
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        repeated = sanitized("millwall", "2026-10-30T20:00:00+00:00")
        football = FakeFootball([[repeated, repeated]])
        payload = Publisher(config, store, rail_provider=FakeRail(),
                            football_provider=football, utcnow=lambda: NOW,
                            runtime_config_store=StaticRuntimeConfigStore(runtime)).run()
        cards = [s for s in payload["screens"] if s["kind"] == "football_score"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["id"], "football-millwall")



    def test_real_calendar_title_format_and_competition_suffix(self):
        samples = (
            ("sporting_cp", "Casa Pia - Sporting Portugal", "Casa Pia", "away"),
            ("sporting_cp", "Shakhtar Donetsk - Sporting Portugal [CL]", "Shakhtar Donetsk", "away"),
            ("sporting_cp", "Sporting Portugal - Moreirense", "Moreirense", "home"),
            ("millwall", "Millwall FC - Derby County", "Derby County", "home"),
            ("millwall", "Birmingham City - Millwall FC", "Birmingham City", "away"),
            ("portugal", "Portugal - Denmark", "Denmark", "home"),
            ("england", "Spain - England", "Spain", "away"),
        )
        for team_key, summary, opponent, home_away in samples:
            with self.subTest(team=team_key, summary=summary):
                result = normalize_event(
                    event("uid", summary, "2026-11-01T16:00:00Z"),
                    calendar_id="test", team_key=team_key,
                    aliases={a.casefold() for a in DEFAULT_ALIASES[team_key]},
                    now=NOW, window_end=NOW + timedelta(days=45),
                )
                self.assertIsNotNone(result)
                self.assertEqual(result["opponent_long_name"], opponent)
                self.assertEqual(result["home_away"], home_away)
        unrelated = normalize_event(
            event("bad", "Meet with Millwall FC - fundraising", "2026-11-01T16:00:00Z"),
            calendar_id="test", team_key="millwall",
            aliases={a.casefold() for a in DEFAULT_ALIASES["millwall"]},
            now=NOW, window_end=NOW + timedelta(days=45),
        )
        self.assertIsNone(unrelated)

    def test_public_ical_provider_uses_supplied_links_and_skips_disabled_teams(self):
        expected = {
            "sporting_cp": "fd67v39hov7a8uplrk8djd818c@group.calendar.google.com",
            "millwall": "rajefpgnm1ue0j6eae1ob9us1s@group.calendar.google.com",
            "portugal": "c88a0605u3b1m04j217pnqfkfs@group.calendar.google.com",
            "england": "ulqvlgdfg9ag1kuv4vlvjd1tuc@group.calendar.google.com",
        }
        self.assertEqual(PUBLIC_ICAL_CALENDARS, expected)
        feeds = {
            "sporting_cp": (
                "Casa Pia - Sporting Portugal", "20261030T201500Z",
            ),
            "millwall": (
                "Millwall FC - Derby County", "20261031T150000Z",
            ),
            "portugal": (
                "Portugal - Denmark", "20261114T194500Z",
            ),
            "england": (
                "England - Croatia", "20261112T194500Z",
            ),
        }
        requests = []

        def fake_ical(url):
            requests.append(url)
            key = next(k for k, value in expected.items() if value.replace("@", "%40") in url)
            title, timestamp = feeds[key]
            text = (
                "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//TEST//EN\r\n"
                "BEGIN:VEVENT\r\nUID:unique-" + key + "\r\n"
                "DTSTAMP:20261020T120000Z\r\nDTSTART:" + timestamp + "\r\n"
                "DTEND:" + timestamp + "\r\n"
                "SUMMARY:" + title + "\r\n"
                "STATUS:CONFIRMED\r\nDESCRIPTION:SECRET\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
            )
            return text.encode("utf-8")

        provider = PublicICalFixtureProvider(fetch_ical=fake_ical)
        fixtures = provider.fetch(NOW)
        self.assertEqual([x["team_key"] for x in fixtures], ["sporting_cp", "millwall"])
        self.assertEqual([x["opponent_long_name"] for x in fixtures], ["Casa Pia", "Derby County"])
        self.assertEqual(len(requests), 2)
        self.assertNotIn("portugal", str(requests))
        self.assertNotIn("england", str(requests))
        self.assertNotIn("SECRET", str(fixtures))
        tests = provider.fetch(NOW, enabled_teams=("portugal", "england"))
        self.assertEqual([x["team_key"] for x in tests], ["portugal", "england"])
        self.assertEqual([x["opponent_long_name"] for x in tests], ["Denmark", "Croatia"])

    def test_public_ical_ignores_all_day_cancelled_and_expired_fixtures(self):
        def fake_ical(_url):
            return (
                "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n"
                "BEGIN:VEVENT\r\nUID:all-day\r\nDTSTAMP:20261020T120000Z\r\n"
                "DTSTART;VALUE=DATE:20261030\r\nDTEND;VALUE=DATE:20261031\r\n"
                "SUMMARY:Millwall FC - Bad\r\nEND:VEVENT\r\n"
                "BEGIN:VEVENT\r\nUID:cancelled\r\nDTSTAMP:20261020T120000Z\r\n"
                "DTSTART:20261030T150000Z\r\nDTEND:20261030T160000Z\r\n"
                "SUMMARY:Millwall FC - Cancelled\r\nSTATUS:CANCELLED\r\nEND:VEVENT\r\n"
                "BEGIN:VEVENT\r\nUID:past\r\nDTSTAMP:20261020T120000Z\r\n"
                "DTSTART:20261001T150000Z\r\nDTEND:20261001T160000Z\r\n"
                "SUMMARY:Millwall FC - Old\r\nEND:VEVENT\r\n"
                "BEGIN:VEVENT\r\nUID:valid\r\nDTSTAMP:20261020T120000Z\r\n"
                "DTSTART:20261031T150000Z\r\nDTEND:20261031T160000Z\r\n"
                "SUMMARY:Millwall FC - Derby County\r\nEND:VEVENT\r\n"
                "END:VCALENDAR\r\n"
            ).encode()
        provider = PublicICalFixtureProvider(fetch_ical=fake_ical)
        result = provider.fetch(NOW, enabled_teams=("millwall",))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["opponent_long_name"], "Derby County")

    def test_public_ical_valid_empty_calendar_is_success(self):
        calls = []

        def empty_calendar(url):
            calls.append(url)
            return b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

        provider = PublicICalFixtureProvider(fetch_ical=empty_calendar)
        self.assertEqual(provider.fetch(NOW, enabled_teams=("sporting_cp", "millwall")), [])
        self.assertEqual(len(calls), 2)

    def test_public_ical_checks_sources_independently_and_identifies_http_failure(self):
        calls = []

        def one_source_fails(url):
            calls.append(url)
            if len(calls) == 1:
                raise HTTPError(url, 503, "private provider detail", {}, None)
            return b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"

        provider = PublicICalFixtureProvider(fetch_ical=one_source_fails)
        with self.assertRaises(RuntimeError) as caught:
            provider.fetch(NOW, enabled_teams=("sporting_cp", "millwall"))
        self.assertEqual(caught.exception.stage, "http_rejection")
        self.assertEqual(caught.exception.source, "sporting_cp")
        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("private provider detail", str(caught.exception))

    def test_public_ical_malformed_response_is_parse_failure_not_empty_success(self):
        provider = PublicICalFixtureProvider(fetch_ical=lambda _url: b"not a calendar")
        with self.assertRaises(RuntimeError) as caught:
            provider.fetch(NOW, enabled_teams=("millwall",))
        self.assertEqual(caught.exception.stage, "parse")
        self.assertEqual(caught.exception.source, "millwall")

    def test_public_ical_normalization_error_has_its_own_stage(self):
        raw = (
            "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:x\r\n"
            "DTSTART:20261030T150000Z\r\nSUMMARY:Millwall FC - Derby County\r\n"
            "END:VEVENT\r\nEND:VCALENDAR\r\n"
        ).encode()
        provider = PublicICalFixtureProvider(fetch_ical=lambda _url: raw)
        with patch("football_calendar.normalize_event", side_effect=ValueError("private normalization detail")):
            with self.assertRaises(RuntimeError) as caught:
                provider.fetch(NOW, enabled_teams=("millwall",))
        self.assertEqual(caught.exception.stage, "normalize")

    def test_team_enablement_flags_default_migrate_validate_and_filter_output(self):
        default = default_runtime_config({})
        expected = {
            "sporting_cp_enabled": True, "millwall_enabled": True,
            "portugal_enabled": False, "england_enabled": False,
        }
        for field, value in expected.items():
            self.assertEqual(default["feeds"]["football_fixtures"][field], value)
            self.assertEqual(
                validate_feed_patch("football_fixtures", {field: not value})[field],
                not value,
            )
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("football_fixtures", {field: "true"})
        old = copy.deepcopy(default)
        for field in expected:
            del old["feeds"]["football_fixtures"][field]
        upgraded = validate_runtime_config(old)
        for field, value in expected.items():
            self.assertEqual(upgraded["feeds"]["football_fixtures"][field], value)

        store = MemoryStore()
        config = PublisherConfig(bucket="test", national_rail_token="test",
                                 thorpe_park_source="off", weather_source="off",
                                 football_fixture_source="public_ical")
        runtime = default_runtime_config({})
        runtime["feeds"]["football_fixtures"]["enabled"] = True
        fixture = [
            sanitized("sporting_cp", "2026-10-30T20:15:00+00:00", "s"),
            sanitized("millwall", "2026-10-31T15:00:00+00:00", "m"),
            sanitized("portugal", "2026-11-14T19:45:00+00:00", "p"),
            sanitized("england", "2026-11-12T19:45:00+00:00", "e"),
        ]
        publisher = Publisher(config, store, rail_provider=FakeRail(),
                              football_provider=FakeFootball([fixture]), utcnow=lambda: NOW,
                              runtime_config_store=StaticRuntimeConfigStore(runtime))
        payload = publisher.run()
        cards = [x for x in payload["screens"] if x["kind"] == "football_score"]
        self.assertEqual([x["team_key"] for x in cards], ["sporting_cp", "millwall"])
        self.assertTrue(all(x["source"] == "public_ical" for x in cards))
        self.assertTrue(all("opponent_long_name" in x for x in cards))


    def test_at_separator_maps_selected_club_to_correct_home_away_side(self):
        cases = (
            ("sporting_cp", "Porto @ Sporting CP", "Porto", "home"),
            ("sporting_cp", "Sporting CP @ Porto", "Porto", "away"),
            ("millwall", "Derby County @ Millwall FC", "Derby County", "home"),
            ("millwall", "Millwall FC @ Derby County", "Derby County", "away"),
            ("portugal", "Denmark @ Portugal", "Denmark", "home"),
            ("england", "England @ Spain", "Spain", "away"),
        )
        for team, title, opponent, home_away in cases:
            with self.subTest(team=team, title=title):
                data = normalize_event(
                    event("game", title, "2026-10-31T15:00:00Z"),
                    calendar_id="calendar", team_key=team,
                    aliases={alias.casefold() for alias in DEFAULT_ALIASES[team]},
                    now=NOW, window_end=NOW + timedelta(days=45),
                )
                self.assertIsNotNone(data)
                self.assertEqual(data["opponent_long_name"], opponent)
                self.assertEqual(data["home_away"], home_away)

    def test_calendar_source_selection_does_not_enable_feed_before_admin_opt_in(self):
        for source in ("off", "google_calendar", "public_ical"):
            with self.subTest(source=source):
                runtime = default_runtime_config({"LED_FOOTBALL_FIXTURE_SOURCE": source})
                self.assertFalse(runtime["feeds"]["football_fixtures"]["enabled"])
                self.assertFalse(runtime["feeds"]["football_fixtures"]["portugal_enabled"])
                self.assertFalse(runtime["feeds"]["football_fixtures"]["england_enabled"])

    def test_team_changes_refresh_before_ttl_and_never_fetch_disabled_teams(self):
        store = MemoryStore()
        config = PublisherConfig(
            bucket="test", national_rail_token="test",
            thorpe_park_source="off", weather_source="off",
            football_fixture_source="public_ical",
        )
        runtime = default_runtime_config({})
        settings = runtime["feeds"]["football_fixtures"]
        settings["enabled"] = True
        now = [NOW]
        football = FakeFootball([
            [sanitized("sporting_cp", "2026-10-30T20:15:00+00:00", "sp"),
             sanitized("millwall", "2026-10-31T15:00:00+00:00", "mi")],
            [sanitized("portugal", "2026-11-14T19:45:00+00:00", "po")],
        ])
        runtime_store = StaticRuntimeConfigStore(runtime)
        # The store intentionally snapshots configs, as DynamoDB does. Change
        # its persisted copy to simulate a subsequent authenticated PATCH.
        settings = runtime_store.config["feeds"]["football_fixtures"]

        def run():
            return Publisher(
                config, store, rail_provider=FakeRail(), football_provider=football,
                utcnow=lambda: now[0], runtime_config_store=runtime_store,
            ).run()

        first = run()
        self.assertEqual(
            [s["team_key"] for s in first["screens"] if s["kind"] == "football_score"],
            ["sporting_cp", "millwall"],
        )
        self.assertEqual(football.calls[0][2], ["sporting_cp", "millwall"])
        now[0] += timedelta(minutes=1)
        run()
        self.assertEqual(len(football.calls), 1)  # unchanged team selection, cache hit

        settings["sporting_cp_enabled"] = False
        settings["millwall_enabled"] = False
        settings["portugal_enabled"] = True
        updated = run()
        self.assertEqual(football.calls[1][2], ["portugal"])
        self.assertEqual(
            [s["team_key"] for s in updated["screens"] if s["kind"] == "football_score"],
            ["portugal"],
        )
        self.assertEqual(len(football.calls), 2)  # change bypasses original TTL

        settings["portugal_enabled"] = False
        empty = run()
        self.assertFalse([s for s in empty["screens"] if s["kind"] == "football_score"])
        self.assertEqual(len(football.calls), 2)  # no calendar requests when all off

    def test_failed_selection_change_respects_retry_interval(self):
        store = MemoryStore()
        config = PublisherConfig(
            bucket="test", national_rail_token="test",
            thorpe_park_source="off", weather_source="off",
            football_fixture_source="public_ical",
        )
        runtime = default_runtime_config({})
        settings = runtime["feeds"]["football_fixtures"]
        settings["enabled"] = True
        now = [NOW]
        football = FakeFootball([
            [sanitized("sporting_cp", "2026-10-30T20:15:00+00:00", "sporting")],
            OSError("private HTTP failure"),
            [sanitized("portugal", "2026-11-14T19:45:00+00:00", "portugal")],
        ])
        runtime_store = StaticRuntimeConfigStore(runtime)
        # The store intentionally snapshots configs, as DynamoDB does. Change
        # its persisted copy to simulate a subsequent authenticated PATCH.
        settings = runtime_store.config["feeds"]["football_fixtures"]

        def run():
            return Publisher(
                config, store, rail_provider=FakeRail(), football_provider=football,
                utcnow=lambda: now[0], runtime_config_store=runtime_store,
            ).run()

        run()
        settings["sporting_cp_enabled"] = False
        settings["millwall_enabled"] = False
        settings["portugal_enabled"] = True
        now[0] += timedelta(minutes=1)
        failed = run()
        self.assertEqual(len(football.calls), 2)
        self.assertFalse([s for s in failed["screens"] if s["kind"] == "football_score"])
        now[0] += timedelta(minutes=1)
        run()
        self.assertEqual(len(football.calls), 2)  # no runaway retry on config mismatch
        now[0] += timedelta(minutes=16)
        result = run()
        self.assertEqual(len(football.calls), 3)
        self.assertEqual(
            [s["team_key"] for s in result["screens"] if s["kind"] == "football_score"],
            ["portugal"],
        )

    def test_google_calendar_request_count_is_capped(self):
        private = secret()
        private["calendars"] = {
            "sporting_cp": ["cal-1", "cal-2", "cal-3", "cal-4"],
            "millwall": ["cal-5", "cal-6", "cal-7", "cal-8"],
        }
        requests = []

        def fake_request(url, data=None, headers=None):
            requests.append(url)
            if "oauth2.googleapis.com" in url:
                return {"access_token": "test-access-token"}
            return {"items": []}

        provider = GoogleCalendarFixtureProvider(
            "/led/football/calendar", settings_loader=lambda: private,
            request_json=fake_request,
        )
        with self.assertRaisesRegex(ValueError, "request budget exceeded"):
            provider.fetch(NOW, enabled_teams=("sporting_cp", "millwall"))
        self.assertEqual(len(requests), 7)  # one token plus at most six event queries
        self.assertTrue(all("googleapis.com" in url for url in requests))


if __name__ == "__main__":
    unittest.main()
