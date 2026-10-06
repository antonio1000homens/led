import unittest
from unittest import mock

import screen_client
from formatting import prepare_rail_presentation
from screen_client import ClockState, ScreenClient, ScreenRotation, london_seconds_from_utc


class ClockTests(unittest.TestCase):
    def test_london_clock_applies_bst_in_summer(self):
        seconds = london_seconds_from_utc("2026-09-12T19:45:30Z")
        self.assertEqual(seconds, 20 * 3600 + 45 * 60 + 30)

    def test_london_clock_uses_gmt_in_winter(self):
        seconds = london_seconds_from_utc("2026-12-12T19:45:30Z")
        self.assertEqual(seconds, 19 * 3600 + 45 * 60 + 30)

    def test_london_dst_boundaries_use_one_am_utc(self):
        self.assertEqual(london_seconds_from_utc("2026-03-29T00:59:30Z"), 59 * 60 + 30)
        self.assertEqual(london_seconds_from_utc("2026-03-29T01:00:00Z"), 2 * 3600)
        self.assertEqual(london_seconds_from_utc("2026-10-25T00:59:30Z"), 1 * 3600 + 59 * 60 + 30)
        self.assertEqual(london_seconds_from_utc("2026-10-25T01:00:00Z"), 1 * 3600)

    def test_clock_advances_between_polls(self):
        clock = ClockState()
        clock.sync("2026-09-12T19:59:45Z", 100)
        self.assertEqual(clock.text(100), "20:59")
        self.assertEqual(clock.text(115), "21:00")

    def test_clock_tracks_london_date_across_midnight(self):
        clock = ClockState()
        clock.sync("2026-09-30T22:59:50Z", 100)
        self.assertEqual(clock.date_text(100), "2026-09-30")
        self.assertEqual(clock.date_text(115), "2026-10-01")
        self.assertEqual(clock.text(115), "00:00")

    def test_clock_sync_uses_local_date_when_bst_is_already_next_day(self):
        clock = ClockState()
        clock.sync("2026-09-30T23:30:00Z", 100)
        self.assertEqual(clock.date_text(100), "2026-10-01")
        self.assertEqual(clock.text(100), "00:30")

    def test_clock_tracks_year_rollover(self):
        clock = ClockState()
        clock.sync("2026-12-31T23:59:50Z", 100)
        self.assertEqual(clock.date_text(115), "2027-01-01")
        self.assertEqual(clock.text(115), "00:00")

    def test_clock_exposes_utc_epoch_for_event_expiry(self):
        clock = ClockState()
        clock.sync("2026-09-21T17:42:12Z", 100.0)
        self.assertEqual(clock.epoch(100.0), 1790012532)
        self.assertEqual(clock.epoch(112.5), 1790012544)
        self.assertIsInstance(clock.epoch(112.5), int)
        self.assertEqual(clock.epoch(113.0) - clock.epoch(112.0), 1)
        self.assertIsNone(ClockState().epoch(100.0))


