import unittest

from bus_departures import normalise_bus_screen, valid_bus_screen
from mqtt_screens import MqttScreenState


def screen():
    return {
        "id": "sl7-heathrow", "kind": "bus_departures", "route": "SL7",
        "stop_key": "heathrow", "stop_name": "Heathrow", "title": "SL7 HEATHROW",
        "observed_at": "2026-10-11T20:00:00Z", "duration_seconds": 8,
        "departures": [
            {"trip_id": "b", "destination": "West Croydon", "planned": "2026-10-11T20:10:00Z", "estimated": None, "cancelled": False, "alerts": False},
            {"trip_id": "a", "destination": "West Croydon", "planned": "2026-10-11T20:05:00Z", "estimated": "2026-10-11T20:06:00Z", "cancelled": False, "alerts": True},
            {"trip_id": "a", "destination": "duplicate", "planned": "2026-10-11T20:07:00Z", "estimated": None, "cancelled": False, "alerts": False},
        ],
    }


class BusDepartureTests(unittest.TestCase):
    def test_sl7_mqtt_messages_are_rejected_even_if_retained(self):
        state = MqttScreenState()
        for stop in ("heathrow", "new-malden"):
            screen_data = dict(screen(), id="sl7-" + stop, stop_key=stop)
            payload = {"schema_version": 1, "event": "upsert",
                       "published_at": "2026-10-11T20:00:00Z",
                       "expires_at": "2026-10-11T20:04:00Z",
                       "source": "homeassistant", "screen": screen_data}
            self.assertFalse(state.accept("led/screens/sl7-" + stop, payload, 1791748800))
            self.assertFalse(state.accept("led/screens/other-bus", payload, 1791748800))
            self.assertFalse(state.accept("led/screens/sl7-" + stop, {
                "schema_version": 1, "event": "clear",
                "published_at": "2026-10-11T20:00:00Z"}, 1791748800))
        self.assertEqual(state.screens(1791748800), [])

    def test_unrelated_mqtt_recycling_screen_is_unchanged(self):
        state = MqttScreenState()
        bin_screen = {
            "id": "homeassistant-next-bin", "kind": "bin_collection",
            "title": "Next collection", "duration_seconds": 8, "slide_speed": 20,
            "collection_date": "2026-10-13",
            "collections": [{"id": "recycling", "label": "Recycling"}],
        }
        payload = {"schema_version": 1, "event": "upsert",
                   "published_at": "2026-10-11T20:00:00Z",
                   "expires_at": "2026-10-11T20:04:00Z",
                   "source": "homeassistant", "screen": bin_screen}
        self.assertTrue(state.accept("led/screens/homeassistant-next-bin", payload, 1791748800))
        self.assertEqual(state.screens(1791748800), [bin_screen])
        self.assertEqual(state.screens(1791749050), [])

    def test_http_bus_wins_if_old_mqtt_message_is_injected(self):
        from screen_client import ScreenRotation
        http = [
            {"id": "sl7-heathrow-intro", "kind": "bus_intro", "duration_seconds": 2, "display_every_cycles": 2},
            dict(screen(), source="transitous", display_every_cycles=2),
            {"id": "rail", "kind": "rail_combined", "duration_seconds": 8, "services": []},
        ]
        mqtt = [dict(screen(), source="homeassistant", display_every_cycles=2)]
        rotation = ScreenRotation()
        rotation.update_sources(http, mqtt, 0)
        self.assertEqual([item["id"] for item in rotation.screens],
                         ["sl7-heathrow-intro", "sl7-heathrow", "rail"])
        self.assertEqual(rotation.screens[1]["source"], "transitous")
        rotation.cycle_number = 1
        self.assertEqual([item["id"] for item in rotation._cycle_plan(rotation._available_screens())], ["rail"])

    def test_normalise_sorts_deduplicates_and_filters_passed(self):
        result = normalise_bus_screen(screen(), 1791748800, count=3)
        self.assertEqual([item["trip_id"] for item in result["departures"]], ["a", "b"])
        self.assertEqual(result["departures"][0]["estimated"], "2026-10-11T20:06:00Z")

    def test_contract_requires_stop_identity(self):
        self.assertTrue(valid_bus_screen(screen(), "sl7-heathrow"))
        self.assertFalse(valid_bus_screen(dict(screen(), stop_key="wrong"), "sl7-heathrow"))


if __name__ == "__main__":
    unittest.main()
