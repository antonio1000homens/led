import unittest

from matrix_runtime import DIAGNOSTIC_COLORS, RuntimeMode, collect_gc_with_state


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
