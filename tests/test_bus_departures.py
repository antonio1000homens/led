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
    def test_mqtt_requires_runtime_enable_and_filters_by_stop(self):
        state = MqttScreenState()
        payload = {"schema_version": 1, "event": "upsert", "published_at": "2026-10-11T20:00:00Z", "expires_at": "2026-10-11T20:04:00Z", "source": "homeassistant", "screen": screen()}
        self.assertTrue(state.accept("led/screens/sl7-heathrow", payload, 1791748800))
        self.assertEqual(state.screens(1791748800), [])
        config = {"enabled": True, "heathrow_enabled": True, "new_malden_enabled": False,
                  "screen_duration_seconds": 9, "no_services_duration_seconds": 5,
                  "upcoming_bus_count": 2, "display_every_cycles": 3,
                  "stale_after_seconds": 180, "destination_scroll_speed": 24}
        state.configure_bus(config)
        result = state.screens(1791748800)
        self.assertEqual(len(result), 1)
        self.assertEqual([item["trip_id"] for item in result[0]["departures"]], ["a", "b"])
        self.assertEqual(result[0]["duration_seconds"], 9)
        self.assertEqual(result[0]["display_every_cycles"], 3)
        self.assertFalse(result[0]["stale"])
        self.assertTrue(state.screens(1791748990)[0]["stale"])
        state.configure_bus(dict(config, heathrow_enabled=False))
        self.assertEqual(state.screens(1791748800), [])

    def test_mqtt_rejects_mismatched_stop_and_unbounded_retention(self):
        state = MqttScreenState()
        payload = {"schema_version": 1, "event": "upsert", "published_at": "2026-10-11T20:00:00Z", "expires_at": "2026-10-11T20:04:00Z", "source": "homeassistant", "screen": screen()}
        self.assertFalse(state.accept("led/screens/sl7-new-malden", payload, 1791748800))
        self.assertFalse(state.accept("led/screens/sl7-heathrow", dict(payload, expires_at="2026-10-12T20:00:00Z"), 1791748800))

    def test_runtime_replaces_http_bus_without_duplicate_and_skips_configured_cycles(self):
        from screen_client import ScreenRotation
        http = [
            {"id": "sl7-heathrow-intro", "kind": "bus_intro", "duration_seconds": 2, "display_every_cycles": 2},
            dict(screen(), display_every_cycles=2),
            {"id": "rail", "kind": "rail_combined", "duration_seconds": 8, "services": []},
        ]
        mqtt = [dict(screen(), source="homeassistant", display_every_cycles=2)]
        rotation = ScreenRotation()
        rotation.update_sources(http, mqtt, 0)
        self.assertEqual([item["id"] for item in rotation.screens],
                         ["sl7-heathrow-intro", "sl7-heathrow", "rail"])
        self.assertEqual(rotation.screens[1]["source"], "homeassistant")
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
