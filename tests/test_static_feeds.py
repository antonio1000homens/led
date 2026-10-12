"""Static-feed pool, maintenance-window and renderer regression tests."""
import ast
import copy
import contextlib
from datetime import datetime, timedelta, timezone
import io
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time
import types
import unittest
from unittest.mock import Mock, patch

from publisher import Publisher, PublisherConfig, S3StateStore, StaticRuntimeConfigStore, content_version
from runtime_config import default_runtime_config, schema_metadata, validate_runtime_config
from screen_client import ScreenClient, ScreenRotation
from test_publisher import MemoryStore, FakeProvider, weather_payload
from test_matrix_todoist_performance import fake_modules, todoist_screen
import display as led_display

ROOT = Path(__file__).resolve().parents[1]


class PoolStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.consumed = set()

    def displayed(self, feed_id, version):
        return (feed_id, version) in self.consumed

    def acknowledgement(self, feed_id, version):
        return "https://example.invalid/" + feed_id + "/" + version


class StaticFeedTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, tzinfo=timezone.utc)
        self.runtime = default_runtime_config({"LED_WEATHER_SOURCE":"off", "LED_THORPE_PARK_SOURCE":"off"})
        self.runtime["feeds"]["departures"]["enabled"] = False
        self.store = PoolStore()

    def publisher(self, **kwargs):
        return Publisher(PublisherConfig(bucket="test", national_rail_token="unused"), self.store,
                         runtime_config_store=StaticRuntimeConfigStore(self.runtime),
                         utcnow=lambda:self.now, **kwargs)

    def test_pool_fills_gradually_and_replaces_only_consumed_item_before_ttl(self):
        self.runtime["feeds"]["dad_joke"]["enabled"] = True
        provider = FakeProvider(["Joke {}".format(i) for i in range(20)])
        publisher = self.publisher(joke_provider=provider)
        for size in (2,4,5):
            payload = publisher.run()
            self.assertEqual(len(payload["screens"][0]["items"]), size)
            self.now += timedelta(seconds=61)
        original = copy.deepcopy(self.store.state["feeds"]["dad_joke"]["items"])
        version = content_version("dad_joke", {"data":original[1]})
        self.store.consumed.add(("dad_joke",version))
        publisher.run()
        after = self.store.state["feeds"]["dad_joke"]["items"]
        self.assertEqual(len(after),5)
        self.assertNotIn(original[1],after)
        self.assertTrue(all(item in after for index,item in enumerate(original) if index!=1))
        self.assertEqual(provider.calls,6)
        # Replayed acknowledgement for removed content cannot consume a newer item.
        self.now += timedelta(seconds=61)
        publisher.run()
        self.assertEqual(provider.calls,6)

    def test_failed_replenishment_keeps_entire_pool_and_retries_are_bounded(self):
        self.runtime["feeds"]["dad_joke"]["enabled"] = True
        provider = FakeProvider(["A", "B", RuntimeError("offline")])
        publisher = self.publisher(joke_provider=provider)
        publisher.run()
        before = copy.deepcopy(self.store.state["feeds"]["dad_joke"]["items"])
        self.now += timedelta(seconds=61)
        publisher.run()
        self.assertEqual(self.store.state["feeds"]["dad_joke"]["items"],before)
        self.assertTrue(self.store.state["feeds"]["dad_joke"]["stale"])
        self.now += timedelta(seconds=10)
        publisher.run()
        self.assertEqual(provider.calls,3)

    def test_today_uses_shared_weather_even_when_forecast_screens_disabled(self):
        self.runtime["feeds"]["today"]["enabled"] = True
        weather = FakeProvider([weather_payload()])
        payload = self.publisher(weather_provider=weather).run()
        self.assertEqual(weather.calls,1)
        self.assertEqual([screen["kind"] for screen in payload["screens"]],["today"])
        self.assertEqual(payload["screens"][0]["weather"]["temperature_c"],17.4)
        self.assertEqual(payload["screens"][0]["display_group"],"static_feeds")

    def test_admin_group_and_retired_frequency_migration(self):
        config = copy.deepcopy(self.runtime)
        del config["feeds"]["today"]
        for feed in config["feeds"].values():
            feed["display_every_cycles"] = 4
        migrated = validate_runtime_config(config)
        self.assertIn("today",migrated["feeds"])
        self.assertTrue(all("display_every_cycles" not in feed for feed_id, feed in migrated["feeds"].items() if feed_id != "sl7_bus"))
        self.assertEqual(migrated["feeds"]["sl7_bus"]["display_every_cycles"], 4)
        schema = schema_metadata()
        for kind in ("dad_joke","random_fact","today"):
            self.assertEqual(schema["feeds"][kind]["display_group"],"static_feeds")
        html = (ROOT / "simulator/admin.html").read_text()
        self.assertIn("<h2>Static feeds</h2>",html)
        self.assertNotIn("display_every_cycles",html)

    def test_acknowledgement_capability_is_scoped_to_item_and_fixed_size(self):
        client = Mock()
        store = S3StateStore("test",client=client)
        store.acknowledgement("random_fact","version")
        arguments = client.generate_presigned_url.call_args
        self.assertEqual(arguments.args,("put_object",))
        self.assertEqual(arguments.kwargs["Params"]["Key"],"state/displayed/random_fact/version.json")
        self.assertEqual(arguments.kwargs["Params"]["ContentLength"],2)
        self.assertEqual(arguments.kwargs["ExpiresIn"],3600)

    def test_acknowledgement_closes_response_on_failure(self):
        client = ScreenClient(Mock(), session=Mock())
        response = client.session.put.return_value
        response.status_code = 403
        with self.assertRaises(ValueError):
            client.acknowledge("https://example.invalid")
        response.close.assert_called_once()

    def test_marker_contents_are_not_trusted_or_parsed(self):
        client = Mock()
        store = S3StateStore("test",client=client)
        self.assertTrue(store.displayed("random_fact","version"))
        client.get_object.assert_not_called()
        class Missing(Exception):
            response = {"Error":{"Code":"404"}}
        client.head_object.side_effect = Missing()
        self.assertFalse(store.displayed("random_fact","version"))
        client.head_object.side_effect = RuntimeError("permission failure")
        with self.assertRaises(RuntimeError):
            store.displayed("random_fact","version")

    def test_real_sdk_signs_fixed_content_length_and_content_type(self):
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            self.skipTest("Optional deployment SDK not installed")
        from urllib.parse import urlparse, parse_qs
        client = boto3.client("s3",region_name="eu-west-2",config=Config(signature_version="s3v4"),
                              aws_access_key_id="test",aws_secret_access_key="test")
        url = S3StateStore("test",client=client).acknowledgement("random_fact","version")
        query = parse_qs(urlparse(url).query)
        self.assertEqual(query["X-Amz-SignedHeaders"],["content-length;content-type;host"])
        self.assertTrue(urlparse(url).path.endswith("/state/displayed/random_fact/version.json"))

    def test_shuffle_preserves_train_pair_normal_order_and_every_screen(self):
        screens = [{"id":"train","kind":"steam_train_intro"},
                   {"id":"rail","kind":"rail_combined"},
                   {"id":"queue","kind":"theme_park_queues"},
                   {"id":"joke","kind":"dad_joke"},
                   {"id":"fact","kind":"random_fact"},
                   {"id":"today","kind":"today"}]
        arrangements = set()
        for seed in range(30):
            rotation = ScreenRotation(rng=random.Random(seed))
            rotation.update(screens,0)
            ids = [screen["id"] for screen in rotation.screens]
            arrangements.add(tuple(ids))
            self.assertEqual(sorted(ids),sorted(screen["id"] for screen in screens))
            self.assertEqual([id for id in ids if id in ("train","rail","queue")],["train","rail","queue"])
            self.assertEqual(ids.index("rail"),ids.index("train")+1)
        self.assertGreater(len(arrangements),1)

    def test_poll_preserves_selected_item_phase_and_plan(self):
        rotation = ScreenRotation(ticks_per_second=1000,rng=random.Random(3))
        screen = {"id":"fact","kind":"random_fact","duration_seconds":2,
                  "items":[{"fact":"A","content_version":"a","refresh_ack_url":"old"}]}
        aged = 500_000_000
        rotation.update([screen],aged)
        selected,phase = rotation.freeze(aged+375)
        changed = copy.deepcopy(screen)
        changed["items"][0]["refresh_ack_url"] = "renewed"
        changed["items"].append({"fact":"B","content_version":"b"})
        rotation.update([changed,{"id":"added","duration_seconds":2}],aged+5000)
        rotation.resume(aged+5000,selected,phase)
        current,phase = rotation.current(aged+5000)
        self.assertEqual((current["fact"],phase),("A",0.375))
        self.assertEqual(current["refresh_ack_url"],"renewed")
        self.assertEqual(len(rotation.screens),1)
        rotation.current(aged+7000)
        self.assertEqual(len(rotation.screens),2)

    def test_maintenance_repeat_does_not_advance_cycle_or_skip_normal_screen(self):
        rotation = ScreenRotation(ticks_per_second=1000)
        rotation.update([{"id":"rail","duration_seconds":2}],500_000_000)
        rotation.maintenance_slot(500_000_000)
        static,phase = rotation.freeze(500_000_375)
        rotation.resume(500_010_000,static,phase)
        self.assertEqual(rotation.current(500_010_000)[1],0.375)
        self.assertEqual(rotation.current(500_017_625)[0]["id"],"rail")
        self.assertEqual(rotation.cycle_number,0)
        self.assertIsInstance(rotation.started_at,int)

    def test_explicit_gc_occurs_only_after_static_is_presented(self):
        source = (ROOT / "code.py").read_text()
        self.assertEqual(source.count("gc.collect()"),1)
        block = source[source.index("    if maintenance_visible and"):source.index("    should_fetch = (fetch_due")]
        self.assertLess(block.index("display.show("),block.index("gc.collect()"))
        self.assertIn("not flash.active(now)",block)
        self.assertNotIn("display.show_loading",source)
        ast.parse(source)

    @unittest.skipUnless(shutil.which("node"),"Node is required for browser scheduler tests")
    def test_browser_scripts_parse_and_pool_selection_repeats_without_suppression(self):
        for filename in ("index.html","admin.html"):
            html = (ROOT / "simulator" / filename).read_text()
            script = re.search(r"<script>([\s\S]*?)</script>",html).group(1)
            subprocess.run(["node","--check"],input=script,text=True,check=True,capture_output=True)
        html = (ROOT / "simulator/index.html").read_text()
        code = html[html.index("    let cyclePlan"):html.index("    function stationMarqueeSpeed")]
        test = """
const screens=[{id:'fact',kind:'random_fact',duration_seconds:2,items:[{fact:'A',content_version:'a'},{fact:'B',content_version:'b'}]}];
let screenOffset=0;
const first=screenAt(0).screen.fact;
if(screenAt(2000).screen.fact===first)throw Error('repeated pool item');
if(screenAt(4000).screen.id!=='fact')throw Error('suppressed page');
"""
        # Functions access screens only on invocation, after the fixture exists.
        subprocess.run(["node"],input=code+test,text=True,check=True,capture_output=True)

    def test_sl7_maintenance_guard_and_simulator_pairing(self):
        source = (ROOT / "code.py").read_text()
        self.assertIn("rotation.is_paired_transition(last_visible_screen, candidate)", source)
        self.assertIn("and boundary and not paired_followup", source)
        html = (ROOT / "simulator/index.html").read_text()
        script = html[html.index("    let cyclePlan"):html.index("    function stationMarqueeSpeed")]
        if not shutil.which("node"):
            self.skipTest("Node is required for browser scheduler tests")
        test = """
const screens=[
  {id:'sl7-heathrow-intro',kind:'bus_intro',stop_key:'heathrow'},
  {id:'sl7-heathrow',kind:'bus_departures',stop_key:'heathrow'},
  {id:'sl7-new-malden-intro',kind:'bus_intro',stop_key:'new-malden'},
  {id:'sl7-new-malden',kind:'bus_departures',stop_key:'new-malden'},
  {id:'fact',kind:'random_fact'},
  {id:'joke',kind:'dad_joke'}
];
for(let i=0;i<50;i++){
  const plan=makeCyclePlan();
  for(const stop of ['heathrow','new-malden']){
    const at=plan.findIndex(s=>s.id==='sl7-'+stop+'-intro');
    if(at<0 || plan[at+1]?.id!=='sl7-'+stop)throw Error('SL7 pair split: '+stop);
  }
}
screens.splice(1,1);
if(makeCyclePlan().some(s=>s.id==='sl7-heathrow-intro'))throw Error('orphan intro');
"""
        subprocess.run(["node"], input=script+test, text=True, check=True, capture_output=True)

    def test_static_scene_is_cached_and_task_preparation_does_not_publish(self):
        led_display.board.MTX_ADDRESS = (0,1,2,3)
        led_display.board.MTX_COMMON = {}
        with patch.dict(sys.modules,fake_modules()):
            display = led_display.MatrixDisplay()
            static = {"id":"fact","kind":"random_fact","fact":"A fact","duration_seconds":10}
            display.show(static,phase=0)
            root = display.display.root_group
            assignments = display.display.root_assignments
            display.show(copy.deepcopy(static),phase=0.5)
            self.assertIs(display.display.root_group,root)
            self.assertEqual(display.display.root_assignments,assignments)
            task = todoist_screen()
            display.prepare_tasks(task,"12:00","2026-10-11")
            self.assertTrue(display.tasks_ready(task,"2026-10-11"))
            self.assertIs(display.display.root_group,root)
            previous = display._todoist_group
            def broken(*args):
                display._todoist_group = None
                raise MemoryError("test")
            with patch.object(display,"_build_todoist_scene",side_effect=broken):
                with self.assertRaises(MemoryError):
                    display.prepare_tasks(todoist_screen(10),"12:00","2026-10-11")
            self.assertIs(display._todoist_group,previous)
            self.assertTrue(display.tasks_ready(task,"2026-10-11"))

    def test_entrypoint_keeps_blocking_work_on_static_pages_over_multiple_cycles(self):
        import gc
        import queue_display
        import screen_client
        import settings
        class Finished(BaseException):
            pass
        milliseconds = [500_000_000]
        started = milliseconds[0]
        shown = []
        work = []
        settings_copy = types.SimpleNamespace(**{name:getattr(settings,name) for name in dir(settings) if name.isupper()})
        settings_copy.DISPLAY_BACKEND = "fixture"
        settings_copy.SCREEN_SOURCE = "api"
        settings_copy.MQTT_ENABLED = False
        settings_copy.POLL_SECONDS = 10
        settings_copy.ANIMATE = True
        def advance(seconds):
            milliseconds[0] += max(1,int(round(seconds*1000)))
            if milliseconds[0]-started > 90_000:
                raise Finished()
        class Display:
            def __init__(self):
                self.events = None
            def show(self,screen,clock_time="",clock_date="",phase=0):
                shown.append((screen["kind"],phase,milliseconds[0]))
            def tasks_ready(self,screen,clock_date=""):
                return self.events == screen.get("events")
            def prepare_tasks(self,screen,*args):
                if not self.tasks_ready(screen):
                    self.blocking("prepare")
                    advance(2)
                    self.events = copy.deepcopy(screen["events"])
            def blocking(self,operation):
                if not shown or shown[-1][0] not in ("today","dad_joke","random_fact"):
                    raise AssertionError(operation+" interrupted a moving screen")
                work.append(operation)
            def animation_cadence(self,screen,phase):
                return 8
            def animation_active(self,screen,phase):
                return not ScreenRotation.is_static(screen)
            def animation_sleep_seconds(self,screen,phase):
                return 1 if ScreenRotation.is_static(screen) else None
        display = Display()
        class Client:
            def __init__(self,*args):
                self.fetches = 0
            def fetch(self):
                display.blocking("fetch")
                advance(3)
                self.fetches += 1
                return {"fetched_at":"2026-10-11T12:00:00Z","screens":[
                    {"id":"steam-train","kind":"steam_train_intro","duration_seconds":2},
                    {"id":"departures","kind":"rail_combined","duration_seconds":2},
                    {"id":"queue","kind":"theme_park_queues","duration_seconds":2},
                    {"id":"calendar","kind":"calendar_agenda","source":"todoist","duration_seconds":2,
                     "events":[{"title":"Task "+str(self.fetches)}]},
                    {"id":"fact","kind":"random_fact","duration_seconds":4,
                     "items":[{"fact":"A","content_version":"a","refresh_ack_url":"url"}]},
                ]}
            def acknowledge(self,url):
                display.blocking("acknowledge")
                advance(1)
        namespace = {"__name__":"static_feed_entrypoint_test"}
        modules = {"settings":settings_copy,"settings_local":types.SimpleNamespace()}
        with patch.dict(sys.modules,modules), patch.object(queue_display,"create",return_value=display), \
             patch.object(screen_client,"ScreenClient",Client), \
             patch.object(time,"monotonic",side_effect=lambda:milliseconds[0]/1000), \
             patch.object(time,"monotonic_ns",side_effect=lambda:milliseconds[0]*1_000_000), \
             patch.object(time,"sleep",side_effect=advance), \
             patch.object(gc,"collect",side_effect=lambda:display.blocking("gc")), \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Finished):
                exec(compile((ROOT/"code.py").read_text(),"code.py","exec"),namespace)
        self.assertGreater(work.count("fetch"),3)
        self.assertIn("acknowledge",work)
        self.assertIn("prepare",work)
        self.assertIn("gc",work)
        self.assertGreater(namespace["rotation"].cycle_number,1)
        self.assertIsInstance(namespace["next_fetch"],int)

