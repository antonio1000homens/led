"""Cubs calendar security, ICS, runtime configuration and publisher regression tests."""
import copy
import unittest
from datetime import datetime, timedelta, timezone

from cubs import CubsCalendarProvider, parse_cubs_events
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import (
    RuntimeConfigValidationError, default_runtime_config, schema_metadata,
    validate_feed_patch, validate_runtime_config,
)


NOW = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)
ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:cubs-1
DTSTART;TZID=Europe/London:20261028T183000
DTEND;TZID=Europe/London:20261028T200000
SUMMARY:Navigation\\, Skills and
 Outdoor Games
LOCATION:Private Scout Hall
DESCRIPTION:Never publish this private instruction
END:VEVENT
BEGIN:VEVENT
UID:cubs-2
DTSTART;VALUE=DATE:20261029
DTEND;VALUE=DATE:20261030
SUMMARY:Half Term - No Meeting
END:VEVENT
BEGIN:VEVENT
UID:cubs-past
DTSTART;TZID=Europe/London:20261020T183000
SUMMARY:Old Cubs event
END:VEVENT
BEGIN:VEVENT
UID:cubs-cancelled
DTSTART;TZID=Europe/London:20261030T183000
SUMMARY:Cancelled meeting
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR
"""


class FakeProvider:
    def __init__(self, events):
        self.events = events
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return copy.deepcopy(self.events)


class MemoryStore:
    def __init__(self):
        self.state = {"version": 2, "feeds": {}}
        self.screen = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, value):
        self.state = copy.deepcopy(value)

    def publish(self, value):
        self.screen = copy.deepcopy(value)


class FakeSSM:
    def __init__(self, values):
        self.values = values
        self.calls = []

    def get_parameter(self, **kwargs):
        self.calls.append(kwargs)
        return {"Parameter": {"Value": self.values[kwargs["Name"]]}}


class FakeResponse:
    def __init__(self, url, content):
        self.url = url
        self.content = content.encode()

    def geturl(self):
        return self.url

    def read(self, maximum):
        return self.content[:maximum]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class CubsTests(unittest.TestCase):
    def test_scouts_header_date_and_two_line_event_title(self):
        from display import (
            scouts_event_when, scouts_event_title_lines, SCOUTS_INTRO_SLIDE_SECONDS
        )
        self.assertEqual(SCOUTS_INTRO_SLIDE_SECONDS, 2.4)
        event = {
            "date_text": "05/11", "time_text": "18:30", "all_day": False,
            "title": "Forest Adventure and Nature Games",
        }
        self.assertEqual(scouts_event_when(event), "05/11 18:30")
        self.assertEqual(scouts_event_title_lines(event["title"]),
                         ("FOREST ADVENTURE AND", "NATURE GAMES"))
        self.assertEqual(scouts_event_when({
            "date_text": "07/11", "all_day": True,
        }), "07/11 ALL DAY")
        first, second = scouts_event_title_lines(
            "This super long pack event name is intentionally much too big"
        )
        self.assertLessEqual(len(first), 21)
        self.assertLessEqual(len(second), 21)
        self.assertTrue(second.endswith("..."))
        self.assertEqual(scouts_event_title_lines("Short hike"), ("SHORT HIKE", ""))
        self.assertEqual(scouts_event_title_lines(None), ("", ""))

    def test_ics_normalisation_and_privacy(self):
        rows = parse_cubs_events(ICS, now=NOW)
        self.assertEqual([row["title"] for row in rows], [
            "Navigation, Skills andOutdoor Games", "Half Term - No Meeting"
        ])
        self.assertEqual(rows[0]["date_text"], "28/10")
        self.assertEqual(rows[0]["time_text"], "18:30")
        self.assertTrue(rows[1]["all_day"])
        self.assertEqual(rows[1]["time_text"], "")
        self.assertNotIn("LOCATION", str(rows))
        self.assertNotIn("Private Scout Hall", str(rows))
        self.assertNotIn("Never publish", str(rows))

    def test_recurring_meetings_and_override(self):
        ics = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:weekly
DTSTART;TZID=Europe/London:20261021T183000
DTEND;TZID=Europe/London:20261021T200000
RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=WE
SUMMARY:Weekly meeting
END:VEVENT
BEGIN:VEVENT
UID:weekly
RECURRENCE-ID;TZID=Europe/London:20261028T183000
DTSTART;TZID=Europe/London:20261029T190000
SUMMARY:Changed meeting
END:VEVENT
BEGIN:VEVENT
UID:weekly
RECURRENCE-ID;TZID=Europe/London:20261104T183000
DTSTART;TZID=Europe/London:20261104T183000
SUMMARY:Cancelled occurrence
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""
        rows = parse_cubs_events(ics, now=NOW)
        self.assertEqual([r["title"] for r in rows], ["Changed meeting", "Weekly meeting"])
        self.assertEqual(rows[0]["date_text"], "29/10")
        self.assertEqual(rows[0]["time_text"], "19:00")
        self.assertEqual(rows[1]["date_text"], "11/11")

    def test_own_ssm_parameters_and_does_not_expose_private_metadata(self):
        url = "https://example.org/private/feed?token=topsecret"
        ssm = FakeSSM({"/led/cubs/programme-ics-url": url})
        provider = CubsCalendarProvider(
            "/led/cubs/programme-ics-url", ssm=ssm,
            opener=lambda request, timeout: FakeResponse(url, ICS),
            utcnow=lambda: NOW,
        )
        rows = provider.fetch()
        self.assertEqual(len(rows), 2)
        self.assertEqual(ssm.calls, [{"Name": "/led/cubs/programme-ics-url", "WithDecryption": True}])
        self.assertNotIn("topsecret", str(rows))
        self.assertNotIn("Private Scout Hall", str(rows))

    def test_runtime_defaults_validation_and_old_configs(self):
        cfg = default_runtime_config({})
        self.assertEqual(cfg["feeds"]["cubs"], {
            "enabled": False, "poll_seconds": 86400,
            "screen_duration_seconds": 10, "intro_text": "Be prepared...",
            "schedule_windows": [],
        })
        schema = schema_metadata()["feeds"]["cubs"]["fields"]
        self.assertEqual(schema["poll_seconds"]["minimum"], 3600)
        self.assertEqual(schema["poll_seconds"]["maximum"], 604800)
        self.assertEqual(schema["intro_text"]["maximumLength"], 48)
        self.assertEqual(validate_feed_patch("cubs", {
            "intro_text": "Be Prepared for Adventure", "poll_seconds": 3600,
        }), {"intro_text": "Be Prepared for Adventure", "poll_seconds": 3600})
        for invalid in ("", "bad\ntext", "x" * 49, True):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("cubs", {"intro_text": invalid})
        for invalid in (0, 3599, 604801, True):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("cubs", {"poll_seconds": invalid})
        legacy = copy.deepcopy(cfg)
        legacy["feeds"]["cubs"].pop("intro_text")
        legacy["feeds"]["cubs"]["visible_event_count"] = 6
        migrated = validate_runtime_config(legacy)["feeds"]["cubs"]
        self.assertEqual(migrated["intro_text"], "Be prepared...")
        self.assertNotIn("visible_event_count", migrated)
        del cfg["feeds"]["cubs"]
        self.assertEqual(validate_runtime_config(cfg)["feeds"]["cubs"]["poll_seconds"], 86400)

    def test_independent_publisher_refresh_and_two_column_next_events(self):
        cfg = default_runtime_config({})
        cfg["feeds"]["cubs"]["enabled"] = True
        cfg["feeds"]["cubs"]["intro_text"] = "Be Prepared for Adventure!"
        for name in ("departures", "weather", "thorpe_park", "chessington"):
            cfg["feeds"][name]["enabled"] = False
        store = MemoryStore()
        cubs_events = [{
            "start": (NOW + timedelta(days=n)).date().isoformat(),
            "all_day": True, "date_text": "01/11", "time_text": "",
            "title": f"Cubs Meeting {n}",
            "location": "Private place", "description": "Private content",
        } for n in range(8)]
        beavers_events = [{
            "start": (NOW + timedelta(days=n)).date().isoformat(),
            "all_day": True, "date_text": "01/11", "time_text": "",
            "title": f"Beavers Meeting {n}",
            "location": "Private place", "description": "Private content",
        } for n in range(8)]
        cubs_provider = FakeProvider(cubs_events)
        beavers_provider = FakeProvider(beavers_events)
        current = [NOW]
        kwargs = dict(
            config=PublisherConfig(bucket="test", national_rail_token="dummy",
                                   thorpe_park_source="off", weather_source="off"),
            store=store, cubs_provider=cubs_provider, beavers_provider=beavers_provider,
            runtime_config_store=StaticRuntimeConfigStore(cfg),
            utcnow=lambda: current[0],
        )
        first = Publisher(**kwargs).run()
        scout_index = next(i for i, s in enumerate(first["screens"]) if s["id"] == "scouts-intro")
        intro, board = first["screens"][scout_index:scout_index + 2]
        self.assertEqual(intro["kind"], "scouts_intro")
        self.assertEqual(intro["intro_text"], "Be Prepared for Adventure!")
        self.assertEqual(board["id"], "cubs")
        self.assertEqual(board["kind"], "scouts_next_events")
        self.assertEqual(board["beavers"]["title"], "Beavers Meeting 0")
        self.assertEqual(board["cubs"]["title"], "Cubs Meeting 0")
        self.assertEqual(board["beavers_status"], "available")
        self.assertEqual(board["cubs_status"], "available")
        self.assertEqual(board["duration_seconds"], 10)
        self.assertNotIn("events", board)
        self.assertFalse(board["stale"])
        self.assertNotIn("calendar", store.state["feeds"])
        self.assertEqual((cubs_provider.calls, beavers_provider.calls), (1, 1))
        self.assertNotIn("Private place", str(first))
        self.assertNotIn("Private content", str(first))
        current[0] += timedelta(hours=23)
        second = Publisher(**kwargs).run()
        board = next(s for s in second["screens"] if s["id"] == "cubs")
        self.assertEqual((cubs_provider.calls, beavers_provider.calls), (1, 1))
        self.assertEqual(board["beavers"]["title"], "Beavers Meeting 1")
        self.assertEqual(board["cubs"]["title"], "Cubs Meeting 1")
        current[0] += timedelta(hours=2)
        Publisher(**kwargs).run()
        self.assertEqual((cubs_provider.calls, beavers_provider.calls), (2, 2))

    def test_beavers_failure_does_not_hide_valid_cubs(self):
        cfg = default_runtime_config({})
        cfg["feeds"]["cubs"]["enabled"] = True
        for name in ("departures", "weather", "thorpe_park", "chessington"):
            cfg["feeds"][name]["enabled"] = False
        class FailingProvider:
            def fetch(self):
                raise RuntimeError("Upstream URL intentionally not available")
        cubs = FakeProvider([{
            "start": (NOW + timedelta(days=1)).date().isoformat(),
            "all_day": True, "date_text": "28/10",
            "time_text": "", "title": "Cub hike",
        }])
        first = Publisher(
            PublisherConfig(bucket="test", national_rail_token="dummy",
                            thorpe_park_source="off", weather_source="off"),
            MemoryStore(), cubs_provider=cubs, beavers_provider=FailingProvider(),
            runtime_config_store=StaticRuntimeConfigStore(cfg), utcnow=lambda: NOW
        ).run()
        board = next(s for s in first["screens"] if s["kind"] == "scouts_next_events")
        self.assertIsNone(board["beavers"])
        self.assertEqual(board["beavers_status"], "unavailable")
        self.assertEqual(board["cubs"]["title"], "Cub hike")
        self.assertEqual(board["cubs_status"], "available")
        self.assertTrue(board["stale"])

    def test_publisher_default_beavers_parameter_names(self):
        config = PublisherConfig.from_env({
            "STATE_BUCKET": "test", "NATIONAL_RAIL_TOKEN": "dummy",
            "CUBS_PROGRAMME_PARAMETER_NAME": "/led/cubs/programme-ics-url",
            "CUBS_EVENTS_PARAMETER_NAME": "/led/cubs/events-ics-url",
            "BEAVERS_PROGRAMME_PARAMETER_NAME": "/led/beavers/programme-ics-url",
            "BEAVERS_EVENTS_PARAMETER_NAME": "/led/beavers/events-ics-url",
        })
        self.assertEqual(config.beavers_programme_parameter, "/led/beavers/programme-ics-url")
        self.assertEqual(config.beavers_events_parameter, "/led/beavers/events-ics-url")
        self.assertEqual(config.cubs_programme_parameter, "/led/cubs/programme-ics-url")


if __name__ == "__main__":
    unittest.main()
