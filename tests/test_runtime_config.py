import copy
import unittest

from runtime_config import (
    DEFAULT_BUS_INTRO_WORDS,
    DEFAULT_CHESSINGTON_RIDES,
    DEFAULT_NO_SERVICES_DURATION_SECONDS,
    DEFAULT_STEAM_TRAIN_SPEED,
    DEFAULT_STEAM_TRAIN_WORDS,
    DEFAULT_STATION_LIST_SPACING,
    DEFAULT_STATION_SCROLL_SPEED,
    DEFAULT_WEATHER_SCREEN_DURATION_SECONDS,
    DEFAULT_WEATHER_TODAY_DURATION_SECONDS,
    DEFAULT_WEATHER_SUN_DURATION_SECONDS,
    DEFAULT_UPCOMING_TRAIN_COUNT,
    DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS,
    LEGACY_DEFAULT_CHESSINGTON_RIDES,
    MAX_STATION_LIST_SPACING,
    MAX_STATION_SCROLL_SPEED,
    MAX_STEAM_TRAIN_SPEED,
    MIN_STATION_LIST_SPACING,
    MIN_STEAM_TRAIN_SPEED,
    MIN_STATION_SCROLL_SPEED,
    RuntimeConfigConflict,
    RuntimeConfigStore,
    RuntimeConfigValidationError,
    default_runtime_config,
    schema_metadata,
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
        self.assertEqual(config["feeds"]["calendar"]["visible_task_count"], 6)
        self.assertEqual(config["feeds"]["departures"]["poll_seconds"], 60)
        self.assertEqual(config["feeds"]["departures"]["no_services_duration_seconds"], DEFAULT_NO_SERVICES_DURATION_SECONDS)
        self.assertEqual(config["feeds"]["departures"]["station_scroll_speed"], 20)
        self.assertEqual(config["feeds"]["departures"]["station_list_spacing"], 10)
        self.assertEqual(config["feeds"]["departures"]["upcoming_train_count"], DEFAULT_UPCOMING_TRAIN_COUNT)
        self.assertEqual(config["feeds"]["departures"]["upcoming_train_pause_seconds"], DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS)
        self.assertEqual(config["feeds"]["thorpe_park"]["park_id"], 2)
        self.assertEqual(config["feeds"]["chessington"]["park_id"], 3)
        self.assertEqual(config["feeds"]["chessington"]["rides"], list(DEFAULT_CHESSINGTON_RIDES))
        self.assertEqual(len(config["feeds"]["chessington"]["rides"]), 6)
        self.assertFalse(config["feeds"]["flash"]["enabled"])
        self.assertEqual(config["feeds"]["flash"]["screen_duration_seconds"], 5)
        self.assertEqual(
            schema_metadata()["feeds"]["flash"]["mutable_fields"],
            ["enabled", "screen_duration_seconds"],
        )

    def test_steam_train_defaults_schema_validation_and_legacy_backfill(self):
        config = default_runtime_config({})
        steam = config["feeds"]["steam_train"]
        self.assertTrue(steam["enabled"])
        self.assertEqual(steam["animation_speed"], DEFAULT_STEAM_TRAIN_SPEED)
        self.assertEqual(steam["words"], DEFAULT_STEAM_TRAIN_WORDS)

        schema = schema_metadata()["feeds"]["steam_train"]
        self.assertTrue(schema["virtual"])
        self.assertEqual(schema["fields"]["animation_speed"]["minimum"], MIN_STEAM_TRAIN_SPEED)
        self.assertEqual(schema["fields"]["animation_speed"]["maximum"], MAX_STEAM_TRAIN_SPEED)
        self.assertEqual(schema["fields"]["words"]["type"], "string")

        self.assertEqual(
            validate_feed_patch(
                "steam_train",
                {"enabled": False, "animation_speed": 36, "words": "all aboard"},
            ),
            {"enabled": False, "animation_speed": 36, "words": "all aboard"},
        )
        for speed in (MIN_STEAM_TRAIN_SPEED - 1, MAX_STEAM_TRAIN_SPEED + 1):
            with self.subTest(speed=speed):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_feed_patch("steam_train", {"animation_speed": speed})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("steam_train", {"words": 123})
        for words in ("choo\nchoo", "🚂"):
            with self.subTest(words=words):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_feed_patch("steam_train", {"words": words})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("steam_train", {"words": "x" * 81})

        legacy = default_runtime_config({})
        del legacy["feeds"]["steam_train"]
        validated = validate_runtime_config(legacy)
        self.assertTrue(validated["feeds"]["steam_train"]["enabled"])
        self.assertEqual(validated["feeds"]["steam_train"]["animation_speed"], DEFAULT_STEAM_TRAIN_SPEED)
        self.assertEqual(validated["feeds"]["steam_train"]["words"], DEFAULT_STEAM_TRAIN_WORDS)

    def test_sl7_bus_intro_controls_and_saved_settings_migrate(self):
        config = default_runtime_config({})
        bus = config["feeds"]["sl7_bus"]
        self.assertTrue(bus["bus_intro_enabled"])
        self.assertEqual(bus["words"], DEFAULT_BUS_INTRO_WORDS)
        self.assertEqual(bus["animation_speed"], DEFAULT_STEAM_TRAIN_SPEED)
        schema = schema_metadata()["feeds"]["sl7_bus"]
        for field in ("bus_intro_enabled", "animation_speed", "words"):
            self.assertIn(field, schema["mutable_fields"])
            self.assertIn(field, schema["fields"])
        self.assertEqual(schema["fields"]["words"]["maximumLength"], 80)
        self.assertEqual(
            validate_feed_patch("sl7_bus", {
                "bus_intro_enabled": False, "animation_speed": 40, "words": "Beep! Beep!...",
            }),
            {"bus_intro_enabled": False, "animation_speed": 40, "words": "Beep! Beep!..."},
        )
        for invalid in (4, 81, True):
            with self.subTest(speed=invalid), self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("sl7_bus", {"animation_speed": invalid})
        for invalid in ("🚍", "beep" + chr(10) + "beep", "x" * 81, None):
            with self.subTest(words=invalid), self.assertRaises(RuntimeConfigValidationError):
                validate_feed_patch("sl7_bus", {"words": invalid})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("sl7_bus", {"bus_intro_enabled": "false"})

        # Older persisted SL7 records gain defaults without changing existing selections.
        config["feeds"]["sl7_bus"].update({"heathrow_enabled": False, "display_every_cycles": 4})
        for field in ("bus_intro_enabled", "animation_speed", "words"):
            del config["feeds"]["sl7_bus"][field]
        migrated = validate_runtime_config(config)["feeds"]["sl7_bus"]
        self.assertTrue(migrated["bus_intro_enabled"])
        self.assertEqual(migrated["animation_speed"], DEFAULT_STEAM_TRAIN_SPEED)
        self.assertEqual(migrated["words"], DEFAULT_BUS_INTRO_WORDS)
        self.assertFalse(migrated["heathrow_enabled"])
        self.assertEqual(migrated["display_every_cycles"], 4)

    def test_flash_duration_is_bounded_and_legacy_configs_are_backfilled(self):
        self.assertEqual(
            validate_feed_patch("flash", {"enabled": True, "screen_duration_seconds": 12}),
            {"enabled": True, "screen_duration_seconds": 12},
        )
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("flash", {"screen_duration_seconds": 1})
        legacy = default_runtime_config({})
        del legacy["feeds"]["flash"]
        validated = validate_runtime_config(legacy)
        self.assertFalse(validated["feeds"]["flash"]["enabled"])

    def test_standalone_today_config_is_separate_from_weather_forecast(self):
        defaults = default_runtime_config({})
        self.assertFalse(defaults["feeds"]["today"]["enabled"])
        self.assertEqual(defaults["feeds"]["today"]["screen_duration_seconds"], 15)
        self.assertTrue(defaults["feeds"]["weather"]["today_enabled"])

        schema = schema_metadata()["feeds"]["today"]
        self.assertEqual(schema["mutable_fields"], ["enabled", "screen_duration_seconds"])
        self.assertTrue(schema["virtual"])
        self.assertEqual(schema["fields"]["screen_duration_seconds"]["minimum"], 2)
        self.assertEqual(schema["fields"]["screen_duration_seconds"]["maximum"], 300)
        self.assertEqual(
            validate_feed_patch("today", {"enabled": True, "screen_duration_seconds": 23}),
            {"enabled": True, "screen_duration_seconds": 23},
        )
        for invalid in (1, 301, True):
            with self.subTest(duration=invalid):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_feed_patch("today", {"screen_duration_seconds": invalid})
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("today", {"today_enabled": False})

        legacy = default_runtime_config({})
        del legacy["feeds"]["today"]
        upgraded = validate_runtime_config(legacy)
        self.assertEqual(upgraded["feeds"]["today"], defaults["feeds"]["today"])
        self.assertEqual(upgraded["feeds"]["weather"], defaults["feeds"]["weather"])

    def test_weather_screen_controls_are_schema_backed_bounded_and_legacy_safe(self):
        patch = validate_feed_patch(
            "weather",
            {
                "overview_enabled": False,
                "screen_duration_seconds": 12,
                "today_enabled": True,
                "today_duration_seconds": 11,
                "sun_enabled": False,
                "sun_duration_seconds": 7,
            },
        )
        self.assertEqual(
            patch,
            {
                "overview_enabled": False,
                "screen_duration_seconds": 12,
                "today_enabled": True,
                "today_duration_seconds": 11,
                "sun_enabled": False,
                "sun_duration_seconds": 7,
            },
        )
        for field in ("screen_duration_seconds", "today_duration_seconds", "sun_duration_seconds"):
            for value in (1, 301):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(RuntimeConfigValidationError):
                        validate_feed_patch("weather", {field: value})
        for field in ("overview_enabled", "today_enabled", "sun_enabled"):
            with self.subTest(field=field):
                with self.assertRaises(RuntimeConfigValidationError):
                    validate_feed_patch("weather", {field: 1})

        schema = schema_metadata()["feeds"]["weather"]
        expected_fields = (
            "overview_enabled",
            "screen_duration_seconds",
            "today_enabled",
            "today_duration_seconds",
            "sun_enabled",
            "sun_duration_seconds",
        )
        for field in expected_fields:
            self.assertIn(field, schema["mutable_fields"])
            self.assertIn(field, schema["fields"])

        weather = default_runtime_config({})["feeds"]["weather"]
        self.assertTrue(weather["overview_enabled"])
        self.assertEqual(weather["screen_duration_seconds"], DEFAULT_WEATHER_SCREEN_DURATION_SECONDS)
        self.assertTrue(weather["today_enabled"])
        self.assertEqual(weather["today_duration_seconds"], DEFAULT_WEATHER_TODAY_DURATION_SECONDS)
        self.assertTrue(weather["sun_enabled"])
        self.assertEqual(weather["sun_duration_seconds"], DEFAULT_WEATHER_SUN_DURATION_SECONDS)

        legacy = default_runtime_config({})
        for field in expected_fields:
            legacy["feeds"]["weather"].pop(field, None)
        validated = validate_runtime_config(legacy)["feeds"]["weather"]
        self.assertTrue(validated["overview_enabled"])
        self.assertEqual(validated["screen_duration_seconds"], DEFAULT_WEATHER_SCREEN_DURATION_SECONDS)
        self.assertTrue(validated["today_enabled"])
        self.assertEqual(validated["today_duration_seconds"], DEFAULT_WEATHER_TODAY_DURATION_SECONDS)
        self.assertTrue(validated["sun_enabled"])
        self.assertEqual(validated["sun_duration_seconds"], DEFAULT_WEATHER_SUN_DURATION_SECONDS)

    def test_calendar_visible_task_count_is_configurable_and_backfilled(self):
        self.assertEqual(
            validate_feed_patch("calendar", {"visible_task_count": 2}),
            {"visible_task_count": 2},
        )
        self.assertEqual(
            validate_feed_patch("calendar", {"visible_task_count": 6}),
            {"visible_task_count": 6},
        )
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("calendar", {"visible_task_count": 7})
        legacy = default_runtime_config({})
        del legacy["feeds"]["calendar"]["visible_task_count"]
        self.assertEqual(
            validate_runtime_config(legacy)["feeds"]["calendar"]["visible_task_count"],
            6,
        )

    def test_no_services_duration_is_bounded_and_backfilled_for_existing_config(self):
        patch = validate_feed_patch("departures", {"no_services_duration_seconds": 5})
        self.assertEqual(patch["no_services_duration_seconds"], 5)
        with self.assertRaises(RuntimeConfigValidationError):
            validate_feed_patch("departures", {"no_services_duration_seconds": 1})

        legacy = default_runtime_config({})
        del legacy["feeds"]["departures"]["no_services_duration_seconds"]
        validated = validate_runtime_config(legacy)
        self.assertEqual(
            validated["feeds"]["departures"]["no_services_duration_seconds"],
            DEFAULT_NO_SERVICES_DURATION_SECONDS,
        )

    def test_existing_saved_config_backfills_new_screens_without_reset(self):
        # An existing DynamoDB item predates newer feeds, including Insult of
        # the Hour. GET /config must be able to load it without losing settings.
        legacy = default_runtime_config({})
        original_ids = {"departures", "thorpe_park", "chessington", "weather", "calendar"}
        self.assertEqual(set(legacy["feeds"]), set(schema_metadata()["feeds"]))
        for feed_id in set(legacy["feeds"]) - original_ids:
            del legacy["feeds"][feed_id]
        legacy["config_version"] = 17
        legacy["updated_by"] = "human:admin@example.com"
        legacy["feeds"]["departures"]["screen_duration_seconds"] = 23
        legacy["feeds"]["weather"]["enabled"] = False
        saved_item = {"config_id": "runtime", **copy.deepcopy(legacy)}
        table = FakeTable()
        table.item = copy.deepcopy(saved_item)
        store = RuntimeConfigStore("table", table=table, defaults=default_runtime_config({}))

        loaded = store.load()
        self.assertEqual(set(loaded["feeds"]), set(schema_metadata()["feeds"]))
        self.assertFalse(loaded["feeds"]["insult_of_hour"]["enabled"])
        self.assertEqual(loaded["feeds"]["insult_of_hour"]["poll_seconds"], 3600)
        self.assertEqual(loaded["config_version"], 17)
        self.assertEqual(loaded["updated_by"], "human:admin@example.com")
        self.assertEqual(loaded["feeds"]["departures"]["screen_duration_seconds"], 23)
        self.assertFalse(loaded["feeds"]["weather"]["enabled"])
        self.assertEqual(table.item, saved_item)  # Reads do not reset persisted data.

        updated, fields = store.patch_feed(
            "insult_of_hour", {"enabled": True},
            expected_version=17, updated_by="human:admin@example.com",
        )
        self.assertEqual(fields, ["enabled"])
        self.assertEqual(updated["config_version"], 18)
        self.assertTrue(store.load()["feeds"]["insult_of_hour"]["enabled"])
        self.assertEqual(table.item["feeds"]["departures"]["screen_duration_seconds"], 23)

    def test_missing_original_or_unknown_feed_still_fails_validation(self):
        config = default_runtime_config({})
        for feed_id in ("departures", "thorpe_park", "chessington", "weather", "calendar"):
            with self.subTest(feed_id=feed_id):
                missing = copy.deepcopy(config)
                del missing["feeds"][feed_id]
                with self.assertRaisesRegex(RuntimeConfigValidationError, "supported v1 feed IDs"):
                    validate_runtime_config(missing)

        unknown = copy.deepcopy(config)
        unknown["feeds"]["not_a_feed"] = {"enabled": True}
        with self.assertRaisesRegex(RuntimeConfigValidationError, "supported v1 feed IDs"):
            validate_runtime_config(unknown)

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
