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
            "screen_duration_seconds": 10, "visible_event_count": 6,
        })
        self.assertEqual(schema_metadata()["feeds"]["cubs"]["fields"]["poll_seconds"]["maximum"], 604800)
        self.assertEqual(validate_feed_patch("cubs", {"visible_event_count": 12, "poll_seconds": 3600}),
                         {"visible_event_count": 12, "poll_seconds": 3600})
        for invalid in (0, 13, True):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("cubs", {"visible_event_count": invalid})
        for invalid in (3599, 604801):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("cubs", {"poll_seconds": invalid})
        del cfg["feeds"]["cubs"]
        self.assertEqual(validate_runtime_config(cfg)["feeds"]["cubs"]["poll_seconds"], 86400)

    def test_independent_publisher_refresh_and_pagination(self):
        cfg = default_runtime_config({})
        cfg["feeds"]["cubs"]["enabled"] = True
        cfg["feeds"]["cubs"]["visible_event_count"] = 5
        cfg["feeds"]["departures"]["enabled"] = False
        cfg["feeds"]["weather"]["enabled"] = False
        cfg["feeds"]["thorpe_park"]["enabled"] = False
        cfg["feeds"]["chessington"]["enabled"] = False
        store = MemoryStore()
        events = [{
            "start": (NOW + timedelta(days=n)).date().isoformat(),
            "all_day": True, "date_text": "01/11", "time_text": "", "title": f"Meeting {n}",
            "location": "Private meeting place", "description": "Private agenda content",
        } for n in range(8)]
        provider = FakeProvider(events)
        current = [NOW]
        kwargs = dict(
            config=PublisherConfig(bucket="test", national_rail_token="dummy",
                                   thorpe_park_source="off", weather_source="off"),
            store=store, cubs_provider=provider,
            runtime_config_store=StaticRuntimeConfigStore(cfg),
            utcnow=lambda: current[0],
        )
        first = Publisher(**kwargs).run()
        cubs = next(item for item in first["screens"] if item["id"] == "cubs")
        self.assertEqual(cubs["source"], "cubs_ics")
        self.assertEqual(cubs["title"], "CUBS")
        self.assertEqual(cubs["viewport_size"], 3)
        self.assertEqual(len(cubs["events"]), 5)
        self.assertGreater(cubs["duration_seconds"], 10)
        self.assertFalse(cubs["stale"])
        self.assertNotIn("calendar", store.state["feeds"])
        self.assertEqual(provider.calls, 1)
        current[0] += timedelta(hours=23)
        updated = Publisher(**kwargs).run()
        updated_rows = next(s for s in updated["screens"] if s["id"] == "cubs")["events"]
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(updated_rows), 5)
        self.assertNotIn("Meeting 0", [e["title"] for e in updated_rows])
        self.assertNotIn("Private meeting place", str(updated_rows))
        self.assertNotIn("Private agenda content", str(updated_rows))
        current[0] += timedelta(hours=2)
        Publisher(**kwargs).run()
        self.assertEqual(provider.calls, 2)


if __name__ == "__main__":
    unittest.main()
