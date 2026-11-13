from datetime import datetime, timezone
import json
import random
import shutil
import subprocess
import sys
import types
import unittest
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))
sys.path.insert(0, str(ROOT / "shared"))

from football_screens import (
    FootballPresentationQueue, FootballScreenState, football_presentation_position,
    football_screen_lines, kickoff_countdown, kickoff_local_label,
    football_due_in, football_slide_offset, football_roll_frame,
    football_countdown_x, FOOTBALL_TEAM_COLORS,
    football_team_name_span, football_presentation_expired,
)
from screen_client import ScreenRotation

sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))
from display import FixtureDisplay


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


class CapturingFootballFixture(FixtureDisplay):
    def __init__(self):
        self.pixels = []
        self.text = []

    def _pixel(self, x, y, color):
        if 0 <= x < 256 and 0 <= y < 32:
            self.pixels.append((x, y, color))

    def _text(self, value, x, y, color, scale=1, x_scale=1, y_scale=1,
              character_advance=None):
        self.text.append((value, x, y, color))


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
                         ["football_score", "football_score"])
        rebooted = FootballScreenState()
        self.assertTrue(rebooted.accept("led/football/sporting_cp", sporting))
        self.assertEqual(len(rebooted.screens(self.now)), 1)

    def test_live_match_joins_rotation_but_post_result_does_not(self):
        final = snapshot(
            "sporting_cp", status="POST", home_score=2, away_score=1,
            post_expires_at="2026-10-27T00:00:00Z",
        )
        self.state.accept("led/football/sporting_cp", final)
        live = snapshot("millwall", team_name="Millwall FC", status="IN",
                        source_updated_at="2026-10-26T20:00:00Z")
        self.state.accept("led/football/millwall", live)
        http = [{"id": "departures", "kind": "rail_combined", "duration_seconds": 30}]
        mqtt = [{"id": "recycling", "kind": "bin_collection", "duration_seconds": 20}]
        rotation = ScreenRotation(rng=random.Random(1))
        rotation.update_sources(
            http, mqtt + self.state.rotation_screens(self.now), 1000
        )
        kinds = [screen["kind"] for screen in rotation.screens]
        self.assertIn("rail_combined", kinds)
        self.assertIn("bin_collection", kinds)
        self.assertEqual(kinds.count("football_score"), 1)
        self.assertEqual(
            {screen["id"] for screen in rotation.screens if screen["kind"] == "football_score"},
            {"football-live-millwall"},
        )
        self.assertEqual(kinds.count("football_intro"), 0)
        self.assertTrue(self.state.has_live_match(self.now))

    def test_final_result_is_not_kept_in_team_state_or_rotation(self):
        final = snapshot(
            "millwall", status="POST", home_score=4, away_score=1,
            post_expires_at="2026-10-27T00:00:00Z",
        )
        self.assertTrue(self.state.accept("led/football/millwall", final))
        self.assertIsNone(self.state.screen_for_team("millwall", self.now))
        self.assertEqual(self.state.rotation_screens(self.now), [])

    def test_live_rotation_entry_expires_when_teamtracker_source_goes_stale(self):
        live = snapshot("millwall", team_name="Millwall FC", status="IN",
                        source_updated_at="2026-10-26T20:00:00Z")
        self.assertTrue(self.state.accept("led/football/millwall", live))
        self.state.staleness_changed(self.now)
        self.assertEqual(len(self.state.rotation_screens(self.now)), 1)
        stale_at = self.now + 601
        self.assertTrue(self.state.staleness_changed(stale_at))
        self.assertEqual(self.state.rotation_screens(stale_at), [])

    def test_active_live_match_stays_presented_but_post_card_ends(self):
        live = {"status": "IN", "duration_seconds": 20}
        post = {"status": "POST", "duration_seconds": 20}
        self.assertFalse(football_presentation_expired(live, 21))
        self.assertFalse(football_presentation_expired(live, 3600))
        self.assertFalse(football_presentation_expired(post, 19.9))
        self.assertTrue(football_presentation_expired(post, 20))

    def test_clock_refresh_updates_live_rotation_entry_without_restarting_phase(self):
        state = FootballScreenState()
        first = snapshot("millwall", team_name="Millwall FC", status="IN",
                         source_updated_at="2026-10-26T20:00:00Z", clock="30")
        self.assertTrue(state.accept("led/football/millwall", first))
        rotation = ScreenRotation(ticks_per_second=1000)
        rotation.update_sources([], state.rotation_screens(self.now), 1000)
        updated = snapshot("millwall", team_name="Millwall FC", status="IN",
                           published="2026-10-26T20:00:05Z",
                           source_updated_at="2026-10-26T20:00:05Z", clock="31")
        self.assertTrue(state.accept("led/football/millwall", updated))
        rotation.update_sources([], state.rotation_screens(self.now + 5), 4000)
        screen, phase = rotation.current(4000)
        self.assertEqual(screen["id"], "football-live-millwall")
        self.assertEqual(screen["clock"], "31")
        self.assertEqual(phase, 3)

    def test_live_match_added_mid_cycle_joins_after_existing_screens(self):
        rotation = ScreenRotation(ticks_per_second=1000)
        existing = [
            {"id": "one", "kind": "message", "duration_seconds": 10},
            {"id": "two", "kind": "message", "duration_seconds": 10},
        ]
        rotation.update_sources([], existing, 1000)
        rotation.current(4000)
        live = {"id": "football-live-millwall", "kind": "football_score",
                "status": "IN", "duration_seconds": 20}
        rotation.update_sources([], existing + [live], 4000)
        current, phase = rotation.current(4000)
        self.assertEqual(current["id"], "one")
        self.assertEqual(phase, 3)
        self.assertEqual([screen["id"] for screen in rotation.screens],
                         ["one", "two", "football-live-millwall"])

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

    def test_accepts_home_assistant_team_tracker_snapshots_for_all_followed_teams(self):
        for team_key in ("sporting_cp", "millwall", "portugal", "england"):
            with self.subTest(team_key=team_key):
                state = FootballScreenState()
                value = snapshot(
                    team_key=team_key,
                    status="IN",
                    team_score=0,
                    opponent_score=0,
                    home_score=0,
                    away_score=0,
                    source_updated_at="2026-10-26T20:00:00Z",
                )
                self.assertTrue(
                    state.accept("led/football/" + team_key, value)
                )
                self.assertTrue(state.has_live_match(self.now))

    def test_accepts_exact_home_assistant_team_tracker_timestamp_formats(self):
        # Captured HA representation: `date` is minute precision and
        # `last_update` is serialized with a space before its time.
        value = snapshot(
            team_key="millwall",
            published="2026-10-26T22:18:00.108470+00:00",
            team_name="Millwall", opponent="Derby County",
            opponent_long_name="Derby County",
            display_fixture="Millwall vs Derby County",
            kickoff="2026-10-31T15:00Z",
            source_updated_at="2026-10-26 22:17:27+00:00",
        )
        self.assertTrue(self.state.accept("led/football/millwall", value))
        screen = self.state.screen_for_team("millwall", self.now)
        self.assertIsNotNone(screen)
        self.assertEqual(
            football_screen_lines(screen, self.now),
            ("MILLWALL  VS DERBY COUNTY", "SAT 31 OCT 15:00"),
        )

    def test_fixture_separator_aligns_vs_for_club_names(self):
        fixtures = (
            ("millwall", "Millwall FC", "Millwall FCVS Derby County",
             "MILLWALL FC VS DERBY COUNTY"),
            ("sporting_cp", "Sporting CP", "Sporting CPVS Benfica",
             "SPORTING CP VS BENFICA"),
        )
        for team_key, team_name, display_fixture, expected in fixtures:
            with self.subTest(team_key=team_key):
                screen = {
                    "kind": "football_score", "status": "PRE", "team_key": team_key,
                    "team_name": team_name, "display_fixture": display_fixture,
                    "opponent": "Unused", "kickoff": "2026-10-31T15:00:00Z",
                }
                self.assertEqual(football_screen_lines(screen, self.now)[0], expected)

    def test_out_of_order_and_duplicate_retained_replays_do_not_replace_snapshot(self):
        newer = snapshot(published="2026-10-26T20:01:00Z", team_name="New name")
        self.assertTrue(self.state.accept("led/football/sporting_cp", newer))
        self.assertFalse(self.state.accept("led/football/sporting_cp", newer))
        older = snapshot(published="2026-10-26T20:00:59Z", team_name="Old name")
        self.assertFalse(self.state.accept("led/football/sporting_cp", older))
        self.assertEqual(score_screen(self.state, self.now)["team_name"], "New name")

    def test_renders_pregame_live_and_final_states_with_optional_scores(self):
        for index, status in enumerate(("PRE", "IN", "POST")):
            value = snapshot(published="2026-10-26T20:{:02d}:00Z".format(index), status=status)
            if status in ("IN", "POST"):
                value.update(home_score=2, away_score=1, clock="72'")
            if status == "POST":
                value["post_expires_at"] = "2026-10-26T20:30:00Z"
            accepted, screen = self.state.accept_for_presentation(
                "led/football/sporting_cp", value, self.now
            )
            self.assertTrue(accepted)
            self.assertIsNotNone(screen)
            rows = football_screen_lines(screen, self.now)
            self.assertTrue(rows[0])
            self.assertTrue(rows[1])
            if status == "PRE":
                self.assertEqual(len(rows), 2)
                self.assertNotIn("PRE", rows)
                self.assertNotIn("League", rows)
            else:
                self.assertEqual(len(rows), 4)
                self.assertTrue(rows[2])
            if status == "IN":
                self.assertIn("2 - 1", rows[2])
                self.assertIn("LIVE", rows[3])
            elif status == "POST":
                self.assertEqual(rows[3], "FULL TIME")

    def test_post_matches_live_layout_but_shows_full_time(self):
        from display import MatrixDisplay, TODAY_DATE_ANIMATION_FPS

        for status in ("IN", "POST"):
            with self.subTest(status=status):
                screen = {"kind": "football_score", "status": status}
                self.assertEqual(
                    MatrixDisplay._animation_class(None, screen, 0),
                    "football_team_color",
                )
                self.assertEqual(
                    MatrixDisplay.animation_sleep_seconds(None, screen, 0),
                    1.0 / TODAY_DATE_ANIMATION_FPS,
                )
        self.assertEqual(
            MatrixDisplay._animation_class(
                None, {"kind": "football_score", "status": "PRE"}, 0
            ),
            "football_entry",
        )

        def render(status):
            display = CapturingFootballFixture()
            display._draw_screen({
                "kind": "football_score", "status": status,
                "team_key": "sporting_cp", "team_name": "Sporting CP",
                "opponent_long_name": "Benfica",
                "home_team": "SPORTING CP", "away_team": "BENFICA",
                "home_score": 2, "away_score": 1, "clock": "92'",
                "ball_animation": True,
            }, phase=0)
            return display

        live, final = render("IN"), render("POST")
        self.assertEqual(min(pixel[0] for pixel in live.pixels), 2)
        self.assertEqual(min(pixel[0] for pixel in final.pixels), 2)
        live_fixture = next(row for row in live.text if row[0] == "SPORTING CP V BENFICA")
        final_fixture = next(row for row in final.text if row[0] == "SPORTING CP V BENFICA")
        self.assertEqual(live_fixture[1:3], final_fixture[1:3])
        self.assertEqual(
            next(row[1:3] for row in live.text if row[0] == "2-1"),
            next(row[1:3] for row in final.text if row[0] == "2-1"),
        )
        self.assertIn("92'", [row[0] for row in live.text])
        self.assertIn("FULL TIME", [row[0] for row in final.text])
        self.assertNotIn("92'", [row[0] for row in final.text])

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for simulator parity")
    def test_post_simulator_starts_settled_and_shows_final_score(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        start = html.index("    function drawFootball(screen, phase)")
        function = html[start:html.index("    function drawBinLorry", start)]
        harness = """
const FOOTBALL_END_X = 2, FOOTBALL_START_X = 256;
const calls = [];
function footballBallPosition(phase, animate) {
  return animate ? {x:256, infoVisible:false} : {x:2, infoVisible:true};
}
function drawFootballScene(screen, phase, offset, settled) {
  calls.push({status:screen.status, offset, settled});
}
function footballSlideSeconds() { return 3.2; }
""" + function + """
for (const status of ['PRE','IN','POST']) {
  drawFootball({kind:'football_score', status}, 0);
}
console.log(JSON.stringify(calls));
"""
        calls = json.loads(subprocess.check_output(["node", "-e", harness], text=True))
        self.assertEqual(calls[0], {"status": "PRE", "offset": 254, "settled": False})
        for status, call in zip(("IN", "POST"), calls[1:]):
            self.assertEqual(call, {"status": status, "offset": 0, "settled": True})

        # The simulator renders the names, final score and FULL TIME in the same
        # live-score branch, rather than falling back to four small text rows.
        scene = html[html.index("    function drawFootballScene("):
                     html.index("    function drawFootball(screen, phase)")]
        self.assertIn("screen.status === 'IN' || screen.status === 'POST'", scene)
        self.assertIn("? 'FULL TIME' : String(screen.clock || 'LIVE')", scene)
        self.assertIn("drawFootballLargeScore(score,", scene)
        self.assertIn("72 - clock.length * 5", scene)

    def test_non_fixture_statuses_are_retained_for_ordering_but_hidden(self):
        for index, status in enumerate(("BYE", "NOT_FOUND", "UNKNOWN", "UNAVAILABLE")):
            value = snapshot(published="2026-10-26T20:{:02d}:00Z".format(index), status=status)
            self.assertTrue(self.state.accept("led/football/sporting_cp", value))
            self.assertEqual(self.state.screens(self.now), [])
            self.assertIsNone(self.state.screen_for_team("sporting_cp", self.now))
            self.assertFalse(self.state.accept("led/football/sporting_cp", value))

    def test_pregame_with_old_source_update_stays_valid_and_missing_fixture_is_hidden(self):
        old_source = snapshot(
            "millwall", source_updated_at="2026-10-20T09:00:00Z",
            team_name="Millwall FC", opponent="Derby County",
            opponent_long_name="Derby County", display_fixture="Millwall vs Derby County",
        )
        self.assertTrue(self.state.accept("led/football/millwall", old_source))
        screen = self.state.screen_for_team("millwall", self.now)
        self.assertEqual(screen["status"], "PRE")
        self.assertEqual(football_screen_lines(screen, self.now), (
            "MILLWALL  VS DERBY COUNTY", "MON 26 OCT 22:00"
        ))
        no_fixture = snapshot(
            "millwall", published="2026-10-26T20:01:00Z",
            team_name=None, opponent=None, opponent_long_name=None,
            display_fixture=None, kickoff=None,
        )
        self.assertTrue(self.state.accept("led/football/millwall", no_fixture))
        self.assertIsNone(self.state.screen_for_team("millwall", self.now))

    def test_stale_live_update_is_hidden_and_next_fresh_fixture_recovers(self):
        stale_live = snapshot(
            team_key="millwall",
            status="IN", source_updated_at="2026-10-26T19:00:00Z",
            home_score=1, away_score=0,
        )
        self.assertTrue(self.state.accept("led/football/millwall", stale_live))
        self.assertIsNone(self.state.screen_for_team("millwall", self.now))
        next_fixture = snapshot(
            team_key="millwall", team_name="Millwall FC",
            opponent_long_name="Derby County", display_fixture="Millwall vs Derby County",
            published="2026-10-26T20:01:00Z", status="PRE",
        )
        self.assertTrue(self.state.accept("led/football/millwall", next_fixture))
        self.assertEqual(self.state.screen_for_team("millwall", self.now)["status"], "PRE")

    def test_pregame_countdown_handles_timezone_and_never_goes_negative(self):
        self.assertEqual(kickoff_countdown("2026-10-26T23:00:00+02:00", self.now),
                         "KICKOFF IN 1H 00M")
        self.assertEqual(kickoff_countdown("2026-10-26T19:59:59Z", self.now),
                         "AWAITING LIVE UPDATE")
        self.assertEqual(kickoff_countdown("2026-10-26T20:00:45Z", self.now),
                         "KICKOFF IN 45S")
        self.assertEqual(kickoff_countdown("2026-10-26T22:00:00Z", None),
                         "CLOCK SYNCING")

    def test_pregame_shows_only_fixture_and_uk_kickoff_without_scores(self):
        for scores in ((None, None), (1, 2)):
            with self.subTest(scores=scores):
                state = FootballScreenState()
                value = snapshot(
                    team_key="millwall", team_name="Millwall FC",
                    opponent="Derby County", opponent_long_name="Derby County",
                    display_fixture="Millwall vs Derby County",
                    kickoff="2026-10-31T15:00:00+00:00",
                    home_score=scores[0], away_score=scores[1],
                )
                self.assertTrue(state.accept("led/football/millwall", value))
                screen = score_screen(state, self.now)
                rows = football_screen_lines(screen, self.now)
                self.assertEqual(rows, ("MILLWALL  VS DERBY COUNTY", "SAT 31 OCT 15:00"))
                self.assertEqual(screen["home_score"], scores[0])
                self.assertEqual(screen["away_score"], scores[1])

    def test_kickoff_uses_london_bst_and_gmt_rules_and_invalid_falls_back(self):
        self.assertEqual(kickoff_local_label("2026-07-15T14:00:00Z"),
                         "WED 15 JUL 15:00")
        self.assertEqual(kickoff_local_label("2026-01-15T14:00:00Z"),
                         "THU 15 JAN 14:00")
        self.assertEqual(kickoff_local_label("2026-03-29T00:59:00Z"),
                         "SUN 29 MAR 00:59")
        self.assertEqual(kickoff_local_label("2026-03-29T01:00:00Z"),
                         "SUN 29 MAR 02:00")
        self.assertEqual(kickoff_local_label("2026-10-25T00:59:00Z"),
                         "SUN 25 OCT 01:59")
        self.assertEqual(kickoff_local_label("2026-10-25T01:00:00Z"),
                         "SUN 25 OCT 01:00")
        self.assertEqual(kickoff_local_label("invalid"), "TIME TBC")

    def test_pre_fixture_fallback_respects_home_away_order(self):
        screen = {
            "status": "PRE", "team_name": "Millwall FC",
            "opponent_long_name": "Derby County", "team_homeaway": "away",
            "kickoff": "2026-10-31T15:00:00Z",
        }
        self.assertEqual(football_screen_lines(screen, self.now)[0],
                         "DERBY COUNTY VS MILLWALL FC")

    def test_ball_slides_from_offscreen_to_left_and_stays_pinned(self):
        self.assertEqual(football_presentation_position(0), (256, False))
        self.assertFalse(football_presentation_position(1.6)[1])
        self.assertEqual(football_presentation_position(3.2), (2, True))
        self.assertEqual(football_presentation_position(20), (2, True))
        self.assertEqual(football_presentation_position(0, animate=False), (2, True))

    def test_adaptive_due_in_thresholds_and_unsynchronised_clock(self):
        base = epoch("2026-10-31T15:00:00Z")
        kickoff = "2026-10-31T15:00:00Z"
        self.assertEqual(football_due_in(kickoff, base - (2*86400 + 5*3600 + 14*60 + 9)),
                         "2 DAYS")
        self.assertEqual(football_due_in(kickoff, base - 172800), "2 DAYS")
        self.assertEqual(football_due_in(kickoff, base - 172799), "1 DAY")
        self.assertEqual(football_due_in(kickoff, base - 86401), "1 DAY")
        self.assertEqual(football_due_in(kickoff, base - 86400), "1 DAY")
        self.assertEqual(football_due_in(kickoff, base - 86399), "23H 59M 59S")
        self.assertEqual(football_due_in(kickoff, base - 3601), "01H 00M 01S")
        self.assertEqual(football_due_in(kickoff, base - 3600), "60M 00S")
        self.assertEqual(football_due_in(kickoff, base - 61), "01M 01S")
        self.assertEqual(football_due_in(kickoff, base - 60), "UNDER 1 MIN")
        self.assertEqual(football_due_in(kickoff, base - 1), "UNDER 1 MIN")
        self.assertEqual(football_due_in(kickoff, base), "DUE NOW")
        self.assertEqual(football_due_in(kickoff, base + 100), "DUE NOW")
        self.assertEqual(football_due_in("invalid", base), "TBC")
        self.assertEqual(football_due_in(kickoff, None), "TBC")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for simulator parity")
    def test_simulator_countdown_matches_firmware_across_day_transition(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        start = html.index("    function footballDueIn")
        function = html[start:html.index("    function drawFootballCompactText", start)]
        kickoff = "2026-10-31T15:00:00Z"
        base = epoch(kickoff)
        # Advance the same fixture's clock through both day boundaries and
        # kickoff, ensuring a days-only value becomes a clock with no days.
        remaining = [191649, 172800, 172799, 86401, 86400, 86399,
                     3601, 3600, 61, 60, 1, 0, -100]
        harness = function + "\nconst remaining = " + json.dumps(remaining) + ";\n" + """
console.log(JSON.stringify(remaining.map(seconds =>
  footballDueIn('2026-10-31T15:00:00Z',
    Date.parse('2026-10-31T15:00:00Z') - seconds * 1000))));
"""
        output = json.loads(subprocess.check_output(["node", "-e", harness], text=True))
        self.assertEqual(output, [football_due_in(kickoff, base - seconds)
                                  for seconds in remaining])

    def test_rolling_scene_positions_and_frames(self):
        self.assertEqual(football_slide_offset(0), (254, False))
        self.assertEqual(football_slide_offset(1.6), (127, False))
        self.assertEqual(football_slide_offset(3.2), (0, True))
        self.assertEqual(football_slide_offset(20), (0, True))
        self.assertEqual(football_roll_frame(0), 0)
        self.assertNotEqual(football_roll_frame(1.0), football_roll_frame(2.0))
        self.assertEqual(football_roll_frame(3.2), 0)

    def test_club_schedules_remain_adjacent_after_static_shuffle(self):
        rotation = ScreenRotation(rng=random.Random(3))
        screens = [
            {"id": "football-sporting_cp", "kind": "football_score", "team_key": "sporting_cp"},
            {"id": "fact", "kind": "random_fact", "display_group": "static_feeds"},
            {"id": "rail", "kind": "rail_combined"},
            {"id": "football-millwall", "kind": "football_score", "team_key": "millwall"},
            {"id": "today", "kind": "today", "display_group": "static_feeds"},
        ]
        plan = rotation._cycle_plan(screens)
        pairs = [(a["id"], b["id"]) for a, b in zip(plan, plan[1:])]
        self.assertIn(("football-sporting_cp", "football-millwall"), pairs)

    def test_countdown_right_aligns_even_when_day_count_grows(self):
        for value in ("1 DAY", "2 DAYS", "123 DAYS", "12345 DAYS",
                      "23H 59M 59S", "UNDER 1 MIN"):
            with self.subTest(value=value):
                x = football_countdown_x(value)
                self.assertEqual(x, 256 - len(value) * 6)
                self.assertLessEqual(x + len(value) * 6, 256)
        self.assertEqual(football_countdown_x("X" * 50), 0)

    def test_club_group_preserves_rail_bus_and_christmas_pairs(self):
        football_a = {"id": "football-a", "kind": "football_score"}
        football_b = {"id": "football-b", "kind": "football_score"}
        cases = [
            ([{"id": "steam-train", "kind": "steam_train_intro"},
              football_a, {"id": "rail", "kind": "rail_combined"},
              football_b], ("steam-train", "rail")),
            ([{"id": "sl7-combined-intro", "kind": "bus_intro", "stop_key": "combined"},
              football_a, {"id": "sl7", "kind": "bus_departures_combined"},
              football_b], ("sl7-combined-intro", "sl7")),
            ([{"id": "christmas-tracker-intro", "kind": "christmas_tracker_intro"},
              football_a, {"id": "christmas-tracker", "kind": "christmas_tracker"},
              football_b], ("christmas-tracker-intro", "christmas-tracker")),
            ([{"id": "weather-sun", "kind": "weather_sun"},
              football_a, {"id": "weather-today", "kind": "weather_today"},
              football_b], ("weather-sun", "weather-today")),
        ]
        for normal, protected in cases:
            with self.subTest(protected=protected):
                rotation = ScreenRotation(rng=random.Random(17))
                plan = rotation._cycle_plan(normal)
                pairs = list(zip(
                    [item["id"] for item in plan[:-1]],
                    [item["id"] for item in plan[1:]],
                ))
                self.assertIn(protected, pairs)
                self.assertIn(("football-a", "football-b"), pairs)
                self.assertEqual(len(plan), len(normal))

    @unittest.skipUnless(shutil.which("node"), "Node.js needed for simulator rotation parity")
    def test_browser_simulator_preserves_interleaved_train_and_bus_pairs(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        rotation_js = html[html.index("    const staticScreen = screen =>"):
                           html.index("    function cronFieldMatches(", html.index("    const staticScreen = screen =>"))]
        harness = "let screens = [];\n" + rotation_js + """
const footballA = {id:'football-a',kind:'football_score'};
const footballB = {id:'football-b',kind:'football_score'};
const cases = [
  [{id:'steam-train',kind:'steam_train_intro'}, footballA,
   {id:'rail',kind:'rail_combined'}, footballB],
  [{id:'sl7-combined-intro',kind:'bus_intro',stop_key:'combined'}, footballA,
   {id:'sl7',kind:'bus_departures_combined'}, footballB],
  [{id:'christmas-tracker-intro',kind:'christmas_tracker_intro'}, footballA,
   {id:'christmas-tracker',kind:'christmas_tracker'}, footballB],
  [{id:'weather-sun',kind:'weather_sun'}, footballA,
   {id:'weather-today',kind:'weather_today'}, footballB]
];
const output = cases.map(items => { screens = items; return makeCyclePlan().map(x => x.id); });
process.stdout.write(JSON.stringify(output));
"""
        result = subprocess.run(["node", "-e", harness], check=True, capture_output=True, text=True)
        sequences = json.loads(result.stdout)
        for sequence, pair in zip(sequences, [
            ("steam-train", "rail"), ("sl7-combined-intro", "sl7"),
            ("christmas-tracker-intro", "christmas-tracker"),
            ("weather-sun", "weather-today")
        ]):
            neighbors = list(zip(sequence, sequence[1:]))
            self.assertIn(pair, neighbors)
            self.assertIn(("football-a", "football-b"), neighbors)
            self.assertEqual(len(sequence), 4)

    def test_team_name_uses_one_team_color_and_fixture_rest_is_white(self):
        self.assertEqual(FOOTBALL_TEAM_COLORS, {
            "sporting_cp": (0, 255, 0), "england": (255, 255, 255),
            "millwall": (0, 0, 255), "portugal": (255, 0, 0),
        })
        names = {
            "sporting_cp": "SPORTING CP",
            "millwall": "MILLWALL FC",
            "england": "ENGLAND",
            "portugal": "PORTUGAL",
        }
        for team, colour in FOOTBALL_TEAM_COLORS.items():
            with self.subTest(team=team):
                screen = {
                    "kind": "football_score", "status": "PRE",
                    "team_key": team, "team_name": names[team],
                }
                span = football_team_name_span(screen, names[team] + " VS OPPONENT")
                self.assertEqual(span, (0, names[team], colour))

    def test_simulator_uses_solid_team_colors_and_white_fixture_text(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        self.assertIn("const FOOTBALL_TEAM_COLORS = {", html)
        self.assertIn("function drawFootballTeamLine(screen, value, x, y, color, phase = 0)", html)
        self.assertIn("FOOTBALL_TEAM_COLORS[key]", html)
        self.assertIn("sporting_cp: 'SPORTING CP'", html)
        self.assertIn("millwall: 'MILLWALL FC'", html)
        self.assertIn("'#ffff00'", html)
        self.assertNotIn("FOOTBALL_TEAM_LETTER_COLORS", html)

    def test_simulator_keeps_ball_pinned_and_pregame_text_to_its_right(self):
        display = CapturingFootballFixture()
        screen = {
            "kind": "football_score", "status": "PRE", "team_key": "millwall",
            "team_name": "Millwall FC", "opponent_long_name": "Derby County",
            "display_fixture": "Millwall vs Derby County",
            "kickoff": "2026-10-31T15:00:00Z", "competition": "League",
            "home_score": None, "away_score": None, "ball_animation": True,
        }
        display._draw_screen(screen, phase=0)
        self.assertEqual(display.text, [])
        self.assertEqual(display.pixels, [])
        display._draw_screen(screen, phase=3.7)
        self.assertTrue(display.pixels)
        self.assertTrue(all(2 <= x < 18 for x, _, _ in display.pixels))
        self.assertEqual([row[0] for row in display.text], [
            "MILLWALL  VS DERBY COUNTY", "SAT 31 OCT 15:00",
        ])
        self.assertTrue(all(x >= 22 for _, x, _, _ in display.text))
        self.assertEqual([row[2] for row in display.text], [5, 18])

    def test_matrix_display_aligns_vs_for_both_clubs(self):
        cases = (
            ("millwall", "Millwall FC", "Millwall FCvs Derby County",
             "MILLWALL FC VS DERBY COUNTY"),
            ("sporting_cp", "Sporting CP", "Sporting CPvs Benfica",
             "SPORTING CP VS BENFICA"),
        )
        for team_key, team_name, display_fixture, expected in cases:
            with self.subTest(team_key=team_key):
                display = CapturingFootballFixture()
                screen = {
                    "kind": "football_score", "status": "PRE", "team_key": team_key,
                    "team_name": team_name, "display_fixture": display_fixture,
                    "kickoff": "2026-10-31T15:00:00Z", "ball_animation": False,
                }
                display._draw_screen(screen, phase=3.7)
                self.assertEqual(display.text[0][0], expected)

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for simulator parity")
    def test_browser_simulator_football_presentation_matches_firmware_contract(self):
        html = (Path(__file__).resolve().parents[1] / "simulator/index.html").read_text()
        constants = html[html.index("    const FOOTBALL_BALL_ROWS"):
                         html.index("    const CLOCK_X", html.index("    const FOOTBALL_BALL_ROWS"))]
        functions = html[html.index("    function footballKickoffLabel"):
                         html.index("    function drawBinLorry", html.index("    function footballKickoffLabel"))]
        harness = constants + """
const FONT_PIXEL_SCALE = 4;
const FONT_FIRST_CODEPOINT = 32;
const FONT_5X7 = Array.from({length: 95}, () => [0, 0, 0, 0, 0, 0, 0]);
const context = {fillStyle: '', fillRect() {}};
const drawn = [];
function drawLedText(value, x, y) { drawn.push([value, x / FONT_PIXEL_SCALE, y / FONT_PIXEL_SCALE]); }
""" + functions + """
// Keep this layout-contract test focused on coordinates. Solid team colors
// are checked separately by test_simulator_uses_solid_team_colors_and_white_fixture_text.
function drawFootballTeamLine(screen, value, x, y) { drawLedText(value, x, y); }
function drawFootballLargeTeamLine(screen, value, x, y) {
  drawLedText(value, x * FONT_PIXEL_SCALE, y * FONT_PIXEL_SCALE);
}
function drawFootballPregameText(value, x, y) { drawLedText(value, x * FONT_PIXEL_SCALE, y * FONT_PIXEL_SCALE); }
const sample = {status:'PRE', team_key:'millwall', team_name:'Millwall FC',
  opponent_long_name:'Derby County', display_fixture:'Millwall vs Derby County',
  kickoff:'2026-10-31T15:00:00Z', competition:'League', ball_animation:true};
const results = [
  footballLines(sample), footballKickoffLabel('bad'),
  footballKickoffLabel('2026-03-29T01:30:00Z'),
  footballKickoffLabel('2026-10-25T01:30:00Z'),
  footballBallPosition(0), footballBallPosition(3.2), footballBallPosition(20),
  footballDueIn(sample.kickoff, Date.parse('2026-10-28T09:45:51Z'))
];
drawFootball(sample, 0); results.push(drawn.slice());
drawFootball(sample, 3.7); results.push(drawn.slice());
results.push(footballLines({...sample, display_fixture:'Millwall FCvs Derby County'}));
results.push(footballLines({...sample, team_key:'sporting_cp', team_name:'Sporting CP',
  display_fixture:'Sporting CPvs Benfica'}));
process.stdout.write(JSON.stringify(results));
"""
        result = subprocess.run(["node", "-e", harness], check=True, capture_output=True, text=True)
        output = json.loads(result.stdout)
        self.assertEqual(output[0], ["MILLWALL  VS DERBY COUNTY", "SAT 31 OCT 15:00"])
        self.assertEqual(output[1], "TIME TBC")
        self.assertEqual(output[2], "SUN 29 MAR 02:30")
        self.assertEqual(output[3], "SUN 25 OCT 01:30")
        self.assertEqual(output[4], {"x": 256, "infoVisible": False})
        self.assertEqual(output[5], {"x": 2, "infoVisible": True})
        self.assertEqual(output[6], {"x": 2, "infoVisible": True})
        self.assertEqual(output[7], "3 DAYS")
        # Both rows are laid out while entering; their x is initially off
        # screen and then reaches the original left-column coordinates.
        self.assertEqual(output[8], [
            ["MILLWALL  VS DERBY COUNTY", 276, 5],
            ["SAT 31 OCT 15:00", 276, 22],
        ])
        self.assertEqual(output[9][:3], [
            ["MILLWALL  VS DERBY COUNTY", 276, 5],
            ["SAT 31 OCT 15:00", 276, 22],
            ["MILLWALL  VS DERBY COUNTY", 22, 5],
        ])
        self.assertIn(["KICK-OFF", 208, 18], output[9])
        self.assertEqual(output[10][0], "MILLWALL FC VS DERBY COUNTY")
        self.assertEqual(output[11][0], "SPORTING CP VS BENFICA")
        self.assertIn("screen.kind === 'football_score'", html)
        self.assertIn("document.getElementById('football-preview')", html)

    def test_prompt_presentation_queue_coalesces_redundant_team_updates(self):
        queue = FootballPresentationQueue()
        self.assertTrue(queue.schedule("millwall"))
        self.assertTrue(queue.schedule("millwall"))
        self.assertTrue(queue.schedule("sporting_cp"))
        self.assertFalse(queue.schedule("unknown/team"))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.pop(), "millwall")
        self.assertTrue(queue.schedule("millwall"))
        self.assertEqual(queue.pop(), "sporting_cp")
        self.assertEqual(queue.pop(), "millwall")
        self.assertIsNone(queue.pop())

    def test_unchanged_snapshot_and_clock_refresh_do_not_request_new_presentation(self):
        queue = FootballPresentationQueue()
        first = snapshot("millwall", team_name="Millwall FC", status="IN",
                         home_score=0, away_score=0, fixture_key="millwall|2026-10-26")
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", first, epoch(first["published_at"])
        ))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.pop(), "millwall")
        self.assertFalse(queue.accept_snapshot(
            self.state, "led/football/millwall", first, epoch(first["published_at"])
        ))
        invalid = dict(first, status="INVALID")
        self.assertFalse(queue.accept_snapshot(
            self.state, "led/football/millwall", invalid, epoch(invalid["published_at"])
        ))
        self.assertEqual(len(queue), 0)
        newer = snapshot("millwall", published="2026-10-26T20:01:00Z",
                         team_name="Millwall FC", status="IN", home_score=0,
                         away_score=0, fixture_key="millwall|2026-10-26")
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", newer, epoch(newer["published_at"])
        ))
        self.assertEqual(len(queue), 0)
        same_fixture_update = snapshot(
            "millwall", published="2026-10-26T20:02:00Z", team_name="Millwall FC",
            status="IN", home_score=0, away_score=0, clock="31",
            fixture_key="millwall|2026-10-26"
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", same_fixture_update,
            epoch(same_fixture_update["published_at"])
        ))
        self.assertEqual(len(queue), 0)
        scored = snapshot("millwall", published="2026-10-26T20:02:10Z",
                          team_name="Millwall FC", status="IN", home_score=1,
                          away_score=0, fixture_key="millwall|2026-10-26")
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", scored, epoch(scored["published_at"]),
            presenting_screen={"team_key": "millwall",
                               "fixture_key": "millwall|2026-10-26",
                               "id": "football-event-7"},
        ))
        self.assertEqual(len(queue), 0)
        next_fixture = snapshot(
            "millwall", published="2026-10-26T20:03:00Z", team_name="Millwall FC",
            match_id="event-456", kickoff="2026-11-07T15:00:00Z",
            fixture_key="millwall|2026-11-07", status="IN", home_score=0,
            away_score=0,
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", next_fixture,
            epoch(next_fixture["published_at"])
        ))
        self.assertEqual(queue.pop(), "millwall")

    def test_post_from_another_or_older_fixture_cannot_clear_live_match(self):
        state = FootballScreenState()
        live = snapshot(
            "millwall", status="IN", match_id="current-event",
            fixture_key="millwall|2026-10-26|current-opponent",
            source_updated_at="2026-10-26T20:10:00Z",
        )
        self.assertTrue(state.accept("led/football/millwall", live))
        old_post = snapshot(
            "millwall", status="POST", match_id="previous-event",
            fixture_key="millwall|2026-10-19|previous-opponent",
            published="2026-10-26T20:11:00Z",
            source_updated_at="2026-10-19T22:00:00Z",
            post_expires_at="2026-10-27T00:00:00Z",
            home_score=2, away_score=1,
        )
        queue = FootballPresentationQueue()
        accepted = queue.accept_snapshot(
            state, "led/football/millwall", old_post,
            epoch(old_post["published_at"]),
            presenting_screen={"team_key": "millwall", "fixture_key": live["fixture_key"]},
        )
        self.assertFalse(accepted)
        self.assertEqual(len(queue), 0)
        current = score_screen(state, self.now)
        self.assertEqual(current["status"], "IN")
        self.assertEqual(current["match_id"], "current-event")

    def test_matching_fresh_post_replaces_active_match_with_final_card(self):
        state = FootballScreenState()
        live = snapshot(
            "millwall", status="IN", match_id="current-event",
            fixture_key="millwall|2026-10-26|current-opponent",
            source_updated_at="2026-10-26T20:10:00Z",
        )
        self.assertTrue(state.accept("led/football/millwall", live))
        final = snapshot(
            "millwall", status="POST", match_id="current-event",
            fixture_key=live["fixture_key"],
            published="2026-10-26T21:00:00Z",
            source_updated_at="2026-10-26T20:59:00Z",
            post_expires_at="2026-10-27T00:00:00Z",
            home_score=2, away_score=1,
        )
        queue = FootballPresentationQueue()
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", final,
            epoch(final["published_at"]),
            presenting_screen={"team_key": "millwall", "fixture_key": live["fixture_key"]},
        ))
        self.assertEqual(queue.last_update, "post_event")
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.pop(self.now)["status"], "POST")
        self.assertIsNone(state.screen_for_team("millwall", self.now))

    def test_republished_post_is_a_new_one_shot_and_is_not_cached(self):
        state = FootballScreenState()
        queue = FootballPresentationQueue()
        first = snapshot(
            "millwall", status="POST", home_score=4, away_score=1,
            post_expires_at="2026-10-27T00:00:00Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", first, self.now
        ))
        self.assertEqual(queue.pop(self.now)["status"], "POST")
        refresh = dict(first, published_at="2026-10-26T20:05:00Z")
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", refresh,
            epoch(refresh["published_at"]),
        ))
        self.assertEqual(queue.last_update, "post_event")
        self.assertEqual(queue.pop(self.now)["status"], "POST")
        self.assertIsNone(state.screen_for_team("millwall", self.now))
        self.assertEqual(state.rotation_screens(self.now), [])

    def test_post_queue_deduplicates_by_match_session_across_provider_ids(self):
        state = FootballScreenState()
        queue = FootballPresentationQueue()
        first = snapshot(
            "millwall", status="POST", match_id="espn-final-1",
            fixture_key="millwall|2026-10-26|derby-county-fc",
            kickoff="2026-10-26T19:00:00Z", opponent="Derby County FC",
            opponent_long_name="Derby County FC", home_score=2, away_score=1,
            post_expires_at="2026-10-27T00:00:00Z",
        )
        second = snapshot(
            "millwall", source="nrwindsor", provider="goalapi", status="POST",
            match_id="goalapi-final-1", fixture_key="millwall|2026-10-26|derby-county",
            kickoff="2026-10-26T19:00:00Z", opponent="Derby County",
            opponent_long_name="Derby County", home_score=2, away_score=1,
            published="2026-10-26T20:05:00Z", source_updated_at="2026-10-26T20:04:00Z",
            post_expires_at="2026-10-27T00:00:00Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", first, epoch(first["published_at"]),
        ))
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", second, epoch(second["published_at"]),
        ))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.pop(self.now)["match_id"], "goalapi-final-1")

    def test_new_match_removes_queued_post_for_finished_session(self):
        state = FootballScreenState()
        queue = FootballPresentationQueue()
        final = snapshot(
            "millwall", status="POST", match_id="old-final",
            fixture_key="millwall|2026-10-26|derby", kickoff="2026-10-26T15:00:00Z",
            opponent="Derby County", opponent_long_name="Derby County",
            home_score=1, away_score=0, post_expires_at="2026-10-27T00:00:00Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", final, epoch(final["published_at"]),
        ))
        next_match = snapshot(
            "millwall", status="IN", match_id="new-match",
            fixture_key="millwall|2026-10-26|leeds", kickoff="2026-10-26T19:00:00Z",
            opponent="Leeds United", opponent_long_name="Leeds United",
            home_score=0, away_score=0, published="2026-10-26T19:01:00Z",
            source_updated_at="2026-10-26T19:01:00Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", next_match, epoch(next_match["published_at"]),
        ))
        self.assertEqual(queue.pop(self.now), "millwall")
        self.assertIsNone(queue.pop(self.now))

    def test_active_match_rejects_terminal_updates_without_cached_live_state(self):
        state = FootballScreenState()
        live = snapshot(
            "millwall", status="IN", match_id="current-event",
            fixture_key="millwall|2026-10-26|current-opponent",
            source_updated_at="2026-10-26T20:10:00Z",
        )
        self.assertTrue(state.accept("led/football/millwall", live))
        active = state.screen_for_team("millwall", self.now)
        state._teams.clear()  # Simulate a board state-cache reset during the match.
        queue = FootballPresentationQueue()

        unavailable = snapshot(
            "millwall", status="NOT_FOUND", match_id=None,
            fixture_key=None, source_updated_at=None,
            published="2026-10-26T20:11:00Z",
        )
        self.assertFalse(queue.accept_snapshot(
            state, "led/football/millwall", unavailable, self.now,
            presenting_screen=active,
        ))
        self.assertEqual(queue.last_update, "rejected_active_match_transition")
        self.assertEqual(len(queue), 0)

        unrelated_post = snapshot(
            "millwall", status="POST", match_id="previous-event",
            fixture_key="millwall|2026-10-19|previous-opponent",
            kickoff="2026-10-19T22:00:00Z",
            published="2026-10-26T20:12:00Z",
            source_updated_at="2026-10-26T20:11:00Z",
            post_expires_at="2026-10-27T00:00:00Z",
            home_score=2, away_score=1,
        )
        self.assertFalse(queue.accept_snapshot(
            state, "led/football/millwall", unrelated_post,
            epoch(unrelated_post["published_at"]), presenting_screen=active,
        ))
        self.assertEqual(len(queue), 0)

        final = snapshot(
            "millwall", status="POST", match_id="current-event",
            fixture_key=live["fixture_key"],
            published="2026-10-26T21:00:00Z",
            source_updated_at="2026-10-26T20:59:00Z",
            post_expires_at="2026-10-27T00:00:00Z",
            home_score=2, away_score=1,
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", final,
            epoch(final["published_at"]), presenting_screen=active,
        ))
        self.assertEqual(queue.pop(self.now)["status"], "POST")
        self.assertIsNone(state.screen_for_team("millwall", self.now))

    def test_goal_api_score_survives_lagging_teamtracker_and_merges_its_clock(self):
        key = "millwall"
        fixture_key = "millwall|2026-10-26"
        initial = snapshot(
            key, status="IN", fixture_key=fixture_key,
            source_updated_at="2026-10-26T20:00:00Z", home_score=0,
            away_score=0, clock="30",
        )
        self.assertTrue(self.state.accept("led/football/" + key, initial))
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-99",
            provider_match_id="api-99", event_id="event-goal-1",
            event_type="goal.scored", fixture_key=fixture_key,
            published="2026-10-26T20:00:05Z",
            source_updated_at="2026-10-26T20:00:05Z", status="IN",
            home_score=1, away_score=0, clock=None,
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        screen = score_screen(self.state, epoch("2026-10-26T20:00:06Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertEqual(screen["clock"], "30")
        self.assertTrue(screen["goal_flash_active"])

        behind = snapshot(
            key, fixture_key=fixture_key, match_id="tracker-99",
            published="2026-10-26T20:00:10Z",
            source_updated_at="2026-10-26T20:00:10Z", status="IN",
            home_score=0, away_score=0, clock="31",
        )
        self.assertTrue(self.state.accept("led/football/" + key, behind))
        screen = score_screen(self.state, epoch("2026-10-26T20:00:11Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertEqual(screen["clock"], "31")

        confirmed = snapshot(
            key, fixture_key=fixture_key, match_id="tracker-99",
            published="2026-10-26T20:00:20Z",
            source_updated_at="2026-10-26T20:00:20Z", status="IN",
            home_score=1, away_score=0, clock="32",
        )
        self.assertTrue(self.state.accept("led/football/" + key, confirmed))
        screen = score_screen(self.state, epoch("2026-10-26T20:00:21Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertEqual(screen["clock"], "32")

        retry = dict(goal, published_at="2026-10-26T20:00:22Z")
        self.assertFalse(self.state.accept("led/football/" + key, retry))
        correction = dict(
            goal, event_id="score-correction-1", event_type="score.changed",
            published_at="2026-10-26T20:00:30Z",
            source_updated_at="2026-10-26T20:00:30Z", home_score=0, away_score=0,
        )
        self.assertTrue(self.state.accept("led/football/" + key, correction))
        screen = score_screen(self.state, epoch("2026-10-26T20:00:31Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (0, 0))
        self.assertNotIn("goal_flash_active", screen)

    def test_live_score_reconciles_across_provider_ids_and_ignores_lag_past_120_seconds(self):
        key = "millwall"
        tracker = snapshot(
            key, match_id="espn-event-44", fixture_key="millwall|2026-10-26|derby-county-fc",
            opponent="Derby County FC", opponent_long_name="Derby County FC",
            status="IN", home_score=0, away_score=0, clock="30",
        )
        self.assertTrue(self.state.accept("led/football/" + key, tracker))
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="goalapi-991",
            provider_match_id="goalapi-991", fixture_key="millwall|2026-10-26|derby-county",
            opponent="Derby County", opponent_long_name="Derby County",
            event_id="goal-event-991", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:31:00Z",
            source_updated_at="2026-10-26T20:31:00Z", clock=None,
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        for minute, timestamp in (
                (31, "2026-10-26T20:31:10Z"),
                (33, "2026-10-26T20:33:00Z"),
                (33, "2026-10-26T20:33:06Z")):
            tracker_refresh = dict(
                tracker,
                published_at=timestamp,
                source_updated_at=timestamp,
                home_score=0, away_score=0, clock=str(minute),
            )
            self.assertTrue(self.state.accept("led/football/" + key, tracker_refresh))
            self.assertEqual(self.state.last_decision, "teamtracker_rollback_ignored")
            now = epoch(timestamp) + 1
            screen = score_screen(self.state, now)
            self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
            self.assertEqual(screen["clock"], str(minute))

    def test_mismatched_provider_ids_clock_refresh_keeps_active_phase_and_score_flash(self):
        state = FootballScreenState()
        queue = FootballPresentationQueue()
        goal = snapshot(
            "millwall", source="nrwindsor", provider="goalapi", match_id="api-44",
            fixture_key="millwall|2026-10-26|derby-county", opponent="Derby County",
            opponent_long_name="Derby County", event_id="goal-44",
            event_type="goal.scored", status="IN", home_score=1, away_score=0,
            previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:00:05Z", source_updated_at="2026-10-26T20:00:05Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", goal, epoch(goal["published_at"]),
        ))
        self.assertEqual(queue.pop(self.now), "millwall")
        goal_until = state._teams["millwall"]["_goal_until"]
        active = state.screen_for_team("millwall", self.now + 1)
        tracker = snapshot(
            "millwall", match_id="espn-44", fixture_key="millwall|2026-10-26|derby-county-fc",
            opponent="Derby County FC", opponent_long_name="Derby County FC",
            status="IN", home_score=1, away_score=0, clock="31",
            published="2026-10-26T20:00:10Z", source_updated_at="2026-10-26T20:00:10Z",
        )
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/millwall", tracker, epoch(tracker["published_at"]),
            presenting_screen=active,
        ))
        self.assertEqual(queue.last_update, "active_data_refresh")
        self.assertEqual(len(queue), 0)
        self.assertEqual(state._teams["millwall"]["_goal_until"], goal_until)
        screen = state.screen_for_team("millwall", epoch("2026-10-26T20:00:11Z"))
        self.assertEqual(screen["clock"], "31")
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertTrue(screen["goal_flash_active"])

    def test_newer_teamtracker_goal_advances_after_goalapi_score_without_120s_expiry(self):
        key = "millwall"
        tracker = snapshot(
            key, match_id="espn-1", fixture_key="millwall|2026-10-26|derby-county-fc",
            opponent="Derby County FC", status="IN", home_score=0, away_score=0,
            clock="30",
        )
        self.assertTrue(self.state.accept("led/football/" + key, tracker))
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            fixture_key="millwall|2026-10-26|derby-county", opponent="Derby County",
            event_id="goal-1", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:00:05Z", source_updated_at="2026-10-26T20:00:05Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        later = dict(tracker, published_at="2026-10-26T22:03:00Z",
                     source_updated_at="2026-10-26T22:03:00Z",
                     home_score=2, away_score=0, clock="63")
        self.assertTrue(self.state.accept("led/football/" + key, later))
        repeated_old = dict(tracker, published_at="2026-10-26T22:04:00Z",
                            source_updated_at="2026-10-26T22:04:00Z",
                            home_score=1, away_score=0, clock="64")
        self.assertTrue(self.state.accept("led/football/" + key, repeated_old))
        screen = score_screen(self.state, epoch("2026-10-26T22:04:01Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (2, 0))
        self.assertEqual(screen["score_source"], "teamtracker")

    def test_goalapi_goal_increases_score_even_if_teamtracker_clock_was_published_later(self):
        key = "millwall"
        tracker = snapshot(
            key, status="IN", match_id="espn-1", fixture_key="millwall|2026-10-26|derby-county-fc",
            opponent="Derby County FC", opponent_long_name="Derby County FC",
            home_score=0, away_score=0, clock="31",
            published="2026-10-26T20:31:10Z", source_updated_at="2026-10-26T20:31:10Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, tracker))
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            fixture_key="millwall|2026-10-26|derby-county", opponent="Derby County",
            opponent_long_name="Derby County", event_id="goal-31",
            event_type="goal.scored", status="IN", home_score=1, away_score=0,
            previous_home_score=0, previous_away_score=0, clock=None,
            source_updated_at="2026-10-26T20:31:05Z",
            published="2026-10-26T20:31:11Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        screen = score_screen(self.state, epoch("2026-10-26T20:31:12Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertEqual(screen["clock"], "31")

    def test_ordered_goalapi_correction_survives_a_late_teamtracker_snapshot(self):
        key = "millwall"
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            event_id="goal-1", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        correction = dict(
            goal, event_id="correction-1", event_type="score.changed",
            published_at="2026-10-26T20:01:00Z", source_updated_at="2026-10-26T20:01:00Z",
            home_score=0, away_score=0,
        )
        self.assertTrue(self.state.accept("led/football/" + key, correction))
        self.assertEqual(self.state.last_decision, "goalapi_score_correction")
        stale_tracker = snapshot(
            key, match_id="espn-1", status="IN", home_score=1, away_score=0,
            published="2026-10-26T20:02:00Z", source_updated_at="2026-10-26T20:02:00Z",
            clock="32",
        )
        self.assertTrue(self.state.accept("led/football/" + key, stale_tracker))
        screen = score_screen(self.state, epoch("2026-10-26T20:02:01Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (0, 0))

    def test_ordered_goalapi_correction_can_override_confirmed_tracker_score(self):
        key = "millwall"
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            event_id="goal-1", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:00:05Z", source_updated_at="2026-10-26T20:00:05Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        confirmation = snapshot(
            key, match_id="espn-1", fixture_key="millwall|2026-10-26|benfica-fc",
            status="IN", home_score=1, away_score=0, clock="32",
            published="2026-10-26T20:00:10Z", source_updated_at="2026-10-26T20:00:10Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, confirmation))
        correction = dict(
            goal, event_id="correction-1", event_type="score.changed",
            home_score=0, away_score=0, published_at="2026-10-26T20:00:11Z",
            source_updated_at="2026-10-26T20:00:08Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, correction))
        self.assertEqual(self.state.last_decision, "goalapi_score_correction")
        stale_tracker = dict(
            confirmation, published_at="2026-10-26T20:00:12Z",
            source_updated_at="2026-10-26T20:00:12Z", clock="33",
        )
        self.assertTrue(self.state.accept("led/football/" + key, stale_tracker))
        screen = score_screen(self.state, epoch("2026-10-26T20:00:13Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (0, 0))

    def test_out_of_order_goalapi_score_event_cannot_undo_newer_event(self):
        key = "millwall"
        first = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            event_id="goal-1", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:00:05Z", source_updated_at="2026-10-26T20:00:05Z",
        )
        second = dict(
            first, event_id="goal-2", previous_home_score=1, home_score=2,
            published_at="2026-10-26T20:00:10Z", source_updated_at="2026-10-26T20:00:10Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, first))
        self.assertTrue(self.state.accept("led/football/" + key, second))
        late_correction = dict(
            first, event_id="late-correction", event_type="score.changed",
            home_score=1, away_score=0,
            published_at="2026-10-26T20:00:11Z", source_updated_at="2026-10-26T20:00:08Z",
        )
        self.assertFalse(self.state.accept("led/football/" + key, late_correction))
        self.assertEqual(self.state.last_decision, "out_of_order_goalapi_event")
        screen = score_screen(self.state, epoch("2026-10-26T20:00:12Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (2, 0))

    def test_same_day_second_match_rejects_late_previous_fixture_and_accepts_new_post(self):
        key = "millwall"
        state = FootballScreenState()
        first = snapshot(
            key, status="IN", match_id="old-espn", fixture_key="millwall|2026-10-26|derby",
            kickoff="2026-10-26T15:00:00Z", opponent="Derby County",
            home_score=1, away_score=0,
        )
        self.assertTrue(state.accept("led/football/" + key, first))
        second = snapshot(
            key, status="IN", match_id="new-api", fixture_key="millwall|2026-10-26|leeds",
            kickoff="2026-10-26T19:00:00Z", opponent="Leeds United",
            opponent_long_name="Leeds United",
            published="2026-10-26T19:01:00Z", source_updated_at="2026-10-26T19:01:00Z",
            home_score=0, away_score=0,
        )
        self.assertTrue(state.accept("led/football/" + key, second))
        late = dict(first, published_at="2026-10-26T19:02:00Z",
                    source_updated_at="2026-10-26T14:30:00Z", home_score=4)
        self.assertFalse(state.accept("led/football/" + key, late))
        final = snapshot(
            key, source="nrwindsor", provider="goalapi", status="POST",
            match_id="goalapi-final", fixture_key=None, kickoff="2026-10-26T19:00:00Z",
            opponent="Leeds United", opponent_long_name="Leeds United",
            published="2026-10-26T21:00:00Z",
            source_updated_at="2026-10-26T20:59:00Z", home_score=2, away_score=1,
            post_expires_at="2026-10-27T00:00:00Z",
        )
        queue = FootballPresentationQueue()
        self.assertTrue(queue.accept_snapshot(
            state, "led/football/" + key, final, epoch(final["published_at"]),
        ))
        self.assertEqual(queue.pop(self.now)["status"], "POST")
        late_live = dict(second, published_at="2026-10-26T21:01:00Z",
                         source_updated_at="2026-10-26T21:00:00Z", home_score=3)
        self.assertFalse(state.accept("led/football/" + key, late_live))
        next_day = dict(second, match_id="next-day", fixture_key="millwall|2026-10-27|leeds",
                        kickoff="2026-10-27T19:00:00Z", published_at="2026-10-27T19:01:00Z",
                        source_updated_at="2026-10-27T19:01:00Z")
        self.assertTrue(state.accept("led/football/" + key, next_day))

    def test_post_requires_final_score_source_time_and_expiry(self):
        invalid = snapshot("millwall", status="POST", home_score=None, away_score=1,
                           post_expires_at="2026-10-27T00:00:00Z")
        self.assertFalse(self.state.accept("led/football/millwall", invalid))
        self.assertEqual(self.state.last_decision, "invalid_final_result")
        invalid = snapshot("millwall", status="POST", home_score=1, away_score=0,
                           source_updated_at=None,
                           post_expires_at="2026-10-27T00:00:00Z")
        self.assertFalse(self.state.accept("led/football/millwall", invalid))
        invalid = snapshot("millwall", status="POST", home_score=1, away_score=0)
        self.assertFalse(self.state.accept("led/football/millwall", invalid))

    def test_interleaved_goal_api_retry_is_deduplicated_after_a_later_event(self):
        state = FootballScreenState()
        first = snapshot(
            "millwall", source="nrwindsor", provider="goalapi",
            fixture_key="millwall|2026-10-26|derby-county", event_id="goal-a",
            event_type="goal.scored", status="IN", home_score=1, away_score=0,
            published="2026-10-26T20:00:05Z", source_updated_at="2026-10-26T20:00:05Z",
        )
        second = dict(
            first, event_id="goal-b", home_score=2,
            published_at="2026-10-26T20:00:10Z",
            source_updated_at="2026-10-26T20:00:10Z",
        )
        self.assertTrue(state.accept("led/football/millwall", first))
        self.assertTrue(state.accept("led/football/millwall", second))
        replay = dict(first, published_at="2026-10-26T20:00:15Z")
        self.assertFalse(state.accept("led/football/millwall", replay))
        screen = score_screen(state, epoch("2026-10-26T20:00:16Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (2, 0))

    def test_different_opponent_on_same_date_is_a_new_fixture(self):
        state = FootballScreenState()
        original = snapshot(
            "millwall", fixture_key="millwall|2026-10-26|derby-county",
            status="IN", home_score=0, away_score=0, clock="12",
        )
        next_match = snapshot(
            "millwall", fixture_key="millwall|2026-10-26|leeds-united",
            status="IN", home_score=0, away_score=0, clock="1",
            published="2026-10-26T20:01:00Z",
        )
        self.assertTrue(state.accept("led/football/millwall", original))
        self.assertTrue(state.accept("led/football/millwall", next_match))
        self.assertEqual(
            state.screen_for_team("millwall", epoch("2026-10-26T20:01:01Z"))["clock"],
            "1",
        )

    def test_goal_api_first_event_uses_previous_score_and_guards_tracker_rollback(self):
        state = FootballScreenState()
        goal = snapshot(
            "millwall", source="nrwindsor", provider="goalapi", match_id="api-99",
            provider_match_id="api-99", fixture_key="millwall|2026-10-26",
            event_id="goal-event-first", event_type="goal.scored",
            previous_home_score=0, previous_away_score=0,
            status="IN", home_score=1, away_score=0,
            published="2026-10-26T20:00:05Z",
            source_updated_at="2026-10-26T20:00:05Z", clock=None,
        )
        self.assertTrue(state.accept("led/football/millwall", goal))
        screen = score_screen(state, epoch("2026-10-26T20:00:06Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertTrue(screen["goal_flash_active"])
        tracker = snapshot(
            "millwall", match_id="tracker-99", fixture_key="millwall|2026-10-26",
            status="IN", home_score=0, away_score=0, clock="31",
            published="2026-10-26T20:00:10Z",
            source_updated_at="2026-10-26T20:00:10Z",
        )
        self.assertTrue(state.accept("led/football/millwall", tracker))
        screen = score_screen(state, epoch("2026-10-26T20:00:11Z"))
        self.assertEqual((screen["home_score"], screen["away_score"]), (1, 0))
        self.assertEqual(screen["clock"], "31")

    def test_unavailable_update_discards_pending_event_and_valid_pregame_recovers(self):
        queue = FootballPresentationQueue()
        initial = snapshot(
            "millwall", team_name="Millwall FC", opponent_long_name="Derby County",
            display_fixture="Millwall vs Derby County",
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", initial, self.now
        ))
        self.assertEqual(len(queue), 1)
        unavailable = snapshot(
            "millwall", published="2026-10-26T20:01:00Z", status="UNAVAILABLE",
            team_name=None, opponent=None, opponent_long_name=None,
            display_fixture=None, kickoff=None,
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", unavailable, self.now
        ))
        self.assertEqual(len(queue), 0)
        self.assertIsNone(self.state.screen_for_team("millwall", self.now))
        self.assertFalse(queue.accept_snapshot(
            self.state, "led/football/millwall", unavailable, self.now
        ))
        recovered = snapshot(
            "millwall", published="2026-10-26T20:02:00Z", team_name="Millwall FC",
            opponent_long_name="Derby County", display_fixture="Millwall vs Derby County",
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", recovered, self.now
        ))
        self.assertEqual(queue.pop(), "millwall")

    def test_active_prompt_cancellation_resumes_the_frozen_rotation(self):
        source = (Path(__file__).resolve().parents[1] / "code.py").read_text()
        tree = ast.parse(source)
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name == "_cancel_active_football")

        class Rotation:
            def __init__(self):
                self.resumed = []
                self.advanced = []

            def resume(self, *args):
                self.resumed.append(args)

            def next(self, *args):
                self.advanced.append(args)

        rotation = Rotation()
        resume_function = next(node for node in tree.body
                               if isinstance(node, ast.FunctionDef)
                               and node.name == "_resume_after_football")
        namespace = {
            "active_football_screen": {"team_key": "millwall"},
            "active_football_started": 200,
            "football_rotation_resume": (100, 3.5),
            "football_pause_started": 300,
            "flash_resume": (100, 3.5),
            "last_render_key": ("football-event-1", "football_score"),
            "rotation": rotation,
            "ticks_ms": lambda: 400,
        }
        exec(compile(ast.Module(body=[resume_function, function], type_ignores=[]),
                     "code.py", "exec"), namespace)
        self.assertTrue(namespace["_cancel_active_football"]())
        self.assertEqual(rotation.resumed, [(400, 100, 3.5)])
        self.assertEqual(rotation.advanced, [(400,)])
        self.assertIsNone(namespace["active_football_screen"])
        self.assertIsNone(namespace["active_football_started"])
        self.assertIsNone(namespace["football_rotation_resume"])
        self.assertIsNone(namespace["football_pause_started"])
        self.assertIsNone(namespace["flash_resume"])
    def test_stale_live_score_becomes_unavailable_without_scores(self):
        updated = "2026-10-26T20:00:00Z"
        self.assertTrue(self.state.accept("led/football/sporting_cp", snapshot(
            status="IN", home_score=1, away_score=0, source_updated_at=updated,
        )))
        self.assertIsNone(self.state.screen_for_team("sporting_cp", None))
        fresh = score_screen(self.state, self.now + 600)
        self.assertEqual(fresh["status"], "IN")
        self.assertIsNone(self.state.screen_for_team("sporting_cp", self.now + 601))
        self.assertTrue(self.state.staleness_changed(self.now))
        self.assertFalse(self.state.staleness_changed(self.now + 600))
        self.assertTrue(self.state.staleness_changed(self.now + 601))

    def test_merged_provider_freshness_uses_each_sources_staleness_threshold(self):
        key = "millwall"
        goal = snapshot(
            key, source="nrwindsor", provider="goalapi", match_id="api-1",
            event_id="goal-1", event_type="goal.scored", status="IN",
            home_score=1, away_score=0, previous_home_score=0, previous_away_score=0,
            published="2026-10-26T20:00:00Z", source_updated_at="2026-10-26T20:00:00Z",
        )
        tracker = snapshot(
            key, match_id="espn-1", fixture_key="millwall|2026-10-26|benfica-fc",
            status="IN", home_score=0, away_score=0, clock="31",
            published="2026-10-26T20:05:00Z", source_updated_at="2026-10-26T20:05:00Z",
        )
        self.assertTrue(self.state.accept("led/football/" + key, goal))
        self.assertTrue(self.state.accept("led/football/" + key, tracker))
        self.assertTrue(self.state.has_live_match(epoch("2026-10-26T20:16:00Z")))
        self.assertFalse(self.state.has_live_match(epoch("2026-10-27T00:06:00Z")))

    def test_fresh_pregame_or_unavailable_snapshot_cannot_regress_live_session(self):
        live = snapshot(
            "millwall", status="IN", match_id="live-match",
            source_updated_at="2026-10-26T20:00:00Z", home_score=1, away_score=0,
        )
        self.assertTrue(self.state.accept("led/football/millwall", live))
        for status in ("PRE", "NOT_FOUND"):
            with self.subTest(status=status):
                update = dict(
                    live, status=status, published_at="2026-10-26T20:01:00Z",
                    source_updated_at="2026-10-26T20:01:00Z",
                )
                self.assertFalse(self.state.accept("led/football/millwall", update))
                self.assertEqual(self.state.last_decision, "live_status_regression_rejected")
                self.assertEqual(self.state._teams["millwall"]["status"], "IN")

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
        value = snapshot(team_name=None, status="IN", home_score=0, away_score=0)
        self.assertTrue(self.state.accept("led/football/sporting_cp", value))
        self.assertEqual(score_screen(self.state, self.now)["title"], "Sporting CP")


if __name__ == "__main__":
    unittest.main()
