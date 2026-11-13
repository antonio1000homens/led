import json
from pathlib import Path
import unittest
from datetime import datetime, timezone

from tfl_bus import DEFAULT_STOPS, TflBusProvider
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


class TflBusProviderTests(unittest.TestCase):
    def test_lambda_packager_includes_the_new_provider_module(self):
        root = Path(__file__).resolve().parents[1]
        self.assertIn('"${ROOT_DIR}/backend/tfl_bus.py"',
                      (root / "scripts" / "package-lambda.sh").read_text())

    def test_default_stops_are_the_live_tfl_stop_ids(self):
        self.assertEqual(
            {key: value["stop_id"] for key, value in DEFAULT_STOPS.items()},
            {"heathrow": "4900801619", "new-malden": "490015206J"},
        )

    def test_fetch_is_anonymous_and_keeps_only_exact_stop_live_sl7_predictions(self):
        calls = []
        payloads = {
            "4900801619": [
                {"lineName": "SL7", "naptanId": "4900801619", "id": "trip-1",
                 "expectedArrival": "2026-11-12T22:55:20Z", "timeToStation": 161,
                 "destinationName": "West Croydon", "vehicleId": "LF26KUA"},
                {"lineName": "X26", "naptanId": "4900801619", "id": "other",
                 "expectedArrival": "2026-11-12T22:56:20Z"},
                {"lineName": "SL7", "naptanId": "wrong-stop", "id": "wrong-stop",
                 "expectedArrival": "2026-11-12T22:57:20Z"},
                {"lineName": "SL7", "naptanId": "4900801619", "id": "no-prediction"},
            ],
            "490015206J": [
                {"lineName": "SL7", "naptanId": "490015206J", "id": "trip-2",
                 "expectedArrival": "2026-11-12T22:59:32Z", "timeToStation": 385,
                 "destinationName": "West Croydon"},
            ],
        }

        def opener(request, timeout):
            calls.append((request.full_url, request.headers["User-agent"], timeout))
            stop_id = request.full_url.rsplit("/", 2)[-2]
            return Response(payloads[stop_id])

        provider = TflBusProvider(opener=opener)
        now = datetime(2026, 11, 12, 22, 52, tzinfo=timezone.utc)
        result = provider.fetch(now)
        self.assertEqual(len(calls), 2)
        self.assertIn("/StopPoint/4900801619/Arrivals", calls[0][0])
        self.assertIn("/StopPoint/490015206J/Arrivals", calls[1][0])
        self.assertTrue(all("app_key" not in call[0] and "app_id" not in call[0] for call in calls))
        row = result["heathrow"]["departures"][0]
        self.assertEqual(row["estimated"], "2026-11-12T22:55:20Z")
        self.assertEqual(row["planned"], row["estimated"])
        self.assertEqual(row["destination"], "West Croydon")
        self.assertEqual(row["time_basis"], "live_prediction")
        self.assertEqual(row["time_to_station_seconds"], 161)
        self.assertEqual(result["heathrow"]["source"], "tfl")
        self.assertEqual(result["heathrow"]["observed_at"], "2026-11-12T22:52:00Z")
        self.assertEqual(len(result["heathrow"]["departures"]), 1)

    def test_selected_tfl_provider_falls_back_to_transitous_only_on_request_error(self):
        class FailingTfl:
            def fetch(self, now=None):
                raise TimeoutError("offline")

        class Transitous:
            def fetch(self, now=None):
                return {key: {"source": "transitous", "departures": []}
                        for key in ("heathrow", "new-malden")}

        publisher = Publisher(
            PublisherConfig("bucket", "token", thorpe_park_source="off", weather_source="off"),
            object(), bus_provider=Transitous(), tfl_bus_provider=FailingTfl(),
        )
        data = publisher._fetch_buses_from("tfl", datetime(2026, 11, 12, tzinfo=timezone.utc))
        self.assertTrue(all(stop["source"] == "transitous" for stop in data.values()))
        self.assertTrue(all(stop["fallback_from"] == "tfl" for stop in data.values()))
        self.assertTrue(all(stop["requested_provider"] == "tfl" for stop in data.values()))

    def test_empty_tfl_response_is_not_replaced_with_transitous_timetable_rows(self):
        class EmptyTfl:
            def fetch(self, now=None):
                return {key: {"source": "tfl", "departures": []}
                        for key in ("heathrow", "new-malden")}

        class MustNotFallback:
            def fetch(self, now=None):
                raise AssertionError("empty TfL results are not a provider error")

        publisher = Publisher(
            PublisherConfig("bucket", "token", thorpe_park_source="off", weather_source="off"),
            object(), bus_provider=MustNotFallback(), tfl_bus_provider=EmptyTfl(),
        )
        data = publisher._fetch_buses_from("tfl", datetime(2026, 11, 12, tzinfo=timezone.utc))
        self.assertTrue(all(stop["source"] == "tfl" for stop in data.values()))
        self.assertTrue(all(not stop["departures"] for stop in data.values()))
        self.assertTrue(all("fallback_from" not in stop for stop in data.values()))

    def test_publisher_selects_tfl_and_labels_the_rendered_live_predictions(self):
        class Store:
            def __init__(self):
                self.state = {"version": 2, "feeds": {}}

            def load(self):
                return self.state

            def save(self, state):
                self.state = state

            def publish(self, payload):
                self.payload = payload

        class MustNotUseTransitous:
            def fetch(self, now=None):
                raise AssertionError("selected TfL provider was bypassed")

        class Tfl:
            def fetch(self, now=None):
                return {key: {
                    "stop_name": name, "source": "tfl", "observed_at": "2026-11-12T20:00:00Z",
                    "departures": [{"planned": "2026-11-12T20:05:00Z", "estimated": "2026-11-12T20:05:00Z",
                                    "time_basis": "live_prediction", "trip_id": key, "destination": "West Croydon"}],
                } for key, name in (("heathrow", "Heathrow"), ("new-malden", "New Malden"))}

        runtime = default_runtime_config({})
        runtime["feeds"]["sl7_bus"].update(enabled=True, provider="tfl", bus_intro_enabled=False)
        for feed_id in ("departures", "queue_times", "weather", "today"):
            runtime["feeds"][feed_id]["enabled"] = False
        store = Store()
        now = datetime(2026, 11, 12, 20, 0, tzinfo=timezone.utc)
        publisher = Publisher(
            PublisherConfig("bucket", "token", thorpe_park_source="off", weather_source="off"), store,
            bus_provider=MustNotUseTransitous(), tfl_bus_provider=Tfl(),
            runtime_config_store=StaticRuntimeConfigStore(runtime), utcnow=lambda: now,
        )
        payload = publisher.run()
        combined = next(screen for screen in payload["screens"] if screen["kind"] == "bus_departures_combined")
        self.assertEqual(combined["source"], "tfl")
        for direction in combined["directions"].values():
            self.assertEqual(direction["source"], "tfl")
            self.assertEqual(direction["departures"][0]["time_basis"], "live_prediction")
        self.assertEqual(store.state["feeds"]["sl7_bus"]["data"]["heathrow"]["requested_provider"], "tfl")


if __name__ == "__main__":
    unittest.main()
