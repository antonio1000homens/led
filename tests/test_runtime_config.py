import copy
import unittest

from runtime_config import (
    RuntimeConfigConflict,
    RuntimeConfigStore,
    RuntimeConfigValidationError,
    default_runtime_config,
    validate_feed_patch,
)


class ConditionalFailure(Exception):
    response = {"Error": {"Code": "ConditionalCheckFailedException"}}


class FakeTable:
    def __init__(self):
        self.item = None

    def get_item(self, **kwargs):
        del kwargs
        return {} if self.item is None else {"Item": copy.deepcopy(self.item)}

    def put_item(self, Item, ConditionExpression=None, ExpressionAttributeValues=None):
        if ConditionExpression == "attribute_not_exists(config_id)" and self.item is not None:
            raise ConditionalFailure()
        if ConditionExpression == "config_version = :expected":
            expected = ExpressionAttributeValues[":expected"]
            if self.item is None or self.item["config_version"] != expected:
                raise ConditionalFailure()
        self.item = copy.deepcopy(Item)
        return {}


class RuntimeConfigTests(unittest.TestCase):
    def test_defaults_match_existing_sources_and_minimum_polling(self):
        config = default_runtime_config({
            "LED_THORPE_PARK_SOURCE": "off",
            "LED_WEATHER_SOURCE": "off",
            "LED_CALENDAR_SOURCE": "todoist",
            "LED_CACHE_SECONDS": "5",
        })
        self.assertFalse(config["feeds"]["thorpe_park"]["enabled"])
        self.assertFalse(config["feeds"]["weather"]["enabled"])
        self.assertTrue(config["feeds"]["calendar"]["enabled"])
        self.assertEqual(config["feeds"]["departures"]["poll_seconds"], 60)
        self.assertEqual(config["feeds"]["thorpe_park"]["park_id"], 2)
        self.assertEqual(config["feeds"]["chessington"]["park_id"], 3)

    def test_validation_rejects_sub_minimum_poll_and_unknown_or_read_only_fields(self):
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("departures", {"poll_seconds": 59})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("departures", {"station": "WAT"})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("thorpe_park", {"park_id": 99})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("not_a_feed", {"enabled": True})

    def test_ride_validation_is_case_insensitive_canonical_and_ordered(self):
        patch = validate_feed_patch(
            "thorpe_park",
            {"rides": ["stealth", "HYPERIA"]},
            available_rides=["Hyperia", "Stealth", "The Swarm"],
        )
        self.assertEqual(patch["rides"], ["Stealth", "Hyperia"])
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("thorpe_park", {"rides": ["Missing ride"]}, ["Hyperia"])

    def test_store_seeds_defaults_and_enforces_optimistic_concurrency(self):
        table = FakeTable()
        store = RuntimeConfigStore("table", table=table, defaults=default_runtime_config({}))
        seeded = store.ensure()
        self.assertEqual(seeded["config_version"], 1)
        updated, fields = store.patch_feed(
            "departures", {"enabled": False, "poll_seconds": 120},
            expected_version=1, updated_by="human:test@example.com",
        )
        self.assertEqual(updated["config_version"], 2)
        self.assertEqual(fields, ["enabled", "poll_seconds"])
        self.assertFalse(updated["feeds"]["departures"]["enabled"])
        with self.assertRaises(RuntimeConfigConflict):
            store.patch_feed(
                "departures", {"enabled": True},
                expected_version=1, updated_by="machine:ha.access",
            )


if __name__ == "__main__":
    unittest.main()
