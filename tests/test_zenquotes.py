"""ZenQuotes #229: contracts for API batches, caching, rotation and screen layout."""

import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
import random
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for source in ("backend", "shared", "hardware/matrixportal/firmware"):
    sys.path.insert(0, str(ROOT / source))
sys.modules.setdefault("board", types.SimpleNamespace(GP0=0))

from zenquotes import ZenQuotesProvider
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore, content_version
from runtime_config import default_runtime_config, schema_metadata, validate_feed_patch, validate_runtime_config
from screen_client import ScreenRotation
from display import _quote_lines, _quote_page, FixtureDisplay


class MemoryStore:
    def __init__(self):
        self.state = {"version": 2, "feeds": {}}
        self.payload = None

    def load(self):
        return copy.deepcopy(self.state)

    def save(self, state):
        self.state = copy.deepcopy(state)

    def publish(self, payload):
        self.payload = copy.deepcopy(payload)


class QuotesProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def fetch(self):
        index = self.calls
        self.calls += 1
        value = self.responses[index]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


def quotes_screen(payload):
    return next(s for s in payload["screens"] if s["kind"] == "quotes")


class ZenQuotesTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)
        self.runtime = default_runtime_config({
            "LED_WEATHER_SOURCE": "off",
            "LED_THORPE_PARK_SOURCE": "off",
            "LED_CALENDAR_SOURCE": "off",
        })
        self.runtime["feeds"]["departures"]["enabled"] = False
        self.store = MemoryStore()

    def publisher(self, provider):
        return Publisher(PublisherConfig(bucket="test", national_rail_token="unused"),
                         self.store, runtime_config_store=StaticRuntimeConfigStore(self.runtime),
                         utcnow=lambda: self.now, quotes_provider=provider)

    def test_batch_provider_ignores_html_normalises_and_deduplicates(self):
        payload = b'[{"q":"Don\\u2019t panic","a":"An Author","h":"<script>alert(1)</script>"},' \
                  b'{"q":"Don\\u2019t panic","a":"An Author"},' \
                  b'{"q":"Second text","a":"Someone Else"},' \
                  b'{"q":"","a":"Nobody"},{"q":"Hello","a":""}]'
        with patch("zenquotes.urlopen", return_value=BytesIO(payload)) as opener:
            result = ZenQuotesProvider().fetch()
        self.assertEqual(result, [
            {"quote": "Don't panic", "author": "An Author"},
            {"quote": "Second text", "author": "Someone Else"},
        ])
        self.assertEqual(opener.call_args.kwargs["timeout"], 5)
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, "https://zenquotes.io/api/quotes")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertNotIn("h", result[0])

    def test_invalid_empty_batches_are_rejected(self):
        for payload in (b"{}", b"[]", b'[{"q":"","a":"Nobody"}]',
                        b'[{"q":"<b>html</b>","a":"Nobody"}]'):
            with self.subTest(payload=payload), patch("zenquotes.urlopen", return_value=BytesIO(payload)):
                with self.assertRaises(ValueError):
                    ZenQuotesProvider().fetch()

    def test_configuration_is_additive_disabled_and_editable(self):
        config = self.runtime
        self.assertFalse(config["feeds"]["quotes"]["enabled"])
        self.assertEqual(config["feeds"]["quotes"]["poll_seconds"], 7200)
        self.assertEqual(config["feeds"]["quotes"]["screen_duration_seconds"], 30)
        schema = schema_metadata()["feeds"]["quotes"]
        self.assertEqual(schema["display_group"], "static_feeds")
        self.assertEqual(schema["mutable_fields"],
                         ["enabled", "poll_seconds", "screen_duration_seconds"])
        old = copy.deepcopy(config)
        del old["feeds"]["quotes"]
        del old["feeds"]["insult_of_hour"]
        migrated = validate_runtime_config(old)
        self.assertFalse(migrated["feeds"]["quotes"]["enabled"])
        self.assertFalse(migrated["feeds"]["insult_of_hour"]["enabled"])
        with self.assertRaises(ValueError):
            validate_feed_patch("quotes", {"poll_seconds": 0})
        with self.assertRaises(ValueError):
            validate_feed_patch("quotes", {"screen_duration_seconds": 999})

    def test_one_batch_fills_pool_no_request_per_rotation(self):
        self.runtime["feeds"]["quotes"]["enabled"] = True
        provider = QuotesProvider([[{"quote": "Quote %s" % i, "author": "Author %s" % i} for i in range(50)]])
        publisher = self.publisher(provider)
        payload = publisher.run()
        screen = quotes_screen(payload)
        self.assertEqual(screen["duration_seconds"], 30)
        self.assertEqual(screen["source_url"], "https://zenquotes.io/")
        self.assertEqual(screen["display_group"], "static_feeds")
        self.assertEqual(len(screen["items"]), 50)
        self.assertEqual(provider.calls, 1)
        rotation = ScreenRotation(rng=random.Random(16))
        rotation.update([screen], 0)
        choices = []
        for step in range(10):
            selected, _ = rotation.current(step * 30)
            choices.append(selected["content_version"])
            if step:
                self.assertNotIn(choices[-1], choices[max(0, step-5):step])
        self.assertEqual(provider.calls, 1)
        self.now += timedelta(seconds=7199)
        publisher.run()
        self.assertEqual(provider.calls, 1)

    def test_refresh_and_failure_keep_last_good_batch(self):
        self.runtime["feeds"]["quotes"]["enabled"] = True
        provider = QuotesProvider([
            [{"quote": "First", "author": "A"}, {"quote": "Second", "author": "B"}],
            [{"quote": "Third", "author": "C"}],
            RuntimeError("HTTP 429"),
        ])
        publisher = self.publisher(provider)
        first = quotes_screen(publisher.run())
        self.assertEqual(len(first["items"]), 2)
        self.now += timedelta(seconds=7201)
        second = quotes_screen(publisher.run())
        self.assertEqual([item["quote"] for item in second["items"]], ["Third"])
        self.now += timedelta(seconds=7201)
        stale = quotes_screen(publisher.run())
        self.assertTrue(stale["stale"])
        self.assertEqual(stale["items"], second["items"])
        self.assertEqual(provider.calls, 3)
        self.now += timedelta(seconds=10)
        publisher.run()
        self.assertEqual(provider.calls, 3)

    def test_cold_failure_is_throttled(self):
        self.runtime["feeds"]["quotes"]["enabled"] = True
        provider = QuotesProvider([TimeoutError("timeout"), [{"quote": "Recovered", "author": "A"}]])
        publisher = self.publisher(provider)
        self.assertFalse(any(s["kind"] == "quotes" for s in publisher.run()["screens"]))
        self.now += timedelta(seconds=15)
        publisher.run()
        self.assertEqual(provider.calls, 1)
        self.now += timedelta(seconds=300)
        self.assertEqual(quotes_screen(publisher.run())["quote"], "Recovered")

    def test_versions_identify_quote_author_and_survive_polls(self):
        first = {"quote": "Same", "author": "A"}
        second = {"quote": "Same", "author": "B"}
        self.assertNotEqual(content_version("quotes", {"data": first}),
                            content_version("quotes", {"data": second}))
        screen = {"id": "quotes", "kind": "quotes", "duration_seconds": 30,
                  "items": [dict(first, content_version=content_version("quotes", {"data": first}))]}
        rotation = ScreenRotation(rng=random.Random(2))
        rotation.update([screen], 100)
        replacement = copy.deepcopy(screen)
        replacement["items"] = [dict(second, content_version=content_version("quotes", {"data": second}))]
        rotation.update([replacement], 110)
        selected, _ = rotation.current(110)
        self.assertEqual((selected["quote"], selected["author"]), ("Same", "A"))

    def test_fixture_renderer_displays_quote_author_credit_and_stale_marker(self):
        class CapturingFixture(FixtureDisplay):
            def __init__(self):
                self.labels = []

            def _text(self, label, x, y, color):
                self.labels.append((label, x, y, color))

        fixture = CapturingFixture()
        fixture._draw_screen({
            "kind": "quotes", "quote": "Keep learning",
            "author": "Sample Author", "stale": True,
        }, 0)
        labels = [label for label, _, _, _ in fixture.labels]
        self.assertIn("QUOTES VIA ZENQUOTES.IO STALE", labels)
        self.assertIn("Keep learning", labels)
        self.assertIn("- Sample Author", labels)

    def test_multiline_quote_author_and_attribution(self):
        screen = {"kind": "quotes", "duration_seconds": 30,
                  "quote": "Some very thoughtful words " * 12,
                  "author": "An author with an unusually long name " * 3}
        lines = _quote_lines(screen)
        self.assertGreater(len(lines), 3)
        self.assertTrue(all(len(line) <= 42 for line in lines))
        pages = (len(lines) + 2) // 3
        gathered = []
        for page in range(pages):
            gathered.extend(_quote_page(screen, (page + .1) * 30 / pages))
        self.assertEqual(gathered, lines)
        self.assertIn("- An author", " ".join(lines))
        self.assertIn("QUOTES VIA ZENQUOTES.IO", (ROOT / "hardware/matrixportal/firmware/display.py").read_text())
        self.assertIn('href="https://zenquotes.io/"', (ROOT / "simulator/index.html").read_text())
        self.assertIn("card('quotes')", (ROOT / "simulator/admin.html").read_text())
        self.assertIn('backend/zenquotes.py', (ROOT / "scripts/package-lambda.sh").read_text())


if __name__ == "__main__":
    unittest.main()
