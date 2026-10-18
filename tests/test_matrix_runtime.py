import unittest

from matrix_runtime import (
    DIAGNOSTIC_COLORS,
    RuntimeMode,
    collect_gc_with_state,
    enter_rail_gc_window,
    christmas_gc_action,
    enter_christmas_gc_window,
    leave_christmas_gc_window,
    prepare_christmas_scene_gc,
)


class FakeRotation:
    def __init__(self):
        self.calls = []

    def next(self, now):
        self.calls.append(now)


class FakeGarbageCollector:
    def __init__(self, fail=False):
        self.enabled = False
        self.fail = fail
        self.collections = 0

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def collect(self):
        self.collections += 1
        if self.fail:
            raise RuntimeError("collection failed")
        return 12


class RuntimeModeTests(unittest.TestCase):
    def test_christmas_gc_is_only_collected_at_scene_boundaries(self):
        collector = FakeGarbageCollector()
        self.assertEqual(christmas_gc_action("christmas_tracker", False), "enter")
        self.assertEqual(christmas_gc_action("christmas_tracker_intro", False), "enter")
        self.assertEqual(prepare_christmas_scene_gc(collector), 12)
        self.assertTrue(collector.enabled)
        enter_christmas_gc_window(collector)
        self.assertFalse(collector.enabled)
        self.assertEqual(collector.collections, 1)
        self.assertIsNone(christmas_gc_action("christmas_tracker", True))
        self.assertIsNone(christmas_gc_action("christmas_tracker_intro", True))
        self.assertEqual(christmas_gc_action("christmas_tracker", True, True), "exit")
        self.assertEqual(christmas_gc_action("weather_today", True), "exit")
        self.assertEqual(leave_christmas_gc_window(collector), 12)
        self.assertTrue(collector.enabled)
        self.assertEqual(collector.collections, 2)

    def test_prebuilt_rail_entry_suppresses_gc_without_collecting(self):
        collector = FakeGarbageCollector()
        collected = enter_rail_gc_window(
            collector, allow_during_build=False, collect_at_entry=False
        )
        self.assertFalse(collected)
        self.assertEqual(collector.collections, 0)
        self.assertFalse(collector.enabled)

    def test_cold_and_post_build_experiment_entry_gc_modes(self):
        cold_collector = FakeGarbageCollector()
        self.assertTrue(enter_rail_gc_window(cold_collector))
        self.assertEqual(cold_collector.collections, 1)
        self.assertFalse(cold_collector.enabled)

        experiment_collector = FakeGarbageCollector()
        self.assertFalse(enter_rail_gc_window(
            experiment_collector, allow_during_build=True
        ))
        self.assertEqual(experiment_collector.collections, 0)
        self.assertTrue(experiment_collector.enabled)

    def test_manual_gc_restores_requested_state_after_success_or_failure(self):
        for fail in (False, True):
            for enabled_after in (False, True):
                collector = FakeGarbageCollector(fail=fail)
                with self.subTest(fail=fail, enabled_after=enabled_after):
                    if fail:
                        with self.assertRaises(RuntimeError):
                            collect_gc_with_state(collector, enabled_after)
                    else:
                        self.assertEqual(collect_gc_with_state(collector, enabled_after), 12)
                    self.assertEqual(collector.enabled, enabled_after)
                    self.assertEqual(collector.collections, 1)

    def test_long_up_enters_and_exits_diagnostic_mode(self):
        runtime = RuntimeMode()
        self.assertEqual(runtime.mode, "normal")
        self.assertFalse(runtime.handle("up"))
        self.assertTrue(runtime.handle("up_long"))
        self.assertEqual(runtime.mode, "diagnostic")
        self.assertEqual(runtime.diagnostic(), DIAGNOSTIC_COLORS[0])
        self.assertTrue(runtime.handle("up_long"))
        self.assertEqual(runtime.mode, "normal")

    def test_down_cycles_diagnostic_colours(self):
        runtime = RuntimeMode()
        runtime.handle("up_long")
        for index in range(1, len(DIAGNOSTIC_COLORS)):
            self.assertTrue(runtime.handle("down"))
            self.assertEqual(runtime.diagnostic(), DIAGNOSTIC_COLORS[index])
        runtime.handle("down")
        self.assertEqual(runtime.diagnostic(), DIAGNOSTIC_COLORS[0])

    def test_long_down_advances_rotation_only_in_normal_mode(self):
        runtime = RuntimeMode()
        rotation = FakeRotation()
        self.assertFalse(runtime.handle("down", rotation, 11))
        self.assertEqual(rotation.calls, [])
        self.assertFalse(runtime.handle("down_long", rotation, 12))
        self.assertEqual(rotation.calls, [12])
        runtime.handle("up_long")
        runtime.handle("down_long", rotation, 13)
        self.assertEqual(rotation.calls, [12])


if __name__ == "__main__":
    unittest.main()
