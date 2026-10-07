import unittest

from flash_events import FlashState, parse_flash_event, _iso_epoch
from mqtt_client import (
    FlashMqttClient,
    MQTT_LOOP_INTERVAL_SECONDS,
    MQTT_SOCKET_TIMEOUT_SECONDS,
)


EVENT = {
    "id": "reminder-1",
    "type": "reminder",
    "event": "due",
    "label": "Take washing out",
    "due_at": "2026-09-21T18:00:00+01:00",
    "expires_at": "2026-09-21T18:05:00+01:00",
    "source": "alexa",
}


class FlashEventTests(unittest.TestCase):
    def test_payload_decoding_accepts_json_strings_bytes_and_dicts(self):
        import json
        encoded = json.dumps(EVENT)
        self.assertEqual(parse_flash_event(encoded, 0)["id"], "reminder-1")
        self.assertEqual(parse_flash_event(encoded.encode("utf-8"), 0)["id"], "reminder-1")
        self.assertEqual(parse_flash_event(EVENT, 0)["id"], "reminder-1")
        self.assertIsNone(parse_flash_event("not-json", 0))

    def test_valid_event_is_normalized_and_expiry_is_checked(self):
        event = parse_flash_event(EVENT, 1790000000)
        self.assertEqual(event["label"], "Take washing out")
        self.assertIsNone(parse_flash_event(EVENT, 1790010400))

    def test_iso8601_fractional_seconds_keep_the_timezone_offset(self):
        payload = {
            **EVENT,
            "due_at": "2026-09-21T18:00:00.123456+01:00",
            "expires_at": "2026-09-21T18:05:00.987654+01:00",
        }
        self.assertIsNotNone(parse_flash_event(payload, 0))
        utc_payload = {
            **EVENT,
            "expires_at": "2026-09-21T17:05:00.123456Z",
        }
        self.assertIsNotNone(parse_flash_event(utc_payload, 0))

    def test_home_assistant_contract_with_published_at_and_offset_is_supported(self):
        import json
        payload = {
            "id": "sensor.echo_living_room_next_reminder|2099-09-21T18:00:00+01:00|Take washing out",
            "type": "reminder",
            "event": "due",
            "label": "Take washing out",
            "due_at": "2099-09-21T18:00:00+01:00",
            "published_at": "2099-09-21T17:42:12+01:00",
            "expires_at": "2099-09-21T18:05:00+01:00",
            "source": "alexa",
        }
        event = parse_flash_event(json.dumps(payload), 4080585600)
        self.assertEqual(event, {
            "id": payload["id"],
            "type": "reminder",
            "label": payload["label"],
            "due_at": payload["due_at"],
            "expires_at": payload["expires_at"],
            "source": "alexa",
        })

    def test_due_occurrence_payload_with_local_offset_is_accepted(self):
        import json
        payload = {
            "id": "alexa|sensor.echo_next_reminder|1790000000|reminder-42",
            "type": "reminder",
            "event": "due",
            "label": "Take washing out",
            "due_at": "2026-09-21T18:00:00+01:00",
            "published_at": "2026-09-21T18:00:01+01:00",
            "expires_at": "2026-09-21T18:05:00+01:00",
            "source": "alexa",
        }
        parsed = parse_flash_event(json.dumps(payload), 1790000001)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["id"], payload["id"])
        self.assertEqual(parsed["due_at"], payload["due_at"])

    def test_recurring_occurrences_with_same_alexa_id_are_distinct(self):
        state = FlashState(enabled=True)
        first = {
            **EVENT,
            "id": "alexa|sensor.echo_next_reminder|1790000000|reminder-42",
        }
        second = {
            **EVENT,
            "id": "alexa|sensor.echo_next_reminder|1790604800|reminder-42",
            "due_at": "2026-09-28T18:00:00+01:00",
            "expires_at": "2026-09-28T18:05:00+01:00",
        }
        self.assertTrue(state.accept(first, 0, epoch_now=_iso_epoch(EVENT["due_at"])))
        self.assertTrue(state.accept(second, 1, epoch_now=_iso_epoch(second["due_at"])))
        self.assertEqual(state.screen()["id"], "flash-" + second["id"])

    def test_malformed_event_is_ignored(self):
        for value in (
            {},
            {**EVENT, "type": "other"},
            {**EVENT, "expires_at": "bad"},
            {**EVENT, "due_at": "2026-09-21T18:00:00"},
        ):
            self.assertIsNone(parse_flash_event(value, 0))

    def test_discovery_or_non_due_event_is_ignored(self):
        self.assertIsNone(parse_flash_event({key: value for key, value in EVENT.items() if key != "event"}, 0))
        self.assertIsNotNone(parse_flash_event({**EVENT, "event": "scheduled"}, 0))

    def test_duplicate_is_ignored_and_new_event_replaces_active(self):
        state = FlashState(enabled=True, duration_seconds=5)
        self.assertTrue(state.accept(EVENT, 0))
        self.assertFalse(state.accept(EVENT, 1))
        replacement = {**EVENT, "id": "reminder-2", "label": "Close the door"}
        self.assertTrue(state.accept(replacement, 2))
        self.assertEqual(state.screen()["label"], "Close the door")
        self.assertTrue(state.active(6))
        self.assertFalse(state.active(8))

    def test_disabled_state_does_not_parse_or_retain_events(self):
        state = FlashState(enabled=False)
        self.assertFalse(state.accept(EVENT, 0))
        self.assertIsNone(state.screen())
        state.configure(enabled=True, duration_seconds=10)
        self.assertTrue(state.accept(EVENT, 0, epoch_now=_iso_epoch(EVENT["due_at"])))
        state.configure(enabled=False)
        self.assertIsNone(state.screen())

    def test_epoch_expiry_and_monotonic_duration_are_separate(self):
        state = FlashState(enabled=True, duration_seconds=5)
        self.assertTrue(state.accept(EVENT, 100.0, epoch_now=_iso_epoch(EVENT["due_at"])))
        self.assertTrue(state.active(104.9))
        self.assertFalse(state.active(105.1))
        self.assertFalse(state.accept(EVENT, 200.0, epoch_now=1790010400))


