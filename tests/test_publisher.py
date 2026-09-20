import copy
from datetime import datetime, timedelta, timezone
import unittest
from publisher import Publisher, PublisherConfig, StaticRuntimeConfigStore
from runtime_config import default_runtime_config


class MemoryStore:
    def __init__(self): self.state={"version":2,"feeds":{}}; self.payload=None
    def load(self): return copy.deepcopy(self.state)
    def save(self,state): self.state=copy.deepcopy(state)
    def publish(self,payload): self.payload=copy.deepcopy(payload)
class FakeProvider:
    source="fake"
    def __init__(self,results): self.results=list(results); self.calls=0
    def fetch(self):
        result=self.results[self.calls]; self.calls+=1
        if isinstance(result,Exception): raise result
        return copy.deepcopy(result)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,9,13,7,0,tzinfo=timezone.utc); self.utcnow=lambda:self.now; self.store=MemoryStore()
        self.config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_source="off",weather_source="off")
    def test_persists_cache_across_separate_publisher_instances(self):
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}]])
        Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow).run(); self.now+=timedelta(seconds=30)
        Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow).run()
        self.assertEqual(rail.calls,1); self.assertEqual(self.store.payload["screens"][0]["services"][0]["time"],"08:01")
        self.assertEqual(self.store.state["feeds"]["departures"]["last_success_at"],"2026-09-13T07:00:00Z")
    def test_refreshes_after_ttl_and_keeps_last_good_data_stale_on_failure(self):
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}],RuntimeError("upstream failure must not leak")])
        Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow).run(); self.now+=timedelta(seconds=61)
        payload=Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow).run()
        self.assertEqual(rail.calls,2); self.assertTrue(payload["screens"][0]["stale"]); self.assertEqual(payload["screens"][0]["services"][0]["destination"],"Waterloo")
    def test_cold_rail_failure_publishes_safe_unavailable_screen(self):
        payload=Publisher(self.config,self.store,rail_provider=FakeProvider([RuntimeError("sensitive response")]),utcnow=self.utcnow).run(); screen=payload["screens"][0]
        self.assertEqual(screen["source"],"unavailable"); self.assertTrue(screen["stale"]); self.assertEqual(screen["services"],[])
        self.assertIsNone(screen["empty_state"])
    def test_empty_departures_publish_no_services_page_for_configured_duration(self):
        runtime=default_runtime_config({"LED_THORPE_PARK_SOURCE":"off","LED_WEATHER_SOURCE":"off","LED_CALENDAR_SOURCE":"off"})
        runtime["feeds"]["departures"]["screen_duration_seconds"]=12
        runtime["feeds"]["departures"]["no_services_duration_seconds"]=5
        screen=Publisher(
            self.config,
            self.store,
            rail_provider=FakeProvider([[]]),
            utcnow=self.utcnow,
            runtime_config_store=StaticRuntimeConfigStore(runtime),
        ).run()["screens"][0]
        self.assertEqual(screen["services"],[])
        self.assertEqual(screen["empty_state"],"No Services")
        self.assertEqual(screen["duration_seconds"],5)
        self.assertFalse(screen["stale"])

    def test_departures_contract_publishes_current_and_configured_next_services(self):
        rail=FakeProvider([[
            {"time":"08:01","destination":"Waterloo"},
            {"time":"08:11","destination":"Waterloo"},
            {"time":"08:21","destination":"Waterloo"},
            {"time":"08:31","destination":"Waterloo"},
        ]])
        screen=Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow).run()["screens"][0]
        self.assertEqual([service["time"] for service in screen["services"]],["08:01","08:11","08:21","08:31"])
        self.assertEqual(screen["upcoming_train_count"], 4)
        self.assertEqual(screen["upcoming_train_pause_seconds"], 2)
        self.assertIsNone(screen["empty_state"])
    def test_queue_and_weather_ttls_are_independent_and_contract_is_preserved(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",rail_ttl=60,thorpe_park_ttl=300,weather_ttl=600,thorpe_park_rides=("Hyperia","Stealth","The Swarm","Colossus"))
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}],[{"time":"08:02"}]])
        rides=[{"name":name,"open":True,"wait_minutes":wait,"last_updated":"","land":""} for name,wait in (("Hyperia",25),("Stealth",10),("The Swarm",15),("Colossus",20))]
        queues=FakeProvider([rides]); chessington=FakeProvider([[{"name":"Mandrill Mayhem","open":True,"wait_minutes":30,"last_updated":"","land":""}]])
        weather=FakeProvider([{"temperature_c":17.4,"weather_code":2,"icon":"partly_cloudy_day","is_day":True,"attribution":"Weather data by Open-Meteo.com","attribution_url":"https://open-meteo.com/"}])
        first=Publisher(config,self.store,rail_provider=rail,queue_provider=queues,weather_provider=weather,utcnow=self.utcnow,chessington_provider=chessington).run(); self.now+=timedelta(seconds=61)
        second=Publisher(config,self.store,rail_provider=rail,queue_provider=queues,weather_provider=weather,utcnow=self.utcnow,chessington_provider=chessington).run()
        self.assertEqual(rail.calls,2); self.assertEqual(queues.calls,1); self.assertEqual(chessington.calls,1); self.assertEqual(weather.calls,1)
        self.assertEqual([s["id"] for s in first["screens"]],["departures","queue-times"])
        queue_screen=second["screens"][1]
        self.assertEqual(queue_screen["kind"],"theme_park_queues")
        self.assertEqual([park["feed_id"] for park in queue_screen["parks"]],["thorpe_park","chessington"])
        self.assertEqual([r["name"] for r in queue_screen["parks"][0]["rides"]],["Hyperia","Stealth","The Swarm","Colossus"])
        self.assertEqual(queue_screen["entries_per_page"],3); self.assertEqual(queue_screen["parks"][1]["rides"][0]["name"],"Mandrill Mayhem")
        for screen in second["screens"]: self.assertEqual(screen["weather"]["temperature_c"],17.4)
    def test_all_closed_queue_pages_are_omitted_per_park(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_rides=("Hyperia",),weather_source="off")
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}]])
        queues=FakeProvider([[{"name":"Hyperia","open":False,"wait_minutes":0,"last_updated":"","land":""}]])
        chessington=FakeProvider([[{"name":"Mandrill Mayhem","open":False,"wait_minutes":0,"last_updated":"","land":""}]])
        payload=Publisher(config,self.store,rail_provider=rail,queue_provider=queues,utcnow=self.utcnow,chessington_provider=chessington).run()
        self.assertEqual([screen["id"] for screen in payload["screens"]],["departures"])
    def test_closed_park_is_skipped_without_hiding_open_park(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_rides=("Hyperia",),weather_source="off")
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}]])
        queues=FakeProvider([[{"name":"Hyperia","open":False,"wait_minutes":0,"last_updated":"","land":""}]])
        chessington=FakeProvider([[{"name":"Mandrill Mayhem","open":True,"wait_minutes":15,"last_updated":"","land":""}]])
        payload=Publisher(config,self.store,rail_provider=rail,queue_provider=queues,utcnow=self.utcnow,chessington_provider=chessington).run()
        self.assertEqual([screen["id"] for screen in payload["screens"]],["departures","queue-times"])
        self.assertEqual([park["feed_id"] for park in payload["screens"][1]["parks"]],["chessington"])
    def test_calendar_has_independent_ttl_and_six_event_contract(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_source="off",weather_source="off",calendar_source="todoist",todoist_oauth_secret_arn="arn:test:todoist",calendar_ttl=300,calendar_max_events=6,calendar_duration=10,calendar_page_seconds=5)
        rail=FakeProvider([[{"time":"08:01","destination":"Waterloo"}],[{"time":"08:02"}]])
        events=[{"start":f"2026-09-{13+i:02d}T18:00:00+01:00","date_text":f"{13+i:02d}/09","time_text":"18:00","title":f"Event {i+1}"} for i in range(6)]; calendar=FakeProvider([events])
        first=Publisher(config,self.store,rail_provider=rail,utcnow=self.utcnow,calendar_provider=calendar).run(); self.now+=timedelta(seconds=61)
        second=Publisher(config,self.store,rail_provider=rail,utcnow=self.utcnow,calendar_provider=calendar).run(); screen=first["screens"][1]
        self.assertEqual(calendar.calls,1); self.assertEqual(screen["id"],"calendar"); self.assertEqual(screen["duration_seconds"],10); self.assertEqual(len(screen["events"]),6); self.assertFalse(second["screens"][1]["stale"])
    def test_calendar_keeps_cached_data_stale_after_failure(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_source="off",weather_source="off",calendar_source="todoist",todoist_oauth_secret_arn="arn:test:todoist",calendar_ttl=60)
        rail=FakeProvider([[{"time":"08:01"}],[{"time":"08:02"}]]); calendar=FakeProvider([[{"date_text":"13/09","time_text":"18:00","title":"Keep me"}],RuntimeError("private upstream error")])
        Publisher(config,self.store,rail_provider=rail,utcnow=self.utcnow,calendar_provider=calendar).run(); self.now+=timedelta(seconds=61)
        screen=Publisher(config,self.store,rail_provider=rail,utcnow=self.utcnow,calendar_provider=calendar).run()["screens"][1]
        self.assertTrue(screen["stale"]); self.assertEqual(screen["events"][0]["title"],"Keep me")
    def test_cold_calendar_failure_does_not_break_departures(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_source="off",weather_source="off",calendar_source="todoist",todoist_oauth_secret_arn="arn:test:todoist")
        payload=Publisher(config,self.store,rail_provider=FakeProvider([[{"time":"08:01","destination":"Waterloo"}]]),utcnow=self.utcnow,calendar_provider=FakeProvider([RuntimeError("private upstream error")])).run()
        self.assertEqual(payload["screens"][0]["source"],"national_rail"); self.assertEqual(payload["screens"][1]["source"],"unavailable")
    def test_empty_calendar_is_successful_not_stale(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",thorpe_park_source="off",weather_source="off",calendar_source="todoist",todoist_oauth_secret_arn="arn:test:todoist")
        screen=Publisher(config,self.store,rail_provider=FakeProvider([[{"time":"08:01"}]]),utcnow=self.utcnow,calendar_provider=FakeProvider([[]])).run()["screens"][1]
        self.assertEqual(screen["events"],[]); self.assertFalse(screen["stale"]); self.assertEqual(screen["title"],"UPCOMING")

    def test_disabled_feed_is_not_polled_and_is_omitted(self):
        runtime=default_runtime_config({"LED_THORPE_PARK_SOURCE":"off","LED_WEATHER_SOURCE":"off","LED_CALENDAR_SOURCE":"off"})
        runtime["feeds"]["departures"]["enabled"]=False
        rail=FakeProvider([])
        payload=Publisher(self.config,self.store,rail_provider=rail,utcnow=self.utcnow,runtime_config_store=StaticRuntimeConfigStore(runtime)).run()
        self.assertEqual(rail.calls,0); self.assertEqual(payload["screens"],[])

    def test_runtime_queue_settings_and_ride_order_reach_combined_screen(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",weather_source="off")
        runtime=default_runtime_config({"LED_WEATHER_SOURCE":"off"}); runtime["config_version"]=9
        runtime["feeds"]["departures"]["screen_duration_seconds"]=12
        runtime["feeds"]["queue_times"]["screen_duration_seconds"]=19
        runtime["feeds"]["queue_times"]["queue_scroll_speed"]=42
        runtime["feeds"]["queue_times"]["queue_scroll_pause_seconds"]=3
        runtime["feeds"]["queue_times"]["splash_enabled"]=True
        runtime["feeds"]["thorpe_park"]["rides"]=["Stealth","Hyperia"]
        runtime["feeds"]["thorpe_park"]["screen_duration_seconds"]=14
        runtime["feeds"]["chessington"]["rides"]=["Vampire"]
        runtime["feeds"]["chessington"]["screen_duration_seconds"]=11
        rides=[{"name":"Hyperia","open":True,"wait_minutes":20},{"name":"Stealth","open":True,"wait_minutes":5}]
        chess=[{"name":"Vampire","open":True,"wait_minutes":30}]
        payload=Publisher(config,self.store,rail_provider=FakeProvider([[{"time":"08:01"}]]),queue_provider=FakeProvider([rides]),chessington_provider=FakeProvider([chess]),utcnow=self.utcnow,runtime_config_store=StaticRuntimeConfigStore(runtime)).run()
        self.assertEqual(payload["config_version"],9)
        self.assertEqual(payload["screens"][0]["duration_seconds"],12)
        queue_screen=payload["screens"][1]
        self.assertEqual(queue_screen["id"],"queue-times")
        self.assertEqual(queue_screen["duration_seconds"],19)
        self.assertEqual(queue_screen["queue_scroll_speed"],42)
        self.assertEqual(queue_screen["queue_scroll_pause_seconds"],3)
        self.assertTrue(queue_screen["splash_enabled"])
        self.assertEqual([ride["name"] for ride in queue_screen["parks"][0]["rides"]],["Stealth","Hyperia"])
        self.assertEqual([ride["name"] for ride in queue_screen["parks"][1]["rides"]],["Vampire"])

    def test_disappeared_ride_is_flagged_without_breaking_park(self):
        config=PublisherConfig(bucket="test-bucket",national_rail_token="test-token",weather_source="off")
        runtime=default_runtime_config({"LED_WEATHER_SOURCE":"off"})
        runtime["feeds"]["thorpe_park"]["rides"]=["Hyperia","Renamed Ride"]
        runtime["feeds"]["chessington"]["enabled"]=False
        rides=[{"name":"Hyperia","open":True,"wait_minutes":20}]
        payload=Publisher(config,self.store,rail_provider=FakeProvider([[{"time":"08:01"}]]),queue_provider=FakeProvider([rides]),utcnow=self.utcnow,runtime_config_store=StaticRuntimeConfigStore(runtime)).run()
        queue_screen=payload["screens"][1]
        park=queue_screen["parks"][0]
        self.assertEqual([ride["name"] for ride in park["rides"]],["Hyperia"])
        self.assertEqual(park["missing_configured_rides"],["Renamed Ride"])


if __name__=="__main__": unittest.main()
