import json
import unittest

from mqtt_screens import MqttScreenState
from screen_client import ScreenRotation


def snapshot(slot="recycling", published="2026-10-07T18:00:00+01:00", expires="2026-10-14T00:00:00+01:00", **screen_changes):
    screen = {
        "id": slot, "kind": "bin_collection", "title": "NEXT COLLECTION",
        "duration_seconds": 8, "slide_speed": 20,
        "collection_date": "2026-10-13",
        "collections": [{"id": "mixed", "label": "Mixed recycling"}],
        "source": "homeassistant", "stale": False,
    }
    screen.update(screen_changes)
    return {
        "schema_version": 1, "event": "upsert", "published_at": published,
        "expires_at": expires, "source": "homeassistant", "screen": screen,
    }


class MqttScreenStateTests(unittest.TestCase):
    def setUp(self):
        self.state = MqttScreenState()
        self.now = 1791392400

    def test_accepts_renderer_payload_and_explicit_timezone_offset(self):
        value = snapshot()
        self.assertTrue(self.state.accept("led/screens/recycling", value, self.now))
        self.assertEqual(self.state.screens(self.now), [value["screen"]])

    def test_retained_active_snapshot_recovers_into_a_fresh_state(self):
        retained = snapshot()
        rebooted_state = MqttScreenState()
        self.assertTrue(rebooted_state.accept("led/screens/recycling", retained, self.now))
        self.assertEqual(rebooted_state.screens(self.now), [retained["screen"]])

    def test_malformed_version_event_topic_and_unknown_kind_are_ignored(self):
        good = snapshot()
        cases = [
            ("led/screens/recycling", "not json"),
            ("led/screens/recycling", {**good, "schema_version": 2}),
            ("led/screens/recycling", {**good, "schema_version": True}),
            ("led/screens/recycling", {**good, "event": "replace"}),
            ("led/screens/other", good),
            ("led/screens/recycling/child", good),
            ("led/screens/a+wildcard", good),
            ("led/flash/reminder", good),
            ("led/screens/recycling", snapshot(kind="new_kind")),
        ]
        for topic, payload in cases:
            self.assertFalse(self.state.accept(topic, payload, self.now))
        self.assertEqual(self.state.screens(self.now), [])

    def test_expired_retained_snapshot_is_rejected_at_boundary(self):
        value = snapshot(expires="2026-10-07T17:00:00Z")
        self.assertFalse(self.state.accept("led/screens/recycling", value, self.now))

    def test_local_expiry_uses_epoch_and_removes_at_boundary(self):
        value = snapshot(expires="2026-10-07T18:01:00+01:00")
        self.assertTrue(self.state.accept("led/screens/recycling", value, self.now))
        expiry = 1791392460
        self.assertEqual(len(self.state.screens(expiry - 1)), 1)
        self.assertEqual(self.state.expire(expiry), ["recycling"])
        self.assertEqual(self.state.screens(expiry), [])

    def test_expiring_current_mqtt_screen_advances_to_http_screen(self):
        http = [{"id": "http", "kind": "message", "duration_seconds": 20}]
        mqtt = snapshot("bin", expires="2026-10-07T17:00:01Z")
        self.assertTrue(self.state.accept("led/screens/bin", mqtt, self.now))
        rotation = ScreenRotation()
        rotation.update_sources(http, self.state.screens(self.now), self.now)
        rotation.index = 1
        rotation.started_at = self.now - 3
        self.assertEqual(rotation.current(self.now)[0]["id"], "bin")
        expiry = self.now + 1
        self.state.expire(expiry)
        rotation.update_sources(http, self.state.screens(expiry), expiry)
        screen, phase = rotation.current(expiry)
        self.assertEqual((screen["id"], phase), ("http", 0))

    def test_older_snapshot_rejected_equal_message_is_idempotent(self):
        first = snapshot()
        self.assertTrue(self.state.accept("led/screens/recycling", first, self.now))
        self.assertFalse(self.state.accept("led/screens/recycling", first, self.now))
        older = snapshot(published="2026-10-07T16:59:59Z", title="OLDER")
        self.assertFalse(self.state.accept("led/screens/recycling", older, self.now))
        self.assertEqual(self.state.screens(self.now)[0]["title"], "NEXT COLLECTION")

    def test_clear_removes_only_its_slot(self):
        one, two = snapshot("one"), snapshot("two")
        self.assertTrue(self.state.accept("led/screens/one", one, self.now))
        self.assertTrue(self.state.accept("led/screens/two", two, self.now))
        clear = {"schema_version": 1, "event": "clear", "published_at": "2026-10-07T19:00:00Z"}
        self.assertTrue(self.state.accept("led/screens/one", clear, self.now))
        self.assertEqual([screen["id"] for screen in self.state.screens(self.now)], ["two"])

    def test_invalid_collection_data_is_rejected(self):
        for collections in ([], [{"id": "", "label": "Mixed"}], [{"id": "x", "label": " "}],
                            [{"id": "x", "label": "A"}] * 3,
                            [{"id": "x", "label": "A"}, {"id": "x", "label": "B"}]):
            self.assertFalse(self.state.accept("led/screens/recycling", snapshot(collections=collections), self.now))

    def test_duration_and_slide_speed_must_be_json_numbers(self):
        self.assertFalse(self.state.accept(
            "led/screens/recycling", snapshot(duration_seconds="8"), self.now
        ))
        self.assertFalse(self.state.accept(
            "led/screens/recycling", snapshot(slide_speed=True), self.now
        ))

    def test_slots_return_in_stable_id_order(self):
        self.state.accept("led/screens/z", snapshot("z"), self.now)
        self.state.accept("led/screens/a", snapshot("a"), self.now)
        self.assertEqual([screen["id"] for screen in self.state.screens(self.now)], ["a", "z"])

    def test_board_local_wildcard_prefix_is_used_for_topic_dispatch(self):
        state = MqttScreenState("homeassistant/screens/+")
        value = snapshot("recycling")
        self.assertTrue(state.accept("homeassistant/screens/recycling", value, self.now))
        with self.assertRaises(ValueError):
            MqttScreenState("homeassistant/#")

    def test_json_string_payload_is_accepted(self):
        self.assertTrue(self.state.accept("led/screens/recycling", json.dumps(snapshot()), self.now))


if __name__ == "__main__":
    unittest.main()
