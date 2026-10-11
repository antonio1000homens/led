"""Weather sequence and maintenance eligibility regressions for the LED scheduler."""
import random
import shutil
import subprocess
import unittest
from pathlib import Path

from screen_client import ScreenRotation


ROOT = Path(__file__).resolve().parents[1]
WEATHER = (
    {"id": "weather-sun", "kind": "weather_sun", "duration_seconds": 6},
    {"id": "weather-today", "kind": "weather_today", "duration_seconds": 8},
    {"id": "weather-weekly", "kind": "weather_weekly", "duration_seconds": 8},
)
WEATHER_KINDS = ("weather_sun", "weather_today", "weather_weekly")


class WeatherRotationTests(unittest.TestCase):
    def test_weather_pages_stay_consecutive_despite_shuffled_static_feeds(self):
        screens = [
            {"id": "train", "kind": "steam_train_intro", "duration_seconds": 2},
            {"id": "departures", "kind": "rail_combined", "duration_seconds": 3},
            {"id": "joke", "kind": "dad_joke", "duration_seconds": 2},
            WEATHER[0], WEATHER[1], WEATHER[2],
            {"id": "fact", "kind": "random_fact", "duration_seconds": 2},
            {"id": "other", "kind": "message", "duration_seconds": 2},
        ]
        for seed in range(50):
            rotation = ScreenRotation(rng=random.Random(seed))
            rotation.update(screens, 0)
            for cycle in range(3):
                plan = rotation.screens
                ids = [item["id"] for item in plan]
                weather_index = ids.index("weather-sun")
                self.assertEqual(
                    [item["kind"] for item in plan[weather_index:weather_index + 3]],
                    list(WEATHER_KINDS),
                )
                self.assertEqual(ids.index("departures"), ids.index("train") + 1)
                self.assertEqual(len(ids), len(screens))
                # Consume the whole cycle, then repeat with a reshuffled pool.
                rotation.current(sum(
                    int(item["duration_seconds"]) for item in screens
                ) * (cycle + 1) + 1)

    def test_disabled_weather_pages_still_form_one_ordered_block(self):
        for selection in ((0, 2), (1, 2), (0, 1), (0,), (1,), (2,)):
            weather = [WEATHER[index] for index in selection]
            for seed in range(12):
                rotation = ScreenRotation(rng=random.Random(seed))
                rotation.update(
                    [WEATHER[index] for index in selection]
                    + [{"id": "fact", "kind": "random_fact", "duration_seconds": 5}],
                    0,
                )
                ids = [item["id"] for item in rotation.screens]
                start = ids.index(weather[0]["id"])
                self.assertEqual(ids[start:start + len(weather)],
                                 [item["id"] for item in weather])

    def test_today_and_weekly_are_maintenance_safe_but_sun_is_not(self):
        self.assertFalse(ScreenRotation.is_maintenance_screen(WEATHER[0]))
        self.assertTrue(ScreenRotation.is_maintenance_screen(WEATHER[1]))
        self.assertTrue(ScreenRotation.is_maintenance_screen(WEATHER[2]))
        for weather in WEATHER:
            self.assertFalse(ScreenRotation.is_static(weather))
        self.assertTrue(ScreenRotation.is_maintenance_screen(
            {"id": "fact", "kind": "random_fact"}
        ))

    def test_weather_block_and_phase_survive_http_refresh(self):
        rotation = ScreenRotation(rng=random.Random(4))
        rotation.update(
            [{"id": "other", "kind": "message", "duration_seconds": 2},
             *WEATHER, {"id": "joke", "kind": "dad_joke", "duration_seconds": 2}],
            0,
        )
        sun_index = next(i for i, item in enumerate(rotation.screens)
                         if item["kind"] == "weather_sun")
        rotation.index = sun_index
        rotation.started_at = 0
        self.assertEqual(rotation.current(2)[0]["kind"], "weather_sun")
        rotation.update(
            [{"id": "other", "kind": "message", "duration_seconds": 2},
             *WEATHER, {"id": "joke", "kind": "dad_joke", "duration_seconds": 2}],
            3,
        )
        self.assertEqual(rotation.current(3)[1], 3)
        self.assertEqual(rotation.current(6)[0]["kind"], "weather_today")
        self.assertEqual(rotation.current(14)[0]["kind"], "weather_weekly")

    @unittest.skipUnless(shutil.which("node"), "Node.js is needed for browser scheduler test")
    def test_simulator_does_not_split_weather_block(self):
        import re
        html = (ROOT / "simulator" / "index.html").read_text()
        script = re.search(r"<script>([\\s\\S]*?)</script>", html).group(1)
        scheduler = script[script.index("    let cyclePlan"):
                           script.index("    function stationMarqueeSpeed")]
        fixture = """
let screens = [
  {id:'joke',kind:'dad_joke'},
  {id:'sun',kind:'weather_sun'},
  {id:'today',kind:'weather_today'},
  {id:'week',kind:'weather_weekly'},
  {id:'fact',kind:'random_fact'}
];
for (const kinds of [['weather_sun','weather_today','weather_weekly'],
                     ['weather_sun','weather_weekly'],
                     ['weather_today','weather_weekly']]) {
  screens = [{id:'joke',kind:'dad_joke'}, ...kinds.map(kind=>({id:kind,kind})),
             {id:'fact',kind:'random_fact'}];
  for (let trial=0;trial<100;trial++) {
    const plan = makeCyclePlan();
    const index = plan.findIndex(screen=>screen.kind===kinds[0]);
    if (kinds.some((kind,offset)=>plan[index+offset]?.kind!==kind)) {
      throw Error('Weather block split: '+plan.map(screen=>screen.kind));
    }
  }
}
"""
        subprocess.run(["node"], input=scheduler + fixture, text=True,
                       check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