class ScheduledReminderTests(unittest.TestCase):
    def setUp(self):
        self.state = FlashState(enabled=True)
        self.due = _iso_epoch(EVENT["due_at"])
        self.payload = {**EVENT, "event": "scheduled",
                        "published_at": "2026-09-21T17:59:00+01:00"}

    def test_minute_republication_does_not_fire_early_or_restart_flash(self):
        self.assertFalse(self.state.accept(self.payload, 0, self.due - 60))
        self.assertFalse(self.state.accept(self.payload, 59, self.due - 1))
        self.assertFalse(self.state.active(59))
        self.assertTrue(self.state.tick(60, self.due))
        self.assertFalse(self.state.accept(self.payload, 61, self.due + 1))
        self.assertEqual(self.state.started_at, 60)
        self.assertFalse(self.state.tick(66, self.due + 6))
        self.assertFalse(self.state.accept(self.payload, 67, self.due + 7))

    def test_cancellation_and_older_replay(self):
        self.state.accept(self.payload, 0, self.due - 60)
        clear = {"type": "reminder", "event": "clear",
                 "published_at": "2026-09-21T17:59:30+01:00"}
        self.state.accept(clear, 30, self.due - 30)
        self.state.accept(self.payload, 31, self.due - 29)
        self.assertFalse(self.state.tick(60, self.due))
        self.assertIsNone(self.state.pending)

    def test_edit_replaces_future_occurrence(self):
        self.state.accept(self.payload, 0, self.due - 60)
        edited = {**self.payload, "id": "edited",
                  "due_at": "2026-09-21T18:01:00+01:00",
                  "published_at": "2026-09-21T17:59:30+01:00"}
        self.state.accept(edited, 30, self.due - 30)
        self.assertFalse(self.state.tick(60, self.due))
        self.assertTrue(self.state.tick(120, self.due + 60))
        self.assertEqual(self.state.event["id"], "edited")

    def test_late_receipt_and_expiry(self):
        self.assertTrue(self.state.accept(self.payload, 0, self.due + 60))
        other = FlashState(enabled=True)
        self.assertFalse(other.accept(self.payload, 0, self.due + 300))
        self.assertIsNone(other.pending)
        other.accept(self.payload, 0, self.due - 1)
        self.assertFalse(other.tick(400, self.due + 300))
        self.assertIsNone(other.pending)

    def test_clock_required_and_disable_cancels_pending(self):
        self.assertFalse(self.state.accept(self.payload, 0))
        self.assertIsNone(self.state.pending)
        self.state.accept(self.payload, 0, self.due - 60)
        self.assertFalse(self.state.tick(60, None))
        self.state.configure(enabled=False)
        self.state.configure(enabled=True)
        self.assertFalse(self.state.tick(60, self.due))

    def test_invalid_snapshot_does_not_replace_valid_schedule(self):
        self.state.accept(self.payload, 0, self.due - 60)
        for invalid in ({**self.payload, "due_at": None},
                        {**self.payload, "published_at": "invalid"},
                        {**self.payload, "expires_at": self.payload["due_at"]}):
            self.assertFalse(self.state.accept(invalid, 1, self.due - 59))
        self.assertTrue(self.state.tick(60, self.due))


class FakeSettings:
    MQTT_BROKER = "broker.example"
    MQTT_PORT = 1883
    MQTT_USERNAME = "user"
    MQTT_PASSWORD = "password"
    MQTT_TOPIC = "led/flash/reminder"


class FakeMqtt:
    def __init__(self, callback_payload=None, fail_loop=False):
        self.callback_payload = callback_payload
        self.fail_loop = fail_loop
        self.on_message = None
        self.subscriptions = []
        self.connected = False
        self.loop_calls = 0
        self.loop_timeouts = []
        self.disconnect_calls = 0

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.disconnect_calls += 1
        self.connected = False

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))

    def loop(self, timeout=0):
        self.loop_calls += 1
        self.loop_timeouts.append(timeout)
        if self.fail_loop:
            raise OSError("broker disconnected")
        if self.callback_payload is not None and self.on_message:
            self.on_message(self, FakeSettings.MQTT_TOPIC, self.callback_payload)
            self.callback_payload = None


