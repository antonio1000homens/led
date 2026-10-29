import unittest
from unittest import mock
from types import SimpleNamespace
from datetime import datetime, timezone

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
    def test_rebuild_replans_when_the_only_retained_mqtt_screen_expires_by_schedule(self):
        rotation = ScreenRotation(ticks_per_second=1000)
        thursday_evening = int(datetime.fromisoformat(
            "2026-10-29T21:36:00+00:00"
        ).timestamp())
        rotation.set_schedule_epoch(thursday_evening)
        recycling = {
            "id": "bin-recycling", "kind": "bin_collection",
            "schedule_windows": [],
        }
        rotation.update_sources([], [recycling], 0)
        self.assertEqual(len(rotation.screens), 1)

        recycling["schedule_windows"] = [{
            "cron": "0 18 * * 0,1,2,3", "duration_minutes": 1440,
        }]
        rotation.update_sources([
            {"id": "today", "kind": "today"},
            {"id": "rail", "kind": "rail_combined"},
        ], [recycling], 1000)

        self.assertGreater(len(rotation.screens), 1)
        self.assertIn("today", [screen["id"] for screen in rotation.screens])
        self.assertIn("rail", [screen["id"] for screen in rotation.screens])
        screen, _ = rotation.current(1000)
        self.assertNotEqual(screen["id"], "schedule-idle")
        self.assertFalse(rotation.schedule_state()["idle"])

    def test_schedule_state_reports_active_and_disabled_cycle_counts(self):
        rotation = ScreenRotation()
        rotation.update_sources([
            {"id": "active", "kind": "message"},
            {"id": "disabled", "kind": "message", "schedule_enabled": False},
            {"id": "active-two", "kind": "message", "schedule_windows": []},
        ], [], 0)

        self.assertEqual(rotation.schedule_state(), {
            "http": 3,
            "mqtt": 0,
            "cycle": 3,
            "active": 2,
            "disabled": 1,
            "windowed": 0,
            "idle": False,
        })

    def test_next_paired_rail_screen_finds_future_train_pair(self):
        rotation = ScreenRotation()
        rotation.update([
            {"id": "static", "kind": "weather"},
            {"id": "train", "kind": "steam_train_intro"},
            {"id": "rail", "kind": "rail_combined"},
        ], 0)
        rotation.index = 0
        self.assertEqual(rotation.next_paired_rail_screen()["id"], "rail")
        rotation.index = 1
        self.assertIsNone(rotation.next_paired_rail_screen())

    def test_next_paired_rail_screen_does_not_pair_across_rotation_end(self):
        rotation = ScreenRotation()
        rotation.update([
            {"id": "rail", "kind": "rail_combined"},
            {"id": "train", "kind": "steam_train_intro"},
        ], 0)
        rotation.index = 0
        self.assertIsNone(rotation.next_paired_rail_screen())

    def test_bus_intro_stays_attached_to_departures(self):
        rotation = ScreenRotation()
        screens = [
            {"id": "intro", "kind": "bus_intro", "stop_key": "heathrow", "duration_seconds": 2},
            {"id": "bus", "kind": "bus_departures", "stop_key": "heathrow", "duration_seconds": 5},
            {"id": "other", "duration_seconds": 3},
        ]
        rotation.update(screens, 0)
        self.assertEqual([item["id"] for item in rotation.screens], ["intro", "bus", "other"])
        self.assertEqual(rotation.current(2)[0]["id"], "bus")

    def test_bus_intros_remain_adjacent_under_static_randomisation(self):
        import random
        screens = [
            {"id": "sl7-heathrow-intro", "kind": "bus_intro", "stop_key": "heathrow", "duration_seconds": 2},
            {"id": "sl7-heathrow", "kind": "bus_departures", "stop_key": "heathrow", "duration_seconds": 4},
            {"id": "sl7-new-malden-intro", "kind": "bus_intro", "stop_key": "new-malden", "duration_seconds": 2},
            {"id": "sl7-new-malden", "kind": "bus_departures", "stop_key": "new-malden", "duration_seconds": 4},
            {"id": "rail", "kind": "rail_combined", "duration_seconds": 4},
            {"id": "fact", "kind": "random_fact", "duration_seconds": 3},
            {"id": "joke", "kind": "dad_joke", "duration_seconds": 3},
        ]
        for seed in range(40):
            rotation = ScreenRotation(rng=random.Random(seed))
            rotation.update(screens, 0)
            ids = [screen["id"] for screen in rotation.screens]
            for stop in ("heathrow", "new-malden"):
                self.assertEqual(ids.index("sl7-" + stop),
                                 ids.index("sl7-" + stop + "-intro") + 1)

    def test_combined_bus_intro_is_adjacent_and_frequency_gated(self):
        import random
        pair = [
            {"id":"sl7-combined-intro","kind":"bus_intro","stop_key":"combined",
             "duration_seconds":2,"display_every_cycles":2},
            {"id":"sl7-combined","kind":"bus_departures_combined",
             "duration_seconds":8,"display_every_cycles":2},
        ]
        for seed in range(20):
            rotation = ScreenRotation(rng=random.Random(seed))
            rotation.update(pair + [
                {"id":"rail","kind":"rail_combined","duration_seconds":5},
                {"id":"joke","kind":"dad_joke","duration_seconds":4}], 0)
            ids = [item["id"] for item in rotation.screens]
            self.assertEqual(ids.index("sl7-combined"), ids.index("sl7-combined-intro") + 1)
            self.assertTrue(rotation.is_paired_transition("sl7-combined-intro",
                                                          pair[1]))
            rotation.cycle_number = 1
            self.assertFalse(any(item["id"].startswith("sl7-") for item in
                                 rotation._cycle_plan(rotation._available_screens())))
        rotation = ScreenRotation()
        rotation.update(pair, 0)
        rotation.update(pair[:1], 1)
        self.assertEqual(rotation.screens, [])

    def test_bus_intro_requires_matching_stop_and_eligible_departures(self):
        rotation = ScreenRotation()
        intro = {"id": "sl7-heathrow-intro", "kind": "bus_intro", "stop_key": "heathrow"}
        other = {"id": "sl7-new-malden", "kind": "bus_departures", "stop_key": "new-malden"}
        self.assertEqual([item["id"] for item in rotation._cycle_plan([intro, other])],
                         ["sl7-new-malden"])
        own = {"id": "sl7-heathrow", "kind": "bus_departures", "stop_key": "heathrow",
               "display_every_cycles": 2}
        rotation.cycle_number = 1
        self.assertEqual(rotation._cycle_plan([intro, own]), [])
        rotation.cycle_number = 0
        rotation.update([intro, dict(own, display_every_cycles=1)], 0)
        self.assertEqual(len(rotation.screens), 2)
        rotation.update([intro], 1)
        self.assertEqual(rotation.screens, [])

    def test_maintenance_cannot_split_bus_intro_and_departures(self):
        rotation = ScreenRotation()
        screens = [
            {"id": "sl7-new-malden-intro", "kind": "bus_intro", "stop_key": "new-malden",
             "duration_seconds": 2},
            {"id": "sl7-new-malden", "kind": "bus_departures", "stop_key": "new-malden",
             "duration_seconds": 5},
            {"id": "other", "kind": "rail_combined", "duration_seconds": 3},
            {"id": "fact", "kind": "random_fact", "duration_seconds": 3},
        ]
        rotation.update(screens, 0)
        ids = [screen["id"] for screen in rotation.screens]
        rotation.index = ids.index("sl7-new-malden")
        rotation.started_at = 2
        self.assertTrue(rotation.is_paired_transition("sl7-new-malden-intro",
                                                      rotation.screens[rotation.index]))
        self.assertFalse(rotation.is_paired_transition("sl7-heathrow-intro",
                                                       rotation.screens[rotation.index]))
        rotation.maintenance_slot(2)
        self.assertEqual([screen["id"] for screen in rotation.screens], ids)
        self.assertEqual(rotation.current(2)[0]["id"], "sl7-new-malden")
        self.assertEqual(rotation.current(6.9)[0]["id"], "sl7-new-malden")

    def test_christmas_intro_stays_attached_to_tracker_under_static_shuffle(self):
        import random
        screens = [
            {"id": "christmas-tracker-intro", "kind": "christmas_tracker_intro", "duration_seconds": 8},
            {"id": "christmas-tracker", "kind": "christmas_tracker", "duration_seconds": 18},
            {"id": "feed", "kind": "message", "duration_seconds": 3},
            {"id": "fact", "kind": "random_fact", "duration_seconds": 3},
        ]
        for seed in range(10):
            rotation = ScreenRotation(rng=random.Random(seed))
            rotation.update(screens, 0)
            ids = [screen["id"] for screen in rotation.screens]
            self.assertEqual(ids.index("christmas-tracker") - ids.index("christmas-tracker-intro"), 1)
            rotation.index = ids.index("christmas-tracker")
            rotation.maintenance_slot(2)
            self.assertEqual([screen["id"] for screen in rotation.screens], ids)

    def test_millisecond_phases_keep_one_pixel_steps_after_days_of_uptime(self):
        rotation = ScreenRotation(ticks_per_second=1000)
        started = 297_805_460
        train = {"id": "train", "kind": "steam_train_intro", "duration_seconds": 33}
        rotation.update([train], started)
        positions = []
        for tick in range(200):
            _, phase = rotation.current(started + tick * 125)
            positions.append(256 - int(phase * 8))
        self.assertEqual(positions, list(range(256, 56, -1)))
        self.assertIsInstance(rotation.started_at, int)

    def test_millisecond_anchors_survive_refresh_freeze_resume_and_rotation(self):
        rotation = ScreenRotation(ticks_per_second=1000)
        started = 297_805_460
        screens = [{"id": "a", "duration_seconds": 1.25},
                   {"id": "b", "duration_seconds": 2}]
        rotation.update(screens, started)
        rotation.update(screens, started + 375)
        self.assertEqual(rotation.current(started + 375)[1], 0.375)
        screen, phase = rotation.freeze(started + 625)
        rotation.resume(started + 50_000, screen, phase)
        self.assertIsInstance(rotation.started_at, int)
        self.assertEqual(rotation.current(started + 50_125)[1], 0.75)
        current, phase = rotation.current(started + 50_750)
        self.assertEqual((current["id"], phase), ("b", 0.125))
        self.assertIsInstance(rotation.started_at, int)

    def test_static_pool_is_selected_locally_and_can_repeat(self):
        class RepeatFirst:
            @staticmethod
            def randrange(limit):
                return 0
        rotation = ScreenRotation(rng=RepeatFirst())
        fact = {"id": "random-fact", "kind": "random_fact", "duration_seconds": 2,
                "items": [{"fact": "One"}, {"fact": "Two"}]}
        rotation.update([fact], 0)
        first = rotation.current(0)[0]
        second = rotation.current(2)[0]
        self.assertEqual(first["fact"], second["fact"])
        self.assertNotIn("content_version", second)
        self.assertNotIn("refresh_ack_url", second)
        rotation.next(3)
        self.assertEqual(rotation.current(3)[0]["id"], "random-fact")

    def test_joke_only_cached_screen_repeats_without_waiting_or_spinning(self):
        rotation = ScreenRotation()
        rotation.update([{"id": "dad-joke", "kind": "dad_joke",
                          "joke": "Only joke", "duration_seconds": 2}], 0)
        self.assertEqual(rotation.current(3)[0]["id"], "dad-joke")

    def test_retired_frequency_is_ignored(self):
        rotation = ScreenRotation()
        rotation.update([{"id":"a","duration_seconds":2,"display_every_cycles":6}],0)
        for now in range(20):
            self.assertEqual(rotation.current(now)[0]["id"],"a")

    def test_http_and_mqtt_sources_merge_in_independent_stable_order(self):
        rotation = ScreenRotation()
        rotation.update_sources(
            [{"id": "http-b", "kind": "message", "duration_seconds": 8},
             {"id": "http-a", "kind": "message", "duration_seconds": 8}],
            [{"id": "mqtt-z", "kind": "bin_collection", "duration_seconds": 8},
             {"id": "mqtt-a", "kind": "bin_collection", "duration_seconds": 8}],
            0,
        )
        self.assertEqual([screen["id"] for screen in rotation.screens],
                         ["http-b", "http-a", "mqtt-a", "mqtt-z"])

    def test_independent_source_removal_keeps_unaffected_screen_phase(self):
        rotation = ScreenRotation()
        http = [{"id": "http", "kind": "message", "duration_seconds": 8}]
        mqtt = [{"id": "mqtt", "kind": "bin_collection", "duration_seconds": 8}]
        rotation.update_sources(http, mqtt, 0)
        rotation.current(3)
        rotation.update_sources(http, [], 4)
        screen, phase = rotation.current(4)
        self.assertEqual((screen["id"], phase), ("http", 4))
        rotation.update_sources([], [mqtt[0]], 5)
        self.assertEqual(rotation.current(5), (mqtt[0], 0))
        rotation.update_sources([], [], 6)
        self.assertEqual(rotation.screens, [])

    def test_removing_current_mqtt_screen_advances_to_survivor_with_fresh_phase(self):
        rotation = ScreenRotation()
        http = [{"id": "http", "kind": "message", "duration_seconds": 8}]
        mqtt = [{"id": "a", "kind": "bin_collection", "duration_seconds": 8},
                {"id": "b", "kind": "bin_collection", "duration_seconds": 8}]
        rotation.update_sources(http, mqtt, 0)
        rotation.index = 1
        rotation.started_at = 0
        rotation.current(3)
        rotation.update_sources(http, [mqtt[1]], 4)
        screen, phase = rotation.current(4)
        self.assertEqual(screen["id"], "b")
        self.assertEqual(phase, 0)

    def test_flash_freezes_and_resumes_mqtt_phase_unless_expired_or_removed(self):
        rotation = ScreenRotation()
        http = [{"id": "http", "kind": "message", "duration_seconds": 8}]
        mqtt = [{"id": "bin", "kind": "bin_collection", "duration_seconds": 8}]
        rotation.update_sources(http, mqtt, 0)
        rotation.index = 1
        rotation.started_at = 0
        interrupted = rotation.freeze(3)
        rotation.current(20)
        rotation.update_sources(http, mqtt, 20)
        self.assertEqual(rotation.current(20), interrupted)
        rotation.resume(20, interrupted[0], interrupted[1])
        self.assertEqual(rotation.current(20), interrupted)
        interrupted = rotation.freeze(22)
        rotation.update_sources(http, [], 24)
        rotation.resume(24, interrupted[0], interrupted[1])
        screen, phase = rotation.current(24)
        self.assertEqual((screen["id"], phase), ("http", 0))

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


