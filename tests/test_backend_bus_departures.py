import json
import unittest
from datetime import datetime, timezone

from transitous_bus import TransitousBusProvider
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import default_runtime_config


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.value).encode()


class BusProviderTests(unittest.TestCase):
    def test_fetch_filters_route_deduplicates_and_normalises(self):
        calls = []
        payload = [{
            "routeShortName": "SL7", "tripId": "trip-1", "headsign": "West Croydon",
            "place": {"scheduledDeparture": "2026-10-11T20:10:00Z", "departure": "2026-10-11T20:11:00Z"},
        }, {
            "routeShortName": "X26", "tripId": "other", "headsign": "Kingston",
            "place": {"scheduledDeparture": "2026-10-11T20:05:00Z"},
        }, {
            "routeShortName": "SL7", "tripId": "trip-1", "headsign": "duplicate",
            "place": {"scheduledDeparture": "2026-10-11T20:12:00Z"},
        }]
        def opener(request, timeout):
            calls.append((request.full_url, request.headers["User-agent"], timeout))
            return Response(payload)

        provider = TransitousBusProvider(
            stops={"test": {"name": "Test", "stop_id": "stop-1"}}, opener=opener)
        result = provider.fetch(datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc))
        self.assertEqual(len(calls), 1)
        self.assertIn("stopId=stop-1", calls[0][0])
        self.assertEqual(result["test"]["departures"][0]["trip_id"], "trip-1")
        self.assertEqual(result["test"]["departures"][0]["estimated"], "2026-10-11T20:11:00Z")
        self.assertEqual(len(result["test"]["departures"]), 1)

    def test_publisher_emits_backend_bus_screens_when_enabled(self):
        class Store:
            def __init__(self):
                self.state = {"version": 2, "feeds": {}}
            def load(self):
                return self.state
            def save(self, state):
                self.state = state
            def publish(self, payload):
                self.payload = payload

        class Bus:
            def fetch(self, now=None):
                row = {"planned": "2026-10-11T20:10:00Z", "estimated": "2026-10-11T20:11:00Z", "trip_id": "trip-1", "destination": "West Croydon", "cancelled": False, "alerts": False}
                return {key: {"stop_name": name, "stop_id": "stop", "route": "SL7", "observed_at": "2026-10-11T20:00:00Z", "departures": [row]} for key, name in (("heathrow", "Heathrow"), ("new-malden", "New Malden"))}

        runtime = default_runtime_config({})
        runtime["feeds"]["sl7_bus"]["enabled"] = True
        for feed_id in ("departures", "queue_times", "weather", "today"):
            runtime["feeds"][feed_id]["enabled"] = False
        publisher = Publisher(
            PublisherConfig("bucket", "token", thorpe_park_source="off", weather_source="off"), Store(),
            bus_provider=Bus(), runtime_config_store=StaticRuntimeConfigStore(runtime),
            utcnow=lambda: datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc),
        )
        payload = publisher.run()
        screens = [screen for screen in payload["screens"] if screen["kind"] == "bus_departures"]
        self.assertEqual([screen["id"] for screen in screens], ["sl7-heathrow", "sl7-new-malden"])
        self.assertTrue(all(screen["source"] == "transitous" and not screen["stale"] for screen in screens))
        self.assertEqual(screens[0]["departures"][0]["local_time"], "21:11")
        self.assertEqual(screens[0]["departures"][0]["due_text"], "11m")
        self.assertEqual(
            [(screen["kind"], screen.get("words")) for screen in payload["screens"]],
            [("bus_intro", "Beep! Beep!..."), ("bus_departures", None),
             ("bus_intro", "Beep! Beep!..."), ("bus_departures", None)],
        )


        for intro in (item for item in payload["screens"] if item["kind"] == "bus_intro"):
            self.assertEqual(intro["animation_speed"], 24)
            self.assertEqual(intro["display_every_cycles"], 1)
        # Custom text and speed are passed straight to the existing renderer.
        intro = Publisher._bus_intro("heathrow", {
            **runtime["feeds"]["sl7_bus"], "words": "HONK HONK!", "animation_speed": 40,
        })
        self.assertEqual((intro["words"], intro["animation_speed"]), ("HONK HONK!", 40))
        self.assertAlmostEqual(intro["duration_seconds"], 256 / 40 + 1)

        # Turning off the animation keeps both departure pages and their order.
        runtime["feeds"]["sl7_bus"]["bus_intro_enabled"] = False
        without_intro = Publisher(
            PublisherConfig("bucket", "token", thorpe_park_source="off", weather_source="off"), Store(),
            bus_provider=Bus(), runtime_config_store=StaticRuntimeConfigStore(runtime),
            utcnow=lambda: datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc),
        ).run()
        self.assertEqual(
            [(page["kind"], page["id"]) for page in without_intro["screens"]],
            [("bus_departures", "sl7-heathrow"), ("bus_departures", "sl7-new-malden")],
        )

    def test_publisher_excludes_departed_services_and_uses_london_dst(self):
        runtime = default_runtime_config({})
        runtime["feeds"]["sl7_bus"]["upcoming_bus_count"] = 3
        now = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
        source = {
            "stop_name": "Heathrow", "observed_at": "2026-10-11T20:00:00Z",
            "departures": [
                {"planned": "2026-10-11T19:00:00Z", "destination": "old", "trip_id": "old"},
                {"planned": "2026-10-11T20:02:00Z", "destination": "second", "trip_id": "2"},
                {"planned": "2026-10-11T20:01:00Z", "destination": "first", "trip_id": "1"},
            ],
        }
        result = Publisher._bus_screen("heathrow", source, runtime["feeds"]["sl7_bus"], now=now)
        self.assertEqual([r["destination"] for r in result["departures"]], ["first", "second"])
        self.assertEqual(result["departures"][0]["local_time"], "21:01")
        self.assertEqual(result["departures"][0]["due_text"], "Due")
        self.assertEqual(result["display_every_cycles"], 1)


if __name__ == "__main__":
    unittest.main()
