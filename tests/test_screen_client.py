import unittest

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

    def test_clock_tracks_year_rollover(self):
        clock = ClockState()
        clock.sync("2026-12-31T23:59:50Z", 100)
        self.assertEqual(clock.date_text(115), "2027-01-01")
        self.assertEqual(clock.text(115), "00:00")


class RotationTests(unittest.TestCase):
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
