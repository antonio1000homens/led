import copy
import unittest

from runtime_config import (
    DEFAULT_CHESSINGTON_RIDES,
    DEFAULT_STATION_LIST_SPACING,
    DEFAULT_STATION_SCROLL_SPEED,
    DEFAULT_UPCOMING_TRAIN_COUNT,
    DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS,
    LEGACY_DEFAULT_CHESSINGTON_RIDES,
    MAX_STATION_LIST_SPACING,
    MAX_STATION_SCROLL_SPEED,
    MIN_STATION_LIST_SPACING,
    MIN_STATION_SCROLL_SPEED,
    RuntimeConfigConflict,
    RuntimeConfigStore,
    RuntimeConfigValidationError,
    default_runtime_config,
    validate_feed_patch,
    validate_runtime_config,
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
        self.assertEqual(config["feeds"]["departures"]["station_scroll_speed"], 30)
        self.assertEqual(config["feeds"]["departures"]["station_list_spacing"], 28)
        self.assertEqual(config["feeds"]["departures"]["upcoming_train_count"], DEFAULT_UPCOMING_TRAIN_COUNT)
        self.assertEqual(config["feeds"]["departures"]["upcoming_train_pause_seconds"], DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS)
        self.assertEqual(config["feeds"]["thorpe_park"]["park_id"], 2)
        self.assertEqual(config["feeds"]["chessington"]["park_id"], 3)
        self.assertEqual(config["feeds"]["chessington"]["rides"], list(DEFAULT_CHESSINGTON_RIDES))
        self.assertEqual(len(config["feeds"]["chessington"]["rides"]), 6)

    def test_validation_rejects_sub_minimum_poll_and_unknown_or_read_only_fields(self):
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("departures", {"poll_seconds": 59})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("departures", {"station": "WAT"})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("thorpe_park", {"park_id": 99})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("not_a_feed", {"enabled": True})

    def test_departure_marquee_settings_are_bounded_and_validated(self):
        patch = validate_feed_patch(
            "departures",
            {"station_scroll_speed": 42, "station_list_spacing": 24},
        )
        self.assertEqual(patch, {"station_scroll_speed": 42, "station_list_spacing": 24})
        for value in (MIN_STATION_SCROLL_SPEED - 1, MAX_STATION_SCROLL_SPEED + 1):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("departures", {"station_scroll_speed": value})
        for value in (MIN_STATION_LIST_SPACING - 1, MAX_STATION_LIST_SPACING + 1):
            with self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("departures", {"station_list_spacing": value})

        patch = validate_feed_patch("departures", {"upcoming_train_count": 6, "upcoming_train_pause_seconds": 3})
        self.assertEqual(patch, {"upcoming_train_count": 6, "upcoming_train_pause_seconds": 3})

    def test_legacy_runtime_config_defaults_missing_departure_rotation_fields(self):
        legacy = default_runtime_config({})
        del legacy["feeds"]["departures"]["upcoming_train_count"]
        del legacy["feeds"]["departures"]["upcoming_train_pause_seconds"]
        validated = validate_runtime_config(legacy)
        self.assertEqual(validated["feeds"]["departures"]["upcoming_train_count"], DEFAULT_UPCOMING_TRAIN_COUNT)
        self.assertEqual(validated["feeds"]["departures"]["upcoming_train_pause_seconds"], DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS)

    def test_legacy_runtime_config_defaults_missing_marquee_fields(self):
        legacy = default_runtime_config({})
        del legacy["feeds"]["departures"]["station_scroll_speed"]
        del legacy["feeds"]["departures"]["station_list_spacing"]

        validated = validate_runtime_config(legacy)

        self.assertEqual(
            validated["feeds"]["departures"]["station_scroll_speed"],
            DEFAULT_STATION_SCROLL_SPEED,
        )
        self.assertEqual(
            validated["feeds"]["departures"]["station_list_spacing"],
            DEFAULT_STATION_LIST_SPACING,
        )

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
            "departures",
            {
                "enabled": False,
                "poll_seconds": 120,
                "station_scroll_speed": 34,
                "station_list_spacing": 20,
            },
            expected_version=1,
            updated_by="human:test@example.com",
        )
        self.assertEqual(updated["config_version"], 2)
        self.assertEqual(
            fields,
            ["enabled", "poll_seconds", "station_scroll_speed", "station_list_spacing"],
        )
        self.assertFalse(updated["feeds"]["departures"]["enabled"])
        self.assertEqual(updated["feeds"]["departures"]["station_scroll_speed"], 34)
        self.assertEqual(updated["feeds"]["departures"]["station_list_spacing"], 20)
        with self.assertRaises(RuntimeConfigConflict):
            store.patch_feed(
                "departures", {"enabled": True},
                expected_version=1, updated_by="machine:ha.access",
            )

    def test_store_expands_only_untouched_legacy_chessington_defaults(self):
        table = FakeTable()
        legacy = default_runtime_config({})
        legacy["config_version"] = 4
        legacy["updated_at"] = "2026-09-13T18:00:00Z"
        legacy["updated_by"] = "system:defaults"
        legacy["feeds"]["chessington"]["rides"] = list(LEGACY_DEFAULT_CHESSINGTON_RIDES)
        table.item = {"config_id": "runtime", **copy.deepcopy(legacy)}
        store = RuntimeConfigStore("table", table=table, defaults=default_runtime_config({}))

        upgraded = store.ensure()

        self.assertEqual(upgraded["config_version"], 5)
        self.assertEqual(upgraded["feeds"]["chessington"]["rides"], list(DEFAULT_CHESSINGTON_RIDES))
        self.assertEqual(table.item["feeds"]["chessington"]["rides"], list(DEFAULT_CHESSINGTON_RIDES))

        human = copy.deepcopy(legacy)
        human["updated_by"] = "human:admin@example.com"
        table.item = {"config_id": "runtime", **human}
        unchanged = store.ensure()
        self.assertEqual(unchanged["config_version"], 4)
        self.assertEqual(unchanged["feeds"]["chessington"]["rides"], list(LEGACY_DEFAULT_CHESSINGTON_RIDES))


if __name__ == "__main__":
    unittest.main()
