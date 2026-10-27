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

    def test_queue_health_is_unavailable_when_status_cannot_be_loaded(self):
        start = ADMIN.index("function queueMemberIds(){")
        end = ADMIN.index("function queueParkHtml(feedId){", start)
        functions = ADMIN[start:end]
        result = self._run_navigation_model(
            "const state={config:{schema:{feeds:{"
            "thorpe_park:{provider:'queue_times'},"
            "chessington:{provider:'queue_times'}"
            "}}},status:null};"
            + functions +
            "const states=[queueHealth()];"
            "state.status={feeds:{thorpe_park:{enabled:false},chessington:{enabled:false}}};"
            "states.push(queueHealth());"
            "state.status.feeds.thorpe_park={enabled:true,health:'stale'};"
            "states.push(queueHealth());"
            "state.status.feeds.thorpe_park.health='unavailable';"
            "states.push(queueHealth());"
            "state.status.feeds.thorpe_park.health='ok';"
            "states.push(queueHealth());"
            "console.log(JSON.stringify(states));"
        )
        self.assertEqual(result, ["unavailable", "disabled", "stale", "unavailable", "ok"])

    def test_failed_config_refresh_discards_stale_editable_controls(self):
        start = ADMIN.index("async function load(){")
        end = ADMIN.index("/* Navigation is derived", start)
        source = ADMIN[start:end]
        output = self._run_navigation_model(
            "const state={config:{config_version:99},status:{feeds:{}},selected:{old:['ride']}};"
            "let navItems=[{key:'screen/old'}];"
            "const cleared=[];"
            "const cards={setAttribute:(key,value)=>cleared.push(key+':'+value),"
            "replaceChildren:()=>cleared.push('cards')};"
            "const document={getElementById:(id)=>({"
            "replaceChildren:()=>cleared.push(id),"
            "set textContent(value){cleared.push(id+'='+value);}})};"
            "const health={innerHTML:''},diagnostics={textContent:''};"
            "let notice='';"
            "function clearNotice(){}"
            "function showNotice(message,level){notice=level+':'+message;}"
            "function render(){throw new Error('Stale controls must not render');}"
            "async function api(path){"
            "if(path==='/config')throw new Error('Config unavailable');"
            "return {data:{feeds:{}}};}"
            + source +
            "load().then(()=>console.log(JSON.stringify({"
            "config:state.config,status:state.status,selected:state.selected,"
            "navItems,cleared,notice,health:health.innerHTML})));"
        )
        self.assertIsNone(output["config"])
        self.assertIsNone(output["status"])
        self.assertEqual(output["selected"], {})
        self.assertEqual(output["navItems"], [])
        self.assertIn("cards", output["cleared"])
        self.assertIn("section-navigation", output["cleared"])
        self.assertIn("section-title=Configuration unavailable", output["cleared"])
        self.assertIn("Config unavailable", output["notice"])
        self.assertIn("unavailable", output["health"])

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
