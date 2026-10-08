"""Contract tests for the optional dad joke screen."""
import pathlib
import sys
import unittest
from unittest.mock import patch
from io import BytesIO

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dad_jokes import DadJokeProvider
from runtime_config import default_runtime_config, validate_runtime_config, validate_feed_patch, schema_metadata


class DadJokesTests(unittest.TestCase):
    def test_default_disabled_and_admin_schema(self):
        config = default_runtime_config({})
        self.assertFalse(config["feeds"]["dad_joke"]["enabled"])
        self.assertIn("enabled", schema_metadata()["feeds"]["dad_joke"]["mutable_fields"])
        self.assertEqual(config["feeds"]["dad_joke"]["screen_duration_seconds"], 15)
        self.assertEqual(config["feeds"]["dad_joke"]["display_every_cycles"], 1)

    def test_existing_saved_config_migrates_additively(self):
        config = default_runtime_config({})
        del config["feeds"]["dad_joke"]
        for feed in config["feeds"].values():
            feed.pop("display_every_cycles", None)
        migrated = validate_runtime_config(config)
        self.assertFalse(migrated["feeds"]["dad_joke"]["enabled"])
        self.assertEqual(migrated["feeds"]["calendar"]["display_every_cycles"], 1)

    def test_admin_patch_validates(self):
        self.assertEqual(validate_feed_patch("dad_joke", {"enabled": True}), {"enabled": True})
        self.assertEqual(validate_feed_patch("dad_joke", {"display_every_cycles": 3}), {"display_every_cycles": 3})
        with self.assertRaises(ValueError):
            validate_feed_patch("dad_joke", {"poll_seconds": 3})

    def test_provider_fetch_and_normalise(self):
        class Response(BytesIO):
            pass
        with patch("dad_jokes.urlopen", return_value=Response(b'{"joke": "Hello dad!"}')) as urlopen:
            self.assertEqual(DadJokeProvider().fetch(), "Hello dad!")
            self.assertEqual(urlopen.call_args.kwargs["timeout"], 5)
            self.assertEqual(urlopen.call_args.args[0].get_header("Accept"), "application/json")


if __name__ == "__main__":
    unittest.main()
