import importlib.util
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "render-r2-worker-config.py"
SPEC = importlib.util.spec_from_file_location("render_r2_worker_config", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class R2WorkerConfigTests(unittest.TestCase):
    def test_custom_bucket_route_and_zone_follow_stack_settings(self):
        config = MODULE.render("custom-r2-bucket", "led.example.org", "example.org")
        self.assertIn('bucket_name = "custom-r2-bucket"', config)
        self.assertIn('pattern = "led.example.org/api/screens"', config)
        self.assertIn('zone_name = "example.org"', config)
        self.assertNotIn("alf-broadcast.co.uk", config)

    def test_invalid_bucket_or_out_of_zone_hostname_is_rejected(self):
        for bucket in ("UPPERCASE", "bad_underscore", "-wrong", "a" * 64):
            with self.subTest(bucket=bucket), self.assertRaises(ValueError):
                MODULE.render(bucket, "led.example.org", "example.org")
        with self.assertRaises(ValueError):
            MODULE.render("led-live-state", "led.other.org", "example.org")
