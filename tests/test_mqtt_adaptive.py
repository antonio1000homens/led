"""Regression tests for adaptive MQTT polling on MatrixPortal S3."""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hardware" / "matrixportal" / "firmware"))
sys.path.insert(0, str(ROOT / "shared"))

from mqtt_client import FlashMqttClient
from football_screens import FootballScreenState


class FakeTransport:
    def __init__(self):
        self.calls = 0

    def loop(self, timeout=None):
        self.calls += 1


def snapshot(team, status, published, **changes):
    value = {
        "schema_version": 1,
        "source": "nrwindsor",
        "provider": "goalapi",
        "team_key": team,
        "status": status,
        "match_id": "game-1",
        "published_at": published,
        "source_updated_at": published,
        "home_score": 1,
        "away_score": 0,
        "team_name": team,
        "opponent": "Other",
        **({"post_expires_at": "2026-11-04T00:00:00Z"}
           if status == "POST" else {}),
    }
    value.update(changes)
    return value


class AdaptiveMqttTests(unittest.TestCase):
    def make_client(self):
        client = FlashMqttClient(object(), lambda *_args: None)
        fake = FakeTransport()
        client.client = fake
        client.connected = True
        return client, fake

    def test_idle_live_post_and_actual_poll_intervals(self):
        client, fake = self.make_client()
        self.assertEqual(client.effective_poll_seconds(), 5)
        client.poll(0)
        client.poll(1.5)
        self.assertEqual(fake.calls, 1)
        client.poll(5)
        self.assertEqual(fake.calls, 2)
        client.set_live_match(True, 5)
        self.assertEqual(client.effective_poll_seconds(), 1.5)
        client.poll(6.5)
        self.assertEqual(fake.calls, 3)
        client.set_live_match(False, 6.5)
        self.assertEqual(client.effective_poll_seconds(), 5)
        client.poll(8)
        self.assertEqual(fake.calls, 3)
        client.poll(11.5)
        self.assertEqual(fake.calls, 4)

    def test_admin_config_rejects_malformed_or_unbounded_values(self):
        client, _fake = self.make_client()
        self.assertFalse(client.configure_polling({"mqtt_idle_poll_seconds": 10}, 0))
        self.assertFalse(client.configure_polling({
            "mqtt_adaptive_enabled": True, "mqtt_idle_poll_seconds": 120,
            "mqtt_live_poll_seconds": 1.5,
        }, 0))
        self.assertEqual(client.effective_poll_seconds(), 5)
        self.assertTrue(client.configure_polling({
            "mqtt_adaptive_enabled": False, "mqtt_idle_poll_seconds": 10,
            "mqtt_live_poll_seconds": 1.5,
        }, 0))
        client.set_live_match(True, 0)
        self.assertEqual(client.effective_poll_seconds(), 10)
        self.assertTrue(client.configure_polling({
            "mqtt_adaptive_enabled": True, "mqtt_idle_poll_seconds": 5,
            "mqtt_live_poll_seconds": 2,
        }, 1))
        self.assertEqual(client.effective_poll_seconds(), 2)

    def test_live_match_multi_team_post_and_stale(self):
        state = FootballScreenState()
        t0 = "2026-11-03T12:00:00Z"
        t1 = "2026-11-03T12:05:00Z"
        now = int(datetime(2026, 11, 3, 12, tzinfo=timezone.utc).timestamp())
        self.assertTrue(state.accept("led/football/millwall", snapshot("millwall", "PRE", t0)))
        self.assertFalse(state.has_live_match(now))
        self.assertTrue(state.accept("led/football/millwall", snapshot(
            "millwall", "IN", t1, kickoff="2026-11-03T11:00:00Z",
            fixture_key="millwall|2026-11-03|other",
        )))
        self.assertTrue(state.has_live_match(now + 301))
        self.assertTrue(state.accept("led/football/sporting_cp", snapshot(
            "sporting_cp", "IN", t1, kickoff="2026-11-03T11:00:00Z",
            fixture_key="sporting_cp|2026-11-03|other",
        )))
        self.assertTrue(state.has_live_match(now + 301))
        self.assertTrue(state.accept("led/football/millwall", snapshot(
            "millwall", "POST", "2026-11-03T12:06:00Z",
            kickoff="2026-11-03T11:00:00Z", fixture_key="millwall|2026-11-03|other",
        )))
        self.assertTrue(state.has_live_match(now + 361))
        self.assertTrue(state.accept("led/football/sporting_cp", snapshot(
            "sporting_cp", "POST", "2026-11-03T12:07:00Z",
            kickoff="2026-11-03T11:00:00Z", fixture_key="sporting_cp|2026-11-03|other",
        )))
        self.assertFalse(state.has_live_match(now + 421))
        self.assertTrue(state.accept("led/football/sporting_cp", snapshot(
            "sporting_cp", "IN", "2026-11-03T12:08:00Z", match_id="next-game",
            kickoff="2026-11-03T12:08:00Z", fixture_key="sporting_cp|2026-11-03|new-opponent",
            opponent="New Opponent",
        )))
        self.assertFalse(state.has_live_match(now + 5 * 60 * 60))

    def test_late_message_does_not_keep_stale_team_live(self):
        state = FootballScreenState()
        stamp = "2026-11-03T12:00:00Z"
        now = int(datetime(2026, 11, 3, 12, tzinfo=timezone.utc).timestamp())
        state.accept("led/football/millwall", snapshot("millwall", "IN", stamp))
        self.assertFalse(state.has_live_match(None))
        self.assertTrue(state.has_live_match(now))
        self.assertFalse(state.has_live_match(now + 4 * 60 * 60 + 1))


if __name__ == "__main__":
    unittest.main()
