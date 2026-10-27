from datetime import datetime, timezone
import json
import random
import unittest

from football_screens import (
    FootballScreenState, football_screen_lines, kickoff_countdown,
    kickoff_datetime_label,
)
from screen_client import ScreenRotation


def epoch(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def snapshot(team_key="sporting_cp", published="2026-10-26T20:00:00Z", **changes):
    value = {
        "schema_version": 1,
        "source": "homeassistant",
        "provider": "teamtracker",
        "team_key": team_key,
        "status": "PRE",
        "match_id": "event-123",
        "team_name": "Sporting CP",
        "opponent": "Benfica",
        "opponent_long_name": "Benfica",
        "display_fixture": "Sporting CP vs Benfica",
        "homeaway": "home",
        "team_homeaway": "home",
        "home_team": "SCP",
        "away_team": "BEN",
        "team_score": None,
        "opponent_score": None,
        "home_score": None,
        "away_score": None,
        "clock": None,
        "kickoff": "2026-10-26T22:00:00+00:00",
        "competition": "League",
        "published_at": published,
        "source_updated_at": published,
    }
    value.update(changes)
    return value


def score_screen(state, now):
    return next(screen for screen in state.screens(now)
                if screen.get("kind") == "football_score")


class FootballScreenTests(unittest.TestCase):
    def setUp(self):
        self.state = FootballScreenState()
        self.now = epoch("2026-10-26T20:00:00Z")

    def test_retained_topics_recover_each_team_independently(self):
        sporting = snapshot()
        millwall = snapshot("millwall", team_name="Millwall FC")
        self.assertTrue(self.state.accept("led/football/sporting_cp", sporting))
        self.assertTrue(self.state.accept("led/football/millwall", json.dumps(millwall)))
        self.assertEqual([s["kind"] for s in self.state.screens(self.now)],
                         ["football_intro", "football_score", "football_intro", "football_score"])
        rebooted = FootballScreenState()
        self.assertTrue(rebooted.accept("led/football/sporting_cp", sporting))
        self.assertEqual(len(rebooted.screens(self.now)), 2)

    def test_both_clubs_join_the_existing_http_and_mqtt_rotation(self):
        self.state.accept("led/football/sporting_cp", snapshot())
        self.state.accept("led/football/millwall", snapshot("millwall", team_name="Millwall FC"))
        http = [{"id": "departures", "kind": "rail_combined", "duration_seconds": 30}]
        mqtt = [{"id": "recycling", "kind": "bin_collection", "duration_seconds": 20}]
        rotation = ScreenRotation(rng=random.Random(1))
        rotation.update_sources(http, mqtt + self.state.screens(self.now), 1000)
        kinds = [screen["kind"] for screen in rotation.screens]
        self.assertIn("rail_combined", kinds)
        self.assertIn("bin_collection", kinds)
        self.assertEqual(kinds.count("football_score"), 2)
        self.assertEqual(kinds.count("football_intro"), 2)
        self.assertEqual(
            {screen["id"] for screen in rotation.screens if screen["kind"] == "football_score"},
            {"football-sporting_cp", "football-millwall"},
        )

    def test_sorted_mqtt_football_intros_stay_paired_with_scores(self):
        for seed in range(25):
            with self.subTest(seed=seed):
                state = FootballScreenState()
                state.accept("led/football/sporting_cp", snapshot())
                state.accept("led/football/millwall",
                             snapshot("millwall", team_name="Millwall FC"))
                rotation = ScreenRotation(rng=random.Random(seed))
                rotation.update_sources([
                    {"id": "rail", "kind": "rail_combined", "duration_seconds": 30},
                    {"id": "joke", "kind": "dad_joke", "duration_seconds": 5},
                    {"id": "fact", "kind": "random_fact", "duration_seconds": 5},
                ], state.screens(self.now), 1000)
                ids = [item["id"] for item in rotation.screens]
                for team in ("sporting_cp", "millwall"):
                    self.assertEqual(
                        ids.index("football-" + team),
                        ids.index("football-intro-" + team) + 1,
                    )

    def test_football_intro_orphan_is_removed_after_score_disappears(self):
        state = FootballScreenState()
        state.accept("led/football/sporting_cp", snapshot())
        state.accept("led/football/millwall",
                     snapshot("millwall", team_name="Millwall FC"))
        rotation = ScreenRotation(rng=random.Random(1))
        http = [{"id": "rail", "kind": "rail_combined", "duration_seconds": 30}]
        mqtt = state.screens(self.now)
        rotation.update_sources(http, mqtt, 1000)
        self.assertEqual(sum(x["kind"] == "football_intro" for x in rotation.screens), 2)

        # A payload update may remove a team's score before the next cycle.
        # Its orphaned intro must not linger, but the other pair stays intact.
        remaining = [x for x in mqtt if x.get("team_key") != "sporting_cp"
                     or x.get("kind") == "football_intro"]
        rotation.update_sources(http, remaining, 1001)
        ids = [x["id"] for x in rotation.screens]
        self.assertNotIn("football-intro-sporting_cp", ids)
        self.assertNotIn("football-sporting_cp", ids)
        self.assertEqual(
            ids.index("football-millwall"),
            ids.index("football-intro-millwall") + 1,
        )

    def test_football_intro_with_no_matching_score_is_omitted(self):
        rotation = ScreenRotation(rng=random.Random(1))
        bad = {"id": "football-intro-sporting_cp", "kind": "football_intro",
               "team_key": "sporting_cp", "duration_seconds": 6}
        other_score = {"id": "football-millwall", "kind": "football_score",
                       "team_key": "millwall", "duration_seconds": 20}
        rotation.update_sources([], [bad, other_score], 1000)
        self.assertEqual([x["id"] for x in rotation.screens], ["football-millwall"])

    def test_validates_topic_team_schema_shape_and_timestamps(self):
        valid = snapshot()
        cases = [
            ("led/football/sporting_cp", {**valid, "schema_version": True}),
            ("led/football/millwall", valid),
            ("led/football/unknown", valid),
            ("led/football/sporting_cp/child", valid),
            ("led/football/sporting_cp", {**valid, "status": "HALF_TIME"}),
            ("led/football/sporting_cp", {**valid, "published_at": "yesterday"}),
            ("led/football/sporting_cp", {**valid, "home_score": True}),
            ("led/football/sporting_cp", {**valid, "match_id": {"id": 1}}),
            ("led/football/sporting_cp", "not json"),
        ]
        for topic, payload in cases:
            with self.subTest(topic=topic, payload=payload):
                self.assertFalse(self.state.accept(topic, payload))
        self.assertEqual(self.state.screens(self.now), [])

    def test_out_of_order_and_duplicate_retained_replays_do_not_replace_snapshot(self):
        newer = snapshot(published="2026-10-26T20:01:00Z", team_name="New name")
        self.assertTrue(self.state.accept("led/football/sporting_cp", newer))
        self.assertFalse(self.state.accept("led/football/sporting_cp", newer))
        older = snapshot(published="2026-10-26T20:00:59Z", team_name="Old name")
        self.assertFalse(self.state.accept("led/football/sporting_cp", older))
        self.assertEqual(score_screen(self.state, self.now)["team_name"], "New name")

    def test_renders_all_lifecycle_states_and_optional_scores(self):
        for index, status in enumerate(("PRE", "IN", "POST", "BYE", "NOT_FOUND", "UNKNOWN", "UNAVAILABLE")):
            value = snapshot(published="2026-10-26T20:{:02d}:00Z".format(index), status=status)
            if status in ("IN", "POST"):
                value.update(home_score=2, away_score=1, clock="72'")
            self.assertTrue(self.state.accept("led/football/sporting_cp", value))
            screen = score_screen(self.state, self.now)
            rows = football_screen_lines(screen, self.now)
            self.assertTrue(rows[0])
            self.assertTrue(rows[1])
            self.assertTrue(rows[2])
            if status == "IN":
                self.assertIn("2 - 1", rows[2])
                self.assertIn("LIVE", rows[3])
            elif status == "POST":
                self.assertEqual(rows[3], "FULL TIME")
            elif status == "BYE":
                self.assertEqual(rows[2], "NO FIXTURE")
            elif status == "NOT_FOUND":
                self.assertEqual(rows[2], "NO FIXTURE FOUND")
            elif status == "UNKNOWN":
                self.assertEqual(rows[2], "STATUS UNKNOWN")

    def test_pregame_countdown_handles_timezone_and_never_goes_negative(self):
        self.assertEqual(kickoff_countdown("2026-10-26T23:00:00+02:00", self.now),
                         "KICKOFF IN 1H 00M")
        self.assertEqual(kickoff_countdown("2026-10-26T19:59:59Z", self.now),
                         "AWAITING LIVE UPDATE")
        self.assertEqual(kickoff_countdown("2026-10-26T20:00:45Z", self.now),
                         "KICKOFF IN 45S")
        self.assertEqual(kickoff_countdown("2026-10-26T22:00:00Z", None),
                         "CLOCK SYNCING")

    def test_pregame_shows_full_fixture_and_utc_kickoff_without_scores(self):
        value = snapshot(
            team_key="millwall", team_name="Millwall FC",
            opponent="Derby County", opponent_long_name="Derby County",
            display_fixture="Millwall vs Derby County",
            kickoff="2026-10-31T15:00:00+00:00",
            home_score=None, away_score=None,
        )
        self.assertTrue(self.state.accept("led/football/millwall", value))
        screen = score_screen(self.state, self.now)
        rows = football_screen_lines(screen, self.now)
        self.assertEqual(rows[:3], (
            "PRE", "Millwall vs Derby County",
            "KICKOFF: 31 October 2026, 15:00 UTC",
        ))
        self.assertEqual(screen["home_score"], None)
        self.assertEqual(screen["away_score"], None)
        self.assertEqual(
            kickoff_datetime_label("2026-10-31T17:00:00+02:00"),
            "31 October 2026, 15:00 UTC",
        )

    def test_stale_live_score_becomes_unavailable_without_scores(self):
        updated = "2026-10-26T20:00:00Z"
        self.assertTrue(self.state.accept("led/football/sporting_cp", snapshot(
            status="IN", home_score=1, away_score=0, source_updated_at=updated,
        )))
        unsynchronized = score_screen(self.state, None)
        self.assertEqual(unsynchronized["status"], "UNAVAILABLE")
        self.assertIsNone(unsynchronized["home_score"])
        fresh = score_screen(self.state, self.now + 600)
        self.assertEqual(fresh["status"], "IN")
        stale = score_screen(self.state, self.now + 601)
        self.assertEqual(stale["status"], "UNAVAILABLE")
        self.assertTrue(stale["stale"])
        self.assertIsNone(stale["home_score"])
        self.assertIn("STALE", football_screen_lines(stale, self.now + 601)[3])
        self.assertTrue(self.state.staleness_changed(self.now))
        self.assertFalse(self.state.staleness_changed(self.now + 600))
        self.assertTrue(self.state.staleness_changed(self.now + 601))

    def test_goal_marker_requires_same_live_fixture_numeric_scores_and_new_source_update(self):
        first = snapshot(status="IN", published="2026-10-26T20:00:00Z",
                         source_updated_at="2026-10-26T19:59:58Z", home_score=0, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", first))
        initial = score_screen(self.state, self.now)
        self.assertNotIn("goal_flash_active", initial)
        score = snapshot(status="IN", published="2026-10-26T20:00:05Z",
                         source_updated_at="2026-10-26T20:00:05Z", home_score=1, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", score))
        updated = score_screen(self.state, self.now + 5)
        self.assertTrue(updated["goal_flash_active"])
        self.assertEqual(updated["goal_side"], "home")
        self.assertTrue(self.state.staleness_changed(self.now + 5))
        self.assertFalse(self.state.staleness_changed(self.now + 7))
        self.assertTrue(self.state.staleness_changed(self.now + 14))
        self.assertNotIn("goal_flash_active", score_screen(self.state, self.now + 14))

    def test_fixture_rollover_null_initialization_and_score_correction_do_not_mark_goal(self):
        first = snapshot(status="IN", source_updated_at="2026-10-26T19:59:58Z",
                         home_score=None, away_score=None)
        self.assertTrue(self.state.accept("led/football/sporting_cp", first))
        initialized = snapshot(status="IN", published="2026-10-26T20:00:05Z",
                               source_updated_at="2026-10-26T20:00:05Z", home_score=1, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", initialized))
        self.assertNotIn("goal_flash_active", score_screen(self.state, self.now + 5))
        correction = snapshot(status="IN", published="2026-10-26T20:00:10Z",
                              source_updated_at="2026-10-26T20:00:10Z", home_score=0, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", correction))
        self.assertNotIn("goal_flash_active", score_screen(self.state, self.now + 10))
        rollover = snapshot(status="IN", published="2026-10-26T20:00:15Z",
                            source_updated_at="2026-10-26T20:00:15Z", match_id="event-456",
                            home_score=0, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", rollover))
        self.assertNotIn("goal_flash_active", score_screen(self.state, self.now + 15))

    def test_disabled_consumer_and_unexpected_topics_are_ignored(self):
        disabled = FootballScreenState(enabled=False)
        self.assertFalse(disabled.accept("led/football/sporting_cp", snapshot()))
        self.assertEqual(disabled.screens(self.now), [])
        self.assertFalse(self.state.accept("led/screens/recycling", snapshot()))

    def test_fallback_titles_use_circuitpython_compatible_team_names(self):
        value = snapshot(team_name=None)
        self.assertTrue(self.state.accept("led/football/sporting_cp", value))
        self.assertEqual(score_screen(self.state, self.now)["title"], "Sporting CP")


if __name__ == "__main__":
    unittest.main()