class MemoryRetrySession(FakeSession):
    def __init__(self, response):
        super().__init__(response)
        self.fail_first_request = True
        self._connection_manager = type("Manager", (), {
            "_free_sockets": lambda manager, force=False: setattr(
                manager, "closed_sockets", getattr(manager, "closed_sockets", 0) + 1
            )
        })()


class ClientTests(unittest.TestCase):
    def test_shared_weather_is_attached_by_reference_and_legacy_values_are_kept(self):
        shared = {"temperature_c": 17.4, "stale": False}
        screens = [
            {"id": "departures", "kind": "rail_combined"},
            {"id": "legacy", "weather": {"temperature_c": 12}},
        ]

        result = screen_client.attach_shared_weather(screens, shared)

        self.assertIs(result, screens)
        self.assertIs(screens[0]["weather"], shared)
        self.assertEqual(screens[1]["weather"], {"temperature_c": 12})

    def test_request_memoryerror_retries_once_without_touching_injected_socket_manager(self):
        response = CircuitPythonResponse({"screens": []})
        session = MemoryRetrySession(response)

        def get_with_one_memory_error(url):
            session.urls.append(url)
            if session.fail_first_request:
                session.fail_first_request = False
                raise MemoryError("simulated response setup allocation")
            return response

        session.get = get_with_one_memory_error
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})

        payload = ScreenClient(settings, session=session).fetch()

        self.assertEqual(payload["screens"], [])
        self.assertEqual(len(session.urls), 2)
        self.assertEqual(getattr(session._connection_manager, "closed_sockets", 0), 0)
        self.assertTrue(response.closed)

    def test_owned_recovery_closes_only_the_screen_pool_and_rebuilds_session_tls(self):
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        client = ScreenClient(settings)
        pool = object()
        client.session = object()
        client._socket_pool = pool
        manager_module = type("ConnectionManagerModule", (), {})()
        calls = []
        manager_module.connection_manager_close_all = lambda **kwargs: calls.append(kwargs)
        with mock.patch.dict("sys.modules", {"adafruit_connection_manager": manager_module}):
            client._recover_request_memory_error()
        self.assertEqual(calls, [{"socket_pool": pool, "release_references": True}])
        self.assertIsNone(client.session)
        self.assertIs(client._socket_pool, pool)
        self.assertIsNone(client._ssl_context)

    def test_managed_http_uses_a_dedicated_pool_and_instruments_only_once(self):
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        client = ScreenClient(settings)
        shared_mqtt_pool = object()
        screen_pool = object()
        closed_pools = []
        base_calls = []

        class Manager:
            def get_socket(self):
                base_calls.append(True)
                return object()

        manager = Manager()

        class SSLContext:
            def load_verify_locations(self, **_kwargs):
                return None

            def wrap_socket(self, *args, **_kwargs):
                if args and args[0] == "fail":
                    raise MemoryError("private allocation detail")
                return "wrapped"

        class Session:
            def __init__(self, pool, context):
                self.pool = pool
                self.context = context

        connection_manager = SimpleNamespace(
            get_radio_socketpool=lambda _radio: shared_mqtt_pool,
            get_connection_manager=lambda _pool: manager,
            connection_manager_close_all=lambda **kwargs: closed_pools.append(kwargs),
        )
        modules = {
            "adafruit_connection_manager": connection_manager,
            "adafruit_ntp": SimpleNamespace(),
            "adafruit_requests": SimpleNamespace(Session=Session, __version__="4.1.17"),
            "socketpool": SimpleNamespace(SocketPool=lambda _radio: screen_pool),
            "ssl": SimpleNamespace(create_default_context=SSLContext),
            "rtc": SimpleNamespace(),
            "wifi": SimpleNamespace(radio=SimpleNamespace(connected=True)),
        }
        with mock.patch.dict("sys.modules", modules):
            client._ensure_session()
            self.assertIs(client.session.pool, screen_pool)
            self.assertIsNot(client.session.pool, shared_mqtt_pool)
            with self.assertRaises(MemoryError):
                client._ssl_context.wrap_socket("fail")
            self.assertEqual(client._fetch_stage, "tls_setup")
            self.assertEqual(client._ssl_context.wrap_socket("socket"), "wrapped")
            self.assertEqual(client._fetch_stage, "connection_setup")
            manager.get_socket()
            self.assertEqual(client._fetch_stage, "response_headers")
            client._recover_request_memory_error()
            self.assertEqual(closed_pools, [{"socket_pool": screen_pool, "release_references": True}])
            client._ensure_session()
            manager.get_socket()
        self.assertEqual(len(base_calls), 2)

    def test_failed_recovery_retry_returns_to_caller_and_closes_any_response(self):
        response = CircuitPythonResponse({"screens": []})
        session = MemoryRetrySession(response)
        session.get = lambda _url: (_ for _ in ()).throw(MemoryError("allocation"))
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        client = ScreenClient(settings, session=session)
        with mock.patch.object(client, "_recover_request_memory_error", wraps=client._recover_request_memory_error) as recover:
            with self.assertRaises(MemoryError):
                client.fetch()
        self.assertEqual(recover.call_count, 2)
        self.assertEqual(client.last_error_class, "MemoryError")
        self.assertEqual(client.last_error_stage, "connection_setup")

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

    def test_json_failure_closes_response_and_records_body_stage(self):
        response = CircuitPythonResponse({"screens": []})
        response.json = lambda: (_ for _ in ()).throw(ValueError("private body"))
        settings = type("Settings", (), {"SCREEN_API_URL": "https://led.example"})
        client = ScreenClient(settings, session=FakeSession(response))
        with self.assertRaisesRegex(ValueError, "private body"):
            client.fetch()
        self.assertTrue(response.closed)
        self.assertEqual(client.last_error_stage, "response_body")
        self.assertEqual(client.last_error_class, "ValueError")


if __name__ == "__main__":
    unittest.main()
