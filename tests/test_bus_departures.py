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
    def test_mqtt_accepts_bus_contract_and_rejects_wrong_route(self):
        state = MqttScreenState()
        payload = {"schema_version": 1, "event": "upsert", "published_at": "2026-10-11T20:00:00Z", "expires_at": "2026-10-11T20:04:00Z", "source": "homeassistant", "screen": screen()}
        self.assertTrue(state.accept("led/screens/sl7-heathrow", payload, 1791748800))
        invalid = dict(screen(), route="X7")
        payload["screen"] = invalid
        payload["published_at"] = "2026-10-11T20:01:00Z"
        self.assertFalse(state.accept("led/screens/sl7-heathrow", payload, 1791748800))

    def test_normalise_sorts_deduplicates_and_filters_passed(self):
        result = normalise_bus_screen(screen(), 1791748800, count=3)
        self.assertEqual([item["trip_id"] for item in result["departures"]], ["a", "b"])
        self.assertEqual(result["departures"][0]["estimated"], "2026-10-11T20:06:00Z")

    def test_contract_requires_stop_identity(self):
        self.assertTrue(valid_bus_screen(screen(), "sl7-heathrow"))
        self.assertFalse(valid_bus_screen(dict(screen(), stop_key="wrong"), "sl7-heathrow"))


if __name__ == "__main__":
    unittest.main()