class RotationTests(unittest.TestCase):
    def test_valid_backend_presentation_is_consumed_without_local_timing(self):
        services = [{"destination": "Waterloo", "stops": [{"station": "Wimbledon", "time": "12:19"}]}]
        presentation = prepare_rail_presentation(services, 20, 2, 8)
        payload = [{
            "id": "rail", "kind": "rail_combined", "duration_seconds": 8,
            "effective_duration_seconds": presentation["effective_duration_seconds"],
            "services": services, "rail_presentation": presentation,
        }]
        rotation = ScreenRotation()
        with mock.patch.object(screen_client, "CALLING_SCROLL_SPEED_OVERRIDE", None), \
             mock.patch.object(screen_client, "rail_calling_timing", side_effect=AssertionError), \
             mock.patch.object(screen_client, "departure_scroll_duration", side_effect=AssertionError):
            rotation.update(payload, 0)
        screen, _ = rotation.current(0)
        self.assertIsNot(screen, payload[0])
        self.assertEqual(screen["rail_presentation"], presentation)
        self.assertEqual(screen["calling_seconds"], presentation["calling_seconds"])
        later, _ = rotation.current(1)
        self.assertIs(later, screen)
        self.assertEqual(later["rail_presentation"], presentation)

    def test_malformed_backend_presentation_uses_legacy_fallback(self):
        rotation = ScreenRotation()
        rotation.update([{
            "id": "rail", "kind": "rail_combined", "duration_seconds": 8,
            "services": [{"destination": "Waterloo", "stops": []}],
            "rail_presentation": {"calling_text": "incomplete"},
        }], 0)
        screen, _ = rotation.current(0)
        self.assertIn("_calling_travel_seconds", screen)
        self.assertNotIn("rail_presentation", screen)

    def test_invalid_backend_timing_metadata_uses_legacy_fallback(self):
        services = [{"destination": "Waterloo", "stops": []}]
        presentation = prepare_rail_presentation(services, 20, 2, 8)
        presentation["calling_travel_seconds"] = -1
        rotation = ScreenRotation()
        with mock.patch.object(screen_client, "CALLING_SCROLL_SPEED_OVERRIDE", None):
            rotation.update([{
                "id": "rail",
                "kind": "rail_combined",
                "duration_seconds": 8,
                "services": services,
                "rail_presentation": presentation,
            }], 0)
        screen, _ = rotation.current(0)
        self.assertIn("_calling_travel_seconds", screen)
        self.assertNotIn("rail_presentation", screen)

    def test_local_scroll_override_recomputes_backend_speed_dependent_timing(self):
        services = [{"destination": "Waterloo", "stops": [{"station": "Wimbledon", "time": "12:19"}]}]
        presentation = prepare_rail_presentation(services, 20, 2, 8)
        rotation = ScreenRotation()
        with mock.patch.object(screen_client, "CALLING_SCROLL_SPEED_OVERRIDE", 8), \
             mock.patch.object(screen_client, "rail_calling_timing", wraps=screen_client.rail_calling_timing) as timing:
            rotation.update([{
                "id": "rail", "kind": "rail_combined", "duration_seconds": 8,
                "services": services, "rail_presentation": presentation,
            }], 0)
        self.assertEqual(timing.call_args.args[:2], (services, 8))
        self.assertEqual(timing.call_count, 1)
        screen, _ = rotation.current(0)
        self.assertEqual(screen["station_scroll_speed"], 8)
        self.assertEqual(screen["rail_presentation"]["calling_text"], presentation["calling_text"])
        self.assertEqual(
            screen["rail_presentation"]["calling_seconds"],
            screen["calling_seconds"],
        )
        self.assertEqual(
            screen["rail_presentation"]["effective_duration_seconds"],
            screen["effective_duration_seconds"],
        )

    def test_rotates_using_each_screen_duration(self):
        rotation = ScreenRotation()
        rotation.update(
            [
                {"id": "rail", "duration_seconds": 8},
                {"id": "queues", "duration_seconds": 5},
            ],
            10,
        )
        self.assertEqual(rotation.current(17)[0]["id"], "rail")
        self.assertEqual(rotation.current(18)[0]["id"], "queues")
        self.assertEqual(rotation.current(23)[0]["id"], "rail")

    def test_refresh_preserves_current_screen_and_rotation_clock(self):
        rotation = ScreenRotation()
        rotation.update(
            [
                {"id": "rail", "duration_seconds": 8},
                {"id": "queues", "duration_seconds": 8},
            ],
            0,
        )
        self.assertEqual(rotation.current(9)[0]["id"], "queues")
        rotation.update(
            [
                {"id": "rail", "duration_seconds": 8, "revision": 2},
                {"id": "queues", "duration_seconds": 8, "revision": 2},
            ],
            10,
        )
        screen, phase = rotation.current(10)
        self.assertEqual(screen["id"], "queues")
        self.assertEqual(screen["revision"], 2)
        self.assertEqual(phase, 2)

    def test_next_advances_immediately_and_restarts_duration(self):
        rotation = ScreenRotation()
        rotation.update(
            [
                {"id": "rail", "duration_seconds": 8},
                {"id": "queues", "duration_seconds": 8},
            ],
            0,
        )
        rotation.next(3)
        screen, phase = rotation.current(3)
        self.assertEqual(screen["id"], "queues")
        self.assertEqual(phase, 0)
        rotation.next(4)
        self.assertEqual(rotation.current(4)[0]["id"], "rail")

    def test_pause_and_resume_preserve_interrupted_screen_phase(self):
        rotation = ScreenRotation()
        rotation.update(
            [{"id": "one", "duration_seconds": 10}, {"id": "two", "duration_seconds": 10}],
            0,
        )
        interrupted = rotation.pause(4)
        self.assertEqual(interrupted[0]["id"], "one")
        self.assertEqual(interrupted[1], 4)
        rotation.update(
            [{"id": "one", "duration_seconds": 10, "revision": 2}, {"id": "two", "duration_seconds": 10}],
            9,
        )
        rotation.resume(9, *interrupted)
        resumed_screen, resumed_phase = rotation.current(9)
        self.assertEqual(resumed_screen["revision"], 2)
        self.assertEqual(resumed_phase, 4)
        self.assertEqual(rotation.current(12)[0]["id"], "one")
        self.assertEqual(rotation.current(19)[0]["id"], "two")


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.closed = False

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload

    def close(self):
        self.closed = True