class MqttTransportTests(unittest.TestCase):
    def test_startup_delay_prevents_mqtt_connection_until_deadline(self):
        attempts = []

        def factory(settings):
            attempts.append(True)
            return FakeMqtt()

        transport = FlashMqttClient(
            FakeSettings,
            lambda payload: None,
            mqtt_factory=factory,
            startup_delay_seconds=30,
            started_at=100,
        )
        transport.poll(129.999)
        self.assertEqual(attempts, [])
        transport.poll(130)
        self.assertEqual(attempts, [True])
        self.assertTrue(transport.connected)

    def test_runtime_disable_disconnects_and_stops_polling_until_reenabled(self):
        first = FakeMqtt()
        second = FakeMqtt()
        clients = [first, second]
        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=lambda settings: clients.pop(0))
        transport.poll(0)
        self.assertTrue(transport.connected)

        transport.set_enabled(False)
        self.assertFalse(transport.connected)
        self.assertEqual(first.disconnect_calls, 1)
        loop_calls_at_disable = first.loop_calls
        transport.poll(1)
        self.assertEqual(first.loop_calls, loop_calls_at_disable)
        self.assertEqual(len(clients), 1)

        transport.set_enabled(True)
        transport.poll(2)
        self.assertTrue(transport.connected)
        self.assertEqual(second.subscriptions, [("led/flash/reminder", 1), ("led/screens/+", 1)])

    def test_runtime_disable_before_first_poll_prevents_connection(self):
        attempts = []

        def factory(settings):
            attempts.append(True)
            return FakeMqtt()

        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=factory)
        transport.set_enabled(False)
        transport.poll(0)
        self.assertEqual(attempts, [])
        transport.set_enabled(True)
        transport.poll(1)
        self.assertEqual(attempts, [True])

    def test_connects_qos_one_and_delivers_string_payload(self):
        received = []
        client = FakeMqtt(json_payload := '{"id":"x","type":"reminder","label":"Hi","expires_at":"2099-01-01T00:00:00Z"}')
        transport = FlashMqttClient(FakeSettings, lambda topic, payload: received.append((topic, payload)), mqtt_factory=lambda settings: client)
        transport.poll(0)
        self.assertEqual(client.subscriptions, [("led/flash/reminder", 1), ("led/screens/+", 1)])
        self.assertEqual(received, [("led/flash/reminder", json_payload)])
        self.assertEqual(client.loop_timeouts, [MQTT_SOCKET_TIMEOUT_SECONDS])

    def test_idle_loop_is_bounded_but_not_run_on_every_frame(self):
        client = FakeMqtt()
        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=lambda settings: client)
        transport.poll(0)
        transport.poll(0.1)
        self.assertEqual(client.loop_calls, 1)
        transport.poll(59.999)
        self.assertEqual(client.loop_calls, 1)
        self.assertEqual(MQTT_LOOP_INTERVAL_SECONDS, 60.0)
        transport.poll(MQTT_LOOP_INTERVAL_SECONDS)
        self.assertEqual(client.loop_calls, 2)
        self.assertEqual(client.subscriptions, [("led/flash/reminder", 1), ("led/screens/+", 1)])

    def test_initial_failure_is_contained_and_later_connect_retries(self):
        attempts = []
        def factory(settings):
            attempts.append(1)
            if len(attempts) == 1:
                raise OSError("offline")
            return FakeMqtt()
        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=factory)
        transport.poll(0)
        self.assertFalse(transport.connected)
        transport.poll(31)
        self.assertTrue(transport.connected)
        self.assertEqual(len(attempts), 2)

    def test_disconnect_is_contained_and_reconnect_resubscribes(self):
        first = FakeMqtt(fail_loop=True)
        second = FakeMqtt()
        clients = [first, second]
        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=lambda settings: clients.pop(0))
        transport.poll(0)
        self.assertFalse(transport.connected)
        self.assertEqual(first.disconnect_calls, 1)
        transport.poll(5)
        self.assertTrue(transport.connected)
        self.assertEqual(clients, [])
        self.assertEqual(second.subscriptions, [("led/flash/reminder", 1), ("led/screens/+", 1)])

    def test_mqtt_outage_does_not_block_http_screen_fetch(self):
        from screen_client import ScreenClient

        transport = FlashMqttClient(
            FakeSettings,
            lambda payload: None,
            mqtt_factory=lambda settings: FakeMqtt(fail_loop=True),
        )
        transport.poll(0)

        class Response:
            status_code = 200
            closed = False

            def json(self):
                return {"screens": [{"id": "departures"}]}

            def close(self):
                self.closed = True

        class Session:
            def get(self, url):
                self.url = url
                return Response()

        class Settings:
            SCREEN_API_URL = "https://led.example"

        payload = ScreenClient(Settings, session=Session()).fetch()
        self.assertEqual(payload["screens"][0]["id"], "departures")


if __name__ == "__main__":
    unittest.main()
