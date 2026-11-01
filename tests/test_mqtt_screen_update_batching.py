"""Guard the firmware against rebuilding screens per MQTT message."""

import ast
from pathlib import Path
import unittest


CODE_PATH = Path(__file__).resolve().parents[1] / "code.py"


def _call_name(statement):
    if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
        return None
    function = statement.value.func
    if isinstance(function, ast.Name):
        return function.id
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return "{}.{}".format(function.value.id, function.attr)
    return None


class MqttScreenUpdateBatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(CODE_PATH.read_text())

    def test_callbacks_mark_screens_dirty_without_rebuilding_rotation(self):
        callback = next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef) and node.name == "receive_mqtt"
        )
        calls = [
            node for node in ast.walk(callback)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "update_sources"
        ]
        self.assertEqual(calls, [])
        assigned_names = {
            target.id
            for node in ast.walk(callback)
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        self.assertIn("mqtt_screens_changed", assigned_names)
        self.assertIn("mqtt_screens_update_pending", assigned_names)

    def test_accepted_timer_snapshots_mark_the_static_sleep_wake_flag(self):
        callback = next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef) and node.name == "receive_mqtt"
        )
        assignments = [
            node for node in ast.walk(callback)
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name)
                    and target.id == "timer_update_pending"
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        self.assertIsInstance(assignments[0].value, ast.Constant)
        self.assertIs(assignments[0].value.value, True)

    def test_every_mqtt_poll_applies_one_coalesced_update_after_poll(self):
        poll_locations = []
        for node in ast.walk(self.tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for index, statement in enumerate(body):
                if _call_name(statement) == "mqtt.poll":
                    poll_locations.append((body, index))

        self.assertEqual(len(poll_locations), 3)
        for body, index in poll_locations:
            next_statement = body[index + 1]
            if isinstance(next_statement, ast.If):
                self.assertIn("mqtt_animation_active", ast.unparse(next_statement.test))
                self.assertEqual(
                    _call_name(next_statement.body[0]),
                    "_apply_pending_mqtt_screen_updates",
                )
            else:
                self.assertEqual(
                    _call_name(next_statement),
                    "_apply_pending_mqtt_screen_updates",
                )

    def test_expiry_and_staleness_paths_do_not_rebuild_sources_directly(self):
        update_calls = [
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "rotation"
            and node.func.attr == "update_sources"
        ]
        self.assertEqual(len(update_calls), 2)
        helper = next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_apply_pending_mqtt_screen_updates"
        )
        self.assertEqual(
            sum(call in ast.walk(helper) for call in update_calls),
            1,
        )
        # The other direct rebuild is the complete HTTP replacement path.
        self.assertTrue(
            any(isinstance(call.args[0], ast.Name) and call.args[0].id == "screens"
                for call in update_calls)
        )

    def test_pending_updates_rebuild_once_and_clear_pending_state(self):
        helper = next(
            node for node in ast.walk(self.tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_apply_pending_mqtt_screen_updates"
        )

        class Rotation:
            http_screens = [{"id": "departures"}]

            def __init__(self):
                self.calls = []

            def update_sources(self, http_screens, mqtt_screens, now):
                self.calls.append((http_screens, mqtt_screens, now))

        rotation = Rotation()
        namespace = {
            "mqtt_screens_update_pending": True,
            "rail_gc_suspended": True,
            "rotation": rotation,
            "_reminder_epoch": lambda now: now + 1000,
            "_effective_mqtt_screens": lambda epoch: [{"id": "football"}],
            "ticks_ms": lambda: 1234,
        }
        exec(compile(ast.Module(body=[helper], type_ignores=[]), "code.py", "exec"), namespace)

        self.assertFalse(namespace["_apply_pending_mqtt_screen_updates"](19))
        self.assertTrue(namespace["mqtt_screens_update_pending"])
        self.assertEqual(rotation.calls, [])

        namespace["rail_gc_suspended"] = False
        self.assertTrue(namespace["_apply_pending_mqtt_screen_updates"](20))
        self.assertFalse(namespace["mqtt_screens_update_pending"])
        self.assertEqual(
            rotation.calls,
            [([{"id": "departures"}], [{"id": "football"}], 1234)],
        )
        self.assertFalse(namespace["_apply_pending_mqtt_screen_updates"](21))
        self.assertEqual(len(rotation.calls), 1)


if __name__ == "__main__":
    unittest.main()
