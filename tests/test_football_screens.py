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

from football_screens import (
    FootballPresentationQueue, FootballScreenState, football_presentation_position,
    football_screen_lines, kickoff_countdown, kickoff_local_label,
    football_due_in, football_slide_offset, football_roll_frame,
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

    def _text(self, value, x, y, color, scale=1):
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
        self.assertEqual(kinds.count("football_intro"), 0)
        self.assertEqual(
            {screen["id"] for screen in rotation.screens if screen["kind"] == "football_score"},
            {"football-sporting_cp", "football-millwall"},
        )

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
            ("MILLWALL VS DERBY COUNTY", "SAT 31 OCT 15:00"),
        )

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
            self.assertTrue(self.state.accept("led/football/sporting_cp", value))
            screen = score_screen(self.state, self.now)
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
            "MILLWALL VS DERBY COUNTY", "MON 26 OCT 22:00"
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
                self.assertEqual(rows, ("MILLWALL VS DERBY COUNTY", "SAT 31 OCT 15:00"))
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
                         "02D 05H 14M 09S")
        self.assertEqual(football_due_in(kickoff, base - 86401), "01D 00H 00M 01S")
        self.assertEqual(football_due_in(kickoff, base - 86400), "24H 00M 00S")
        self.assertEqual(football_due_in(kickoff, base - 3601), "01H 00M 01S")
        self.assertEqual(football_due_in(kickoff, base - 3600), "60M 00S")
        self.assertEqual(football_due_in(kickoff, base - 61), "01M 01S")
        self.assertEqual(football_due_in(kickoff, base - 60), "UNDER 1 MIN")
        self.assertEqual(football_due_in(kickoff, base - 1), "UNDER 1 MIN")
        self.assertEqual(football_due_in(kickoff, base), "DUE NOW")
        self.assertEqual(football_due_in(kickoff, base + 100), "DUE NOW")
        self.assertEqual(football_due_in("invalid", base), "TBC")
        self.assertEqual(football_due_in(kickoff, None), "TBC")

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
        display._draw_screen(screen, phase=3.2)
        self.assertTrue(display.pixels)
        self.assertTrue(all(2 <= x < 18 for x, _, _ in display.pixels))
        self.assertEqual([row[0] for row in display.text], [
            "MILLWALL VS DERBY COUNTY", "SAT 31 OCT 15:00",
        ])
        self.assertTrue(all(x >= 22 for _, x, _, _ in display.text))
        self.assertEqual([row[2] for row in display.text], [5, 18])

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
drawFootball(sample, 3.2); results.push(drawn.slice());
process.stdout.write(JSON.stringify(results));
"""
        result = subprocess.run(["node", "-e", harness], check=True, capture_output=True, text=True)
        output = json.loads(result.stdout)
        self.assertEqual(output[0], ["MILLWALL VS DERBY COUNTY", "SAT 31 OCT 15:00"])
        self.assertEqual(output[1], "TIME TBC")
        self.assertEqual(output[2], "SUN 29 MAR 02:30")
        self.assertEqual(output[3], "SUN 25 OCT 01:30")
        self.assertEqual(output[4], {"x": 256, "infoVisible": False})
        self.assertEqual(output[5], {"x": 2, "infoVisible": True})
        self.assertEqual(output[6], {"x": 2, "infoVisible": True})
        self.assertEqual(output[7], "03D 05H 14M 09S")
        # Both rows are laid out while entering; their x is initially off
        # screen and then reaches the original left-column coordinates.
        self.assertEqual(output[8], [
            ["MILLWALL VS DERBY COUNTY", 276, 5],
            ["SAT 31 OCT 15:00", 276, 18],
        ])
        self.assertEqual(output[9][:3], [
            ["MILLWALL VS DERBY COUNTY", 276, 5],
            ["SAT 31 OCT 15:00", 276, 18],
            ["MILLWALL VS DERBY COUNTY", 22, 5],
        ])
        self.assertIn(["DUE IN", 214, 5], output[9])
        self.assertIn("screen.kind === 'football_score'", html)
        self.assertIn("document.getElementById('football-preview')", html)

    def test_prompt_presentation_queue_is_per_team_and_coalesces_bursts(self):
        queue = FootballPresentationQueue()
        self.assertTrue(queue.schedule("millwall"))
        self.assertFalse(queue.schedule("millwall"))
        self.assertTrue(queue.schedule("sporting_cp"))
        self.assertFalse(queue.schedule("unknown"))
        self.assertEqual(len(queue), 2)
        self.assertEqual(queue.pop(), "millwall")
        self.assertTrue(queue.schedule("millwall"))
        self.assertEqual(queue.pop(), "sporting_cp")
        self.assertEqual(queue.pop(), "millwall")
        self.assertIsNone(queue.pop())

    def test_only_accepted_newer_snapshots_request_prompt_presentation(self):
        queue = FootballPresentationQueue()
        first = snapshot("millwall", team_name="Millwall FC")
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", first
        ))
        self.assertEqual(len(queue), 1)
        self.assertFalse(queue.accept_snapshot(
            self.state, "led/football/millwall", first
        ))
        invalid = dict(first, status="INVALID")
        self.assertFalse(queue.accept_snapshot(
            self.state, "led/football/millwall", invalid
        ))
        self.assertEqual(len(queue), 1)
        newer = snapshot("millwall", published="2026-10-26T20:01:00Z",
                         team_name="Millwall FC")
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", newer
        ))
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue.pop(), "millwall")
        same_fixture_update = snapshot(
            "millwall", published="2026-10-26T20:02:00Z", team_name="Millwall FC"
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", same_fixture_update
        ))
        self.assertEqual(len(queue), 0)
        next_fixture = snapshot(
            "millwall", published="2026-10-26T20:03:00Z", team_name="Millwall FC",
            match_id="event-456", kickoff="2026-11-07T15:00:00Z",
        )
        self.assertTrue(queue.accept_snapshot(
            self.state, "led/football/millwall", next_fixture
        ))
        self.assertEqual(queue.pop(), "millwall")

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

            def resume(self, *args):
                self.resumed.append(args)

        rotation = Rotation()
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
        exec(compile(ast.Module(body=[function], type_ignores=[]), "code.py", "exec"), namespace)
        self.assertTrue(namespace["_cancel_active_football"]())
        self.assertEqual(rotation.resumed, [(400, 100, 3.5)])
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
