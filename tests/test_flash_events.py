import unittest

from flash_events import FlashState, parse_flash_event
from mqtt_client import FlashMqttClient


EVENT = {
    "id": "reminder-1",
    "type": "reminder",
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

    def test_malformed_event_is_ignored(self):
        for value in ({}, {**EVENT, "type": "other"}, {**EVENT, "expires_at": "bad"}):
            self.assertIsNone(parse_flash_event(value, 0))

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
        self.assertTrue(state.accept(EVENT, 0, epoch_now=1790000000))
        state.configure(enabled=False)
        self.assertIsNone(state.screen())

    def test_epoch_expiry_and_monotonic_duration_are_separate(self):
        state = FlashState(enabled=True, duration_seconds=5)
        self.assertTrue(state.accept(EVENT, 100.0, epoch_now=1790000000))
        self.assertTrue(state.active(104.9))
        self.assertFalse(state.active(105.1))
        self.assertFalse(state.accept(EVENT, 200.0, epoch_now=1790010400))


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
    def test_connects_qos_one_and_delivers_string_payload(self):
        received = []
        client = FakeMqtt(json_payload := '{"id":"x","type":"reminder","label":"Hi","expires_at":"2099-01-01T00:00:00Z"}')
        transport = FlashMqttClient(FakeSettings, received.append, mqtt_factory=lambda settings: client)
        transport.poll(0)
        self.assertEqual(client.subscriptions, [("led/flash/reminder", 1)])
        self.assertEqual(received, [json_payload])
        self.assertEqual(client.loop_timeouts, [0.1])

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
        clients = [first, FakeMqtt()]
        transport = FlashMqttClient(FakeSettings, lambda payload: None, mqtt_factory=lambda settings: clients.pop(0))
        transport.poll(0)
        self.assertFalse(transport.connected)
        self.assertEqual(first.disconnect_calls, 1)
        transport.poll(5)
        self.assertTrue(transport.connected)
        self.assertEqual(clients, [])

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
