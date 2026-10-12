import os
import sys
import unittest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from summarize_rail_heap import render_table, summarize


class RailHeapSummaryTests(unittest.TestCase):
    def test_summarizes_build_gc_latency_gaps_and_coexisting_prebuild_heap(self):
        log = [
            "RAIL PREBUILD OK screen_id=departures duration=2.000s gc_duration=0.050s gc_reclaimed=200 heap_free_before=5000000 heap_free_after=4500000 retained_heap_drop=500000",
            "SCREEN END id=steam-train kind=steam_train_intro low_water=4300000",
            "SCREEN START id=departures kind=rail_combined heap_free=4200000",
            "RAIL BUILD START services=5 static_row_renderer=labels heap_free=4200000",
            "RAIL BUILD OK scenes=1 static_row_bitmaps=0 duration=0.400s heap_free_before=4200000 heap_free_after=3700000 heap_drop=500000",
            "RAIL GC ENTER reason=cold_scene_build auto_gc_during_build=False entry_collect=True duration=0.020s heap_free=3700000 heap_allocated=100000",
            "RAIL POST BUILD GC duration=0.030s heap_free_before=3700000 heap_free_after=3800000 reclaimed_bytes=100000 retained_heap_drop=400000 build_to_gc_ms=400",
            "RAIL FIRST REFRESH OK duration=0.100s scene_ready_to_present_ms=35 refreshed=True heap_free=3800000",
            "RAIL GC END reason=calling_end_pause duration=0.010s heap_free_before=3800000 heap_free_after=3800100",
            "RAIL FRAME GAP gap_ms=220 preframe_ms=1.0 phase=4.0",
            "RAIL GC EXIT duration=0.015s heap_free=3800100",
            "SCREEN END id=departures kind=rail_combined duration=30.0s heap_free=3800100 low_water=3600000",
        ]
        cycles = summarize(log, "control")
        self.assertEqual(len(cycles), 1)
        cycle = cycles[0]
        self.assertEqual(cycle["services"], 5)
        self.assertEqual(cycle["train_prepared_min_free"], 4300000)
        self.assertEqual(cycle["build_heap_drop"], 500000)
        self.assertEqual(cycle["retained_bytes"], 400000)
        self.assertEqual(cycle["ready_to_present_ms"], 35)
        self.assertEqual(cycle["gc_count"], 5)
        self.assertAlmostEqual(cycle["gc_seconds"], 0.125)
        self.assertEqual(cycle["gap_over_200ms"], 1)
        self.assertEqual(cycle["max_gap_ms"], 220)
        self.assertEqual(cycle["min_free"], 3600000)
        self.assertIn("| control | departures | complete | 5 | labels | 4300000 |", render_table(cycles))

    def test_keeps_a_reset_interrupted_rail_cycle_in_the_summary(self):
        cycles = summarize([
            "SCREEN START id=departures kind=rail_combined",
            "RAIL BUILD START services=10 static_row_renderer=bitmap heap_free=2000000",
            "RAIL BUILD OK scenes=1 static_row_bitmaps=10 duration=1.0s heap_free_before=2000000 heap_free_after=100000 heap_drop=1900000",
            "Code done running. Auto-reload is off.",
            "soft reboot",
        ], "prebuild")
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0]["status"], "reset")
        self.assertEqual(cycles[0]["errors"], 1)
        self.assertIn("| prebuild | departures | reset | 10 | bitmap |", render_table(cycles))


if __name__ == "__main__":
    unittest.main()