class CircuitPythonResponse(FakeResponse):
    def __init__(self, payload, status_code=200):
        super().__init__(payload)
        self.status_code = status_code

    def raise_for_status(self):
        raise AssertionError("CircuitPython response should use status_code")


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return self.response


class ClientTests(unittest.TestCase):
    def test_current_http_date_sets_clock_without_changing_data_age(self):
        response = CircuitPythonResponse({"fetched_at": "2026-10-04T21:30:00Z", "screens": []})
        response.headers = {"date": "Sun, 04 Oct 2026 21:31:05 GMT"}
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        payload = ScreenClient(settings, session=FakeSession(response)).fetch()
        self.assertEqual(payload["fetched_at"], "2026-10-04T21:30:00Z")
        clock = ClockState()
        clock.sync(payload["clock_at"], 10)
        self.assertEqual(clock.text(11), "22:31")
        self.assertEqual(clock.epoch(11), 1791149466)
        self.assertTrue(response.closed)

    def test_bad_http_date_does_not_break_screen_fetch(self):
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        for date in (None, "invalid", "Sun, 32 Oct 2026 21:31:05 GMT",
                     "Sun, 04 Oct 2026 25:31:05 GMT"):
            response = CircuitPythonResponse({"fetched_at": "2026-10-04T21:30:00Z", "screens": []})
            response.headers = {"Date": date}
            payload = ScreenClient(settings, session=FakeSession(response)).fetch()
            self.assertNotIn("clock_at", payload)
            self.assertTrue(response.closed)

    def test_fetches_screen_contract_and_closes_response(self):
        response = FakeResponse({"fetched_at": "2026-09-12T19:45:30Z", "screens": []})
        session = FakeSession(response)

        class Settings:
            SCREEN_API_URL = "http://led-backend:8000/"

        payload = ScreenClient(Settings, session=session).fetch()
        self.assertEqual(payload["screens"], [])
        self.assertEqual(session.urls, ["http://led-backend:8000/api/screens"])
        self.assertTrue(response.closed)

    def test_supports_circuitpython_response_status_code(self):
        response = CircuitPythonResponse({"screens": []})

        class Settings:
            SCREEN_API_URL = "https://led.example"

        payload = ScreenClient(Settings, session=FakeSession(response)).fetch()
        self.assertEqual(payload["screens"], [])
        self.assertTrue(response.closed)

    def test_rejects_circuitpython_http_error(self):
        response = CircuitPythonResponse({"error": "no"}, status_code=503)

        class Settings:
            SCREEN_API_URL = "https://led.example"

        with self.assertRaises(ValueError):
            ScreenClient(Settings, session=FakeSession(response)).fetch()
        self.assertTrue(response.closed)

    def test_rejects_invalid_payload(self):
        response = FakeResponse({"services": []})

        class Settings:
            SCREEN_API_URL = "http://led-backend:8000"

        with self.assertRaises(ValueError):
            ScreenClient(Settings, session=FakeSession(response)).fetch()
        self.assertTrue(response.closed)


if __name__ == "__main__":
    unittest.main()
