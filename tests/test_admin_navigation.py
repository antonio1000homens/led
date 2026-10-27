"""Regression coverage for the navigable static LED admin control plane (issue #274)."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN = (ROOT / "simulator" / "admin.html").read_text(encoding="utf-8")


class AdminNavigationTests(unittest.TestCase):
    def test_semantic_responsive_navigation_and_focus(self):
        for fragment in (
            'id="nav-panel"',
            'aria-label="Screen and maintenance sections"',
            'id="nav-toggle"',
            'aria-expanded="false"',
            'aria-controls="nav-panel"',
            'id="nav-search"',
            'id="nav-scrim"',
            'aria-current',
            '.nav-panel.is-open',
            '@media(max-width:840px)',
            "event.key==='Escape'",
            "navSearch.focus()",
            'heading.focus({preventScroll:true})',
            "function filterNavigation()",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, ADMIN)

    def test_deep_links_restore_after_auth_and_support_browser_history(self):
        for fragment in (
            'window.sessionStorage.setItem',
            'window.sessionStorage.getItem',
            "'/admin'+restoredHash",
            "'hashchange'",
            "hash==='insult-of-hour'",
            "function selectedKeyFromHash()",
            "function selectFromHash(focusHeading)",
            "link.setAttribute('aria-current','page')",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, ADMIN)

    def test_draft_persistence_and_concurrent_apply_guards(self):
        for fragment in (
            "function captureDirtyDrafts(excludeFeedId)",
            "function restoreDirtyDrafts(drafts)",
            "card.querySelectorAll('[data-schedule-windows]')",
            "card.dataset.queueGroup==='true'?queueMemberIds():[feedId]",
            "card.dataset.dirty='true'",
            "restoreDirtyDrafts(drafts)",
            "window.addEventListener('beforeunload'",
            "window.confirm('Discard unsaved screen changes",
            "'If-Match'",
            'response.status===412',
            "function collectQueueCard(card)",
            'data-window-unit',
            "function statusAfterSave()",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, ADMIN)

    def test_unknown_static_feed_still_uses_generic_card(self):
        self.assertIn("function navigationModel(config)", ADMIN)
        self.assertIn("'Other screens'", ADMIN)
        self.assertIn("&&['dad_joke','insult_of_hour','random_fact','quotes'].includes(feedId)", ADMIN)
        self.assertIn("return cardHtml(feedId,feed,schema,status?.feeds?.[feedId]);", ADMIN)
        self.assertIn("schema.provider==='queue_times'", ADMIN)
        self.assertIn("queueMemberIds().map(queueParkHtml)", ADMIN)

    def _run_navigation_model(self, code):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js not installed; markup and integration checks still run")
        start = ADMIN.index("function navigationModel(config){")
        end = ADMIN.index("function navigationHealth(entry){", start)
        script = ADMIN[start:end] + "\n" + code
        result = subprocess.run(
            [node, "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return json.loads(result.stdout)

    def _config_fixture(self):
        ids = (
            "departures", "steam_train", "sl7_bus", "weather", "today",
            "queue_times", "thorpe_park", "chessington", "calendar",
            "flash", "recycling", "dad_joke", "insult_of_hour",
            "random_fact", "quotes", "future_static_feed",
        )
        return {
            "feeds": {name: {"enabled": True} for name in ids},
            "schema": {
                "feeds": {
                    name: {
                        "label": name.replace("_", " ").title(),
                        "provider": "queue_times" if name in ("thorpe_park", "chessington") else "other",
                        "display_group": "static_feeds" if name == "future_static_feed" else "",
                    }
                    for name in ids
                }
            },
        }

    def test_model_builds_sections_and_preserves_unknown_feed(self):
        config = json.dumps(self._config_fixture())
        result = self._run_navigation_model(
            "const groups=navigationModel(" + config + ");"
            "console.log(JSON.stringify(groups));"
        )
        names = [group["label"] for group in result]
        self.assertIn("Overview", names)
        self.assertIn("Transport", names)
        self.assertIn("Theme parks", names)
        self.assertIn("Other screens", names)
        self.assertIn("Maintenance & diagnostics", names)
        lookup = {
            item["key"]: item
            for group in result
            for item in group["items"]
        }
        self.assertEqual(lookup["overview"]["feedIds"], [])
        self.assertEqual(lookup["maintenance"]["feedIds"], [])
        self.assertEqual(lookup["screen/departures"]["feedIds"], ["departures", "steam_train"])
        self.assertEqual(lookup["screen/thorpe_park"]["view"], "queue_times")
        self.assertEqual(lookup["screen/queue_times"]["feedIds"], [
            "queue_times", "thorpe_park", "chessington",
        ])
        self.assertEqual(lookup["screen/today"]["view"], "today")
        self.assertEqual(lookup["screen/weather-next-24-hours"]["view"], "weather")
        self.assertEqual(lookup["screen/future_static_feed"]["view"], "future_static_feed")

    def test_fragment_mapping_and_legacy_alias(self):
        config = json.dumps(self._config_fixture())
        start = ADMIN.index("function selectedKeyFromHash(){")
        end = ADMIN.index("function selectFromHash(focusHeading){", start)
        fragment_parser = ADMIN[start:end]
        body = (
            "const navItems=navigationModel(" + config + ").flatMap(g=>g.items);"
            "const window={location:{hash:''}};"
            + fragment_parser +
            "const hashes=['#screen/today','#screen/weather-next-24-hours',"
            "'#screen/future_static_feed','#insult-of-hour','#missing'];"
            "console.log(JSON.stringify(hashes.map(hash=>{window.location.hash=hash;"
            "return selectedKeyFromHash();})));"
        )
        self.assertEqual(
            self._run_navigation_model(body),
            [
                "screen/today",
                "screen/weather-next-24-hours",
                "screen/future_static_feed",
                "screen/insult_of_hour",
                "overview",
            ],
        )


if __name__ == "__main__":
    unittest.main()
