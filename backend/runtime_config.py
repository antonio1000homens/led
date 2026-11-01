"""Typed runtime configuration shared by the publisher and control API.

Runtime values are operational, non-secret settings.  Provider credentials and
other deployment secrets deliberately do not belong in this model.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from decimal import Decimal
import os
from typing import Any

from cron_schedule import parse_cron_schedule

CONFIG_ID = "runtime"
MIN_POLL_SECONDS = 60
MIN_INSULT_POLL_SECONDS = 3600  # Never request a new insult more than hourly.
MAX_POLL_SECONDS = 86400
MIN_SCREEN_DURATION_SECONDS = 2
MAX_SCREEN_DURATION_SECONDS = 300
MIN_STATION_SCROLL_SPEED = 10
MAX_STATION_SCROLL_SPEED = 80
DEFAULT_STATION_SCROLL_SPEED = 20
MIN_STATION_LIST_SPACING = 8
MAX_STATION_LIST_SPACING = 80
DEFAULT_STATION_LIST_SPACING = 10
MIN_UPCOMING_TRAIN_COUNT = 2
MAX_UPCOMING_TRAIN_COUNT = 10
DEFAULT_UPCOMING_TRAIN_COUNT = 4
MIN_UPCOMING_TRAIN_PAUSE_SECONDS = 1
MAX_UPCOMING_TRAIN_PAUSE_SECONDS = 30
DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS = 2
DEFAULT_NO_SERVICES_DURATION_SECONDS = 5
MIN_STEAM_TRAIN_SPEED = 8
MAX_STEAM_TRAIN_SPEED = 80
DEFAULT_STEAM_TRAIN_SPEED = 24
MAX_STEAM_TRAIN_WORDS_LENGTH = 80
DEFAULT_STEAM_TRAIN_WORDS = "choo choo"
DEFAULT_BUS_INTRO_WORDS = "Beep! Beep!..."
SCREEN_SCHEDULE_FEEDS = (
    "steam_train", "departures", "queue_times", "weather", "dad_joke",
    "random_fact", "quotes", "insult_of_hour", "today", "calendar",
    "recycling", "sl7_bus", "christmas", "football_fixtures", "cubs",
)
MAX_SCHEDULE_WINDOWS = 16
MAX_SCHEDULE_WINDOW_MINUTES = 31 * 24 * 60
MIN_QUEUE_SCROLL_SPEED = 8
MAX_QUEUE_SCROLL_SPEED = 80
DEFAULT_QUEUE_SCROLL_SPEED = 27
MIN_QUEUE_SCROLL_PAUSE_SECONDS = 1
MAX_QUEUE_SCROLL_PAUSE_SECONDS = 30
DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS = 1
DEFAULT_QUEUE_SCREEN_DURATION_SECONDS = 16
DEFAULT_WEATHER_SCREEN_DURATION_SECONDS = 8
DEFAULT_WEATHER_TODAY_DURATION_SECONDS = 8
DEFAULT_WEATHER_SUN_DURATION_SECONDS = 6
DEFAULT_FLASH_SCREEN_DURATION_SECONDS = 5
MIN_FLASH_SCREEN_DURATION_SECONDS = 2
MAX_FLASH_SCREEN_DURATION_SECONDS = 60
MIN_BUS_COUNT = 1
MAX_BUS_COUNT = 3
MIN_STALE_AFTER_SECONDS = 60
MAX_STALE_AFTER_SECONDS = 1800
MIN_DESTINATION_SCROLL_SPEED = 8
MAX_DESTINATION_SCROLL_SPEED = 80
MIN_CALENDAR_TASKS = 1
MAX_CALENDAR_TASKS = 6
DEFAULT_CALENDAR_TASKS = 6
DEFAULT_FOOTBALL_LOOKAHEAD_DAYS = 45
MAX_FOOTBALL_LOOKAHEAD_DAYS = 180
MIN_FOOTBALL_ANIMATION_SPEED = 20
MAX_FOOTBALL_ANIMATION_SPEED = 160
DEFAULT_FOOTBALL_ANIMATION_SPEED = 80
DEFAULT_SCOUTS_INTRO_TEXT = "Be prepared..."
MAX_SCOUTS_INTRO_TEXT_LENGTH = 48
MIN_CUBS_POLL_SECONDS = 3600
MAX_CUBS_POLL_SECONDS = 604800
DISPLAY_BRIGHTNESS_LEVELS = (25, 50, 75, 100)
DEFAULT_DISPLAY_BRIGHTNESS_PERCENT = 100
DEFAULT_RECYCLING_DURATION_SECONDS = 20
DEFAULT_RECYCLING_SCROLL_SPEED = 15
DEFAULT_RECYCLING_DAYS_BEFORE = 2
MIN_RECYCLING_SCROLL_SPEED = 1
MAX_RECYCLING_SCROLL_SPEED = 120
MAX_RECYCLING_DAYS_BEFORE = 14

DEPARTURE_NUMERIC_FIELDS = {
    "station_scroll_speed": {
        "minimum": MIN_STATION_SCROLL_SPEED,
        "maximum": MAX_STATION_SCROLL_SPEED,
        "default": DEFAULT_STATION_SCROLL_SPEED,
    },
    "station_list_spacing": {
        "minimum": MIN_STATION_LIST_SPACING,
        "maximum": MAX_STATION_LIST_SPACING,
        "default": DEFAULT_STATION_LIST_SPACING,
    },
    "upcoming_train_count": {
        "minimum": MIN_UPCOMING_TRAIN_COUNT,
        "maximum": MAX_UPCOMING_TRAIN_COUNT,
        "default": DEFAULT_UPCOMING_TRAIN_COUNT,
    },
    "upcoming_train_pause_seconds": {
        "minimum": MIN_UPCOMING_TRAIN_PAUSE_SECONDS,
        "maximum": MAX_UPCOMING_TRAIN_PAUSE_SECONDS,
        "default": DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS,
    },
    "no_services_duration_seconds": {
        "minimum": MIN_SCREEN_DURATION_SECONDS,
        "maximum": MAX_SCREEN_DURATION_SECONDS,
        "default": DEFAULT_NO_SERVICES_DURATION_SECONDS,
    },
}

QUEUE_TIMES_NUMERIC_FIELDS = {
    "queue_scroll_speed": {
        "minimum": MIN_QUEUE_SCROLL_SPEED,
        "maximum": MAX_QUEUE_SCROLL_SPEED,
        "default": DEFAULT_QUEUE_SCROLL_SPEED,
    },
    "queue_scroll_pause_seconds": {
        "minimum": MIN_QUEUE_SCROLL_PAUSE_SECONDS,
        "maximum": MAX_QUEUE_SCROLL_PAUSE_SECONDS,
        "default": DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS,
    },
}

CALENDAR_NUMERIC_FIELDS = {
    "visible_task_count": {
        "minimum": MIN_CALENDAR_TASKS,
        "maximum": MAX_CALENDAR_TASKS,
        "default": DEFAULT_CALENDAR_TASKS,
    },
}

DEFAULT_THORPE_RIDES = (
    "Hyperia",
    "Stealth",
    "The Swarm",
    "SAW - The Ride",
    "Nemesis Inferno",
    "Colossus",
    "Ghost Train",
    "Rush",
    "Detonator",
    "Tidal Wave",
)
LEGACY_DEFAULT_CHESSINGTON_RIDES = (
    "Vampire",
    "Dragon's Fury",
    "Mandrill Mayhem",
)
DEFAULT_CHESSINGTON_RIDES = LEGACY_DEFAULT_CHESSINGTON_RIDES + (
    "Rattlesnake",
    "Croc Drop",
    "ZUFARI",
)

FEED_REGISTRY = {
    "steam_train": {
        "label": "Steam train intro",
        "provider": "local_animation",
        "virtual": True,
        "mutable_fields": ("enabled", "animation_speed", "words"),
    },
    "departures": {
        "label": "Departures",
        "provider": "national_rail",
        "mutable_fields": (
            "enabled",
            "poll_seconds",
            "screen_duration_seconds",
            "no_services_duration_seconds",
            "station_scroll_speed",
            "station_list_spacing",
            "upcoming_train_count",
            "upcoming_train_pause_seconds",
        ),
        "advanced_fields": ("no_services_duration_seconds", "station_scroll_speed", "station_list_spacing", "upcoming_train_count", "upcoming_train_pause_seconds"),
        "screen_duration": True,
    },
    "queue_times": {
        "label": "Queue Times",
        "provider": "queue_times_group",
        "virtual": True,
        "mutable_fields": (
            "enabled",
            "poll_seconds",
            "screen_duration_seconds",
            "queue_scroll_speed",
            "queue_scroll_pause_seconds",
            "splash_enabled",
        ),
        "advanced_fields": ("queue_scroll_speed", "queue_scroll_pause_seconds", "splash_enabled"),
        "screen_duration": True,
    },
    "thorpe_park": {
        "label": "Thorpe Park",
        "provider": "queue_times",
        "park_id": 2,
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds", "rides"),
        "screen_duration": True,
        "rides": True,
    },
    "chessington": {
        "label": "Chessington World of Adventures",
        "provider": "queue_times",
        "park_id": 3,
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds", "rides"),
        "screen_duration": True,
        "rides": True,
    },
    "weather": {
        "label": "Weather",
        "provider": "open_meteo",
        "mutable_fields": (
            "enabled",
            "poll_seconds",
            "overview_enabled",
            "screen_duration_seconds",
            "today_enabled",
            "today_duration_seconds",
            "sun_enabled",
            "sun_duration_seconds",
        ),
        "screen_duration": True,
        "advanced_fields": (
            "overview_enabled",
            "today_enabled",
            "today_duration_seconds",
            "sun_enabled",
            "sun_duration_seconds",
        ),
    },
    "dad_joke": {
        "label": "Dad jokes",
        "display_group": "static_feeds",
        "provider": "icanhazdadjoke",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
        "screen_duration": True,
    },
    "random_fact": {
        "label": "Random facts",
        "display_group": "static_feeds",
        "provider": "uselessfacts.jsph.pl",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
        "screen_duration": True,
    },
    "quotes": {
        "label": "Quotes",
        "display_group": "static_feeds",
        "provider": "zenquotes.io",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
        "screen_duration": True,
    },
    "insult_of_hour": {
        "label": "Insult of the Hour",
        "display_group": "static_feeds",
        "provider": "insult.mattbas.org",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
        "screen_duration": True,
    },
    "today": {
        "label": "Today",
        "provider": "open_meteo",
        "display_group": "static_feeds",
        "mutable_fields": ("enabled", "screen_duration_seconds"),
        "screen_duration": True,
        "virtual": True,
    },
    "calendar": {
        "label": "Calendar",
        "provider": "todoist",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds", "visible_task_count"),
        "advanced_fields": ("visible_task_count",),
        "screen_duration": True,
    },
    "football_fixtures": {
        "label": "Football fixtures (Google Calendar)",
        "provider": "google_calendar",
        "display_group": "sports",
        "mutable_fields": (
            "enabled", "poll_seconds", "screen_duration_seconds", "lookahead_days", "animation_speed",
            "sporting_cp_enabled", "millwall_enabled", "portugal_enabled", "england_enabled",
        ),
        "advanced_fields": ("lookahead_days", "animation_speed"),
        "screen_duration": True,
    },
    "cubs": {
        "label": "Scouts · Beavers & Cubs",
        "provider": "cubs_ics",
        "display_group": "calendar",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds", "intro_text"),
        "advanced_fields": ("intro_text",),
        "screen_duration": True,
    },
    "flash": {
        "label": "Flash events",
        "provider": "mqtt_pending",
        "mutable_fields": ("enabled", "screen_duration_seconds"),
        "screen_duration": True,
        "flash": True,
    },
    "recycling": {
        "label": "Recycling / Next collection",
        "provider": "Home Assistant · local MQTT",
        "virtual": True,
        "mutable_fields": ("enabled", "screen_duration_seconds", "slide_speed"),
        "screen_duration": True,
    },
    "christmas": {
        "label": "Christmas tracker",
        "provider": "MatrixPortal firmware",
        "virtual": True,
        "mutable_fields": ("enabled",),
    },
    "sl7_bus": {
        "label": "SL7 bus departures",
        "provider": "transitous",
        "display_group": "transit",
        "mutable_fields": (
            "enabled", "heathrow_enabled", "new_malden_enabled",
            "bus_intro_enabled", "animation_speed", "words", "layout_mode",
            "screen_duration_seconds", "no_services_duration_seconds",
            "display_every_cycles", "upcoming_bus_count",
            "stale_after_seconds", "destination_scroll_speed",
        ),
        "advanced_fields": ("stale_after_seconds", "destination_scroll_speed"),
        "screen_duration": True,
    },
}


class RuntimeConfigConflict(RuntimeError):
    """The caller attempted to write an out-of-date config version."""


class RuntimeConfigValidationError(ValueError):
    """A requested runtime setting is not safe or supported."""


def _iso_now(utcnow=None) -> str:
    now = (utcnow or (lambda: datetime.now(timezone.utc)))()
    return now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _int_env(
    env: dict[str, str],
    name: str,
    default: int,
    minimum: int = MIN_POLL_SECONDS,
    maximum: int = MAX_POLL_SECONDS,
) -> int:
    try:
        value = int(env.get(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return min(maximum, max(minimum, value))


def _rides_env(env: dict[str, str], name: str, default: tuple[str, ...]) -> list[str]:
    raw = env.get(name, ",".join(default))
    values = [part.strip() for part in str(raw).split(",") if part.strip()]
    return values or list(default)


def default_runtime_config(env: dict[str, str] | None = None) -> dict[str, Any]:
    """Return safe defaults derived from non-secret deployment configuration."""
    env = dict(os.environ if env is None else env)
    thorpe_enabled = env.get("LED_THORPE_PARK_SOURCE", "queue_times").strip() != "off"
    weather_enabled = env.get("LED_WEATHER_SOURCE", "open_meteo").strip() != "off"
    calendar_enabled = env.get("LED_CALENDAR_SOURCE", "off").strip() != "off"
    thorpe_poll = _int_env(env, "LED_THORPE_PARK_CACHE_SECONDS", 300)
    result = {
        "config_version": 0,
        "display": {"brightness_percent": DEFAULT_DISPLAY_BRIGHTNESS_PERCENT},
        "feeds": {
            "steam_train": {
                "enabled": True,
                "animation_speed": DEFAULT_STEAM_TRAIN_SPEED,
                "words": DEFAULT_STEAM_TRAIN_WORDS,
            },
            "departures": {
                "enabled": True,
                "poll_seconds": _int_env(env, "LED_CACHE_SECONDS", 60),
                "screen_duration_seconds": 8,
                "no_services_duration_seconds": DEFAULT_NO_SERVICES_DURATION_SECONDS,
                "station_scroll_speed": DEFAULT_STATION_SCROLL_SPEED,
                "station_list_spacing": DEFAULT_STATION_LIST_SPACING,
                "upcoming_train_count": DEFAULT_UPCOMING_TRAIN_COUNT,
                "upcoming_train_pause_seconds": DEFAULT_UPCOMING_TRAIN_PAUSE_SECONDS,
            },
            "queue_times": {
                "enabled": True,
                "poll_seconds": thorpe_poll,
                "screen_duration_seconds": _int_env(
                    env,
                    "LED_QUEUE_TIMES_DURATION_SECONDS",
                    DEFAULT_QUEUE_SCREEN_DURATION_SECONDS,
                    minimum=MIN_SCREEN_DURATION_SECONDS,
                    maximum=MAX_SCREEN_DURATION_SECONDS,
                ),
                "queue_scroll_speed": _int_env(
                    env,
                    "LED_QUEUE_TIMES_SCROLL_SPEED",
                    DEFAULT_QUEUE_SCROLL_SPEED,
                    minimum=MIN_QUEUE_SCROLL_SPEED,
                    maximum=MAX_QUEUE_SCROLL_SPEED,
                ),
                "queue_scroll_pause_seconds": _int_env(
                    env,
                    "LED_QUEUE_TIMES_SCROLL_PAUSE_SECONDS",
                    DEFAULT_QUEUE_SCROLL_PAUSE_SECONDS,
                    minimum=MIN_QUEUE_SCROLL_PAUSE_SECONDS,
                    maximum=MAX_QUEUE_SCROLL_PAUSE_SECONDS,
                ),
                "splash_enabled": env.get("LED_QUEUE_TIMES_SPLASH", "off").strip().lower() in ("1", "true", "on", "yes"),
            },
            "thorpe_park": {
                "enabled": thorpe_enabled,
                "poll_seconds": thorpe_poll,
                "screen_duration_seconds": 8,
                "park_id": 2,
                "rides": _rides_env(env, "LED_THORPE_PARK_RIDES", DEFAULT_THORPE_RIDES),
            },
            "chessington": {
                "enabled": thorpe_enabled,
                "poll_seconds": _int_env(env, "LED_CHESSINGTON_CACHE_SECONDS", thorpe_poll),
                "screen_duration_seconds": 8,
                "park_id": 3,
                "rides": _rides_env(env, "LED_CHESSINGTON_RIDES", DEFAULT_CHESSINGTON_RIDES),
            },
            "weather": {
                "enabled": weather_enabled,
                "poll_seconds": _int_env(env, "LED_WEATHER_CACHE_SECONDS", 600),
                "overview_enabled": True,
                "screen_duration_seconds": _int_env(
                    env,
                    "LED_WEATHER_DURATION_SECONDS",
                    DEFAULT_WEATHER_SCREEN_DURATION_SECONDS,
                    minimum=MIN_SCREEN_DURATION_SECONDS,
                    maximum=MAX_SCREEN_DURATION_SECONDS,
                ),
                "today_enabled": True,
                "today_duration_seconds": DEFAULT_WEATHER_TODAY_DURATION_SECONDS,
                "sun_enabled": True,
                "sun_duration_seconds": DEFAULT_WEATHER_SUN_DURATION_SECONDS,
            },
            "dad_joke": {
                "enabled": False,
                "poll_seconds": 3600,
                "screen_duration_seconds": 15,
            },
            "random_fact": {
                "enabled": False,
                "poll_seconds": 3600,
                "screen_duration_seconds": 15,
            },
            "quotes": {
                "enabled": False,
                "poll_seconds": 7200,
                "screen_duration_seconds": 30,
            },
            "insult_of_hour": {
                "enabled": False,
                "poll_seconds": 3600,
                "screen_duration_seconds": 15,
            },
            "today": {"enabled": False, "screen_duration_seconds": 15},
            "calendar": {
                "enabled": calendar_enabled,
                "poll_seconds": _int_env(env, "LED_TODOIST_CACHE_SECONDS", 300),
                "screen_duration_seconds": _int_env(
                    env,
                    "LED_CALENDAR_DURATION_SECONDS",
                    10,
                    minimum=MIN_SCREEN_DURATION_SECONDS,
                    maximum=MAX_SCREEN_DURATION_SECONDS,
                ),
                "visible_task_count": _int_env(
                    env,
                    "LED_TODOIST_VISIBLE_TASKS",
                    DEFAULT_CALENDAR_TASKS,
                    minimum=MIN_CALENDAR_TASKS,
                    maximum=MAX_CALENDAR_TASKS,
                ),
            },
            "football_fixtures": {
                # Provider source selection does not implicitly opt in to publishing.
                # Keep migration/first deploy safe until the admin enables it.
                "enabled": False,
                "poll_seconds": _int_env(env, "LED_FOOTBALL_FIXTURE_CACHE_SECONDS", 900),
                "screen_duration_seconds": _int_env(env, "LED_FOOTBALL_FIXTURE_DURATION_SECONDS", 20,
                    minimum=MIN_SCREEN_DURATION_SECONDS, maximum=MAX_SCREEN_DURATION_SECONDS),
                "lookahead_days": _int_env(env, "LED_FOOTBALL_FIXTURE_LOOKAHEAD_DAYS",
                    DEFAULT_FOOTBALL_LOOKAHEAD_DAYS, minimum=1, maximum=MAX_FOOTBALL_LOOKAHEAD_DAYS),
                "animation_speed": DEFAULT_FOOTBALL_ANIMATION_SPEED,
                "sporting_cp_enabled": True,
                "millwall_enabled": True,
                "portugal_enabled": False,
                "england_enabled": False,
            },
            "cubs": {
                "enabled": False,
                "poll_seconds": _int_env(env, "LED_CUBS_CACHE_SECONDS", 86400,
                                         minimum=MIN_CUBS_POLL_SECONDS, maximum=MAX_CUBS_POLL_SECONDS),
                "screen_duration_seconds": 10,
                "intro_text": DEFAULT_SCOUTS_INTRO_TEXT,
            },
            "flash": {
                # This is deliberately disabled until Home Assistant issue #4
                # and the broker path have been reviewed and enabled together.
                "enabled": False,
                "screen_duration_seconds": _int_env(
                    env, "LED_FLASH_SCREEN_DURATION_SECONDS", DEFAULT_FLASH_SCREEN_DURATION_SECONDS,
                    minimum=MIN_FLASH_SCREEN_DURATION_SECONDS,
                    maximum=MAX_FLASH_SCREEN_DURATION_SECONDS,
                ),
            },
            "recycling": {
                "enabled": True,
                "screen_duration_seconds": DEFAULT_RECYCLING_DURATION_SECONDS,
                "slide_speed": DEFAULT_RECYCLING_SCROLL_SPEED,
            },
            "christmas": {"enabled": True},
            "sl7_bus": {
                "enabled": False,
                "heathrow_enabled": True,
                "new_malden_enabled": True,
                "bus_intro_enabled": True,
                "animation_speed": DEFAULT_STEAM_TRAIN_SPEED,
                "words": DEFAULT_BUS_INTRO_WORDS,
                "layout_mode": "split_columns",
                "screen_duration_seconds": 8,
                "no_services_duration_seconds": DEFAULT_NO_SERVICES_DURATION_SECONDS,
                "display_every_cycles": 1,
                "upcoming_bus_count": 3,
                "stale_after_seconds": 180,
                "destination_scroll_speed": 20,
            },
        },
        "updated_at": None,
        "updated_by": "system:defaults",
    }
    for feed_id in SCREEN_SCHEDULE_FEEDS:
        result["feeds"][feed_id]["schedule_windows"] = []
    return result


def schema_metadata() -> dict[str, Any]:
    feeds = {}
    for feed_id, definition in FEED_REGISTRY.items():
        fields: dict[str, Any] = {
            "enabled": {"type": "boolean"},
            "poll_seconds": {
                "type": "integer",
                "minimum": MIN_CUBS_POLL_SECONDS if feed_id == "cubs" else (MIN_INSULT_POLL_SECONDS if feed_id == "insult_of_hour" else MIN_POLL_SECONDS),
                "maximum": MAX_CUBS_POLL_SECONDS if feed_id == "cubs" else MAX_POLL_SECONDS,
            },
        }
        if definition.get("screen_duration") and not definition.get("flash"):
            fields["screen_duration_seconds"] = {
                "type": "integer",
                "minimum": MIN_FLASH_SCREEN_DURATION_SECONDS if definition.get("flash") else MIN_SCREEN_DURATION_SECONDS,
                "maximum": MAX_FLASH_SCREEN_DURATION_SECONDS if definition.get("flash") else MAX_SCREEN_DURATION_SECONDS,
            }
        if feed_id == "steam_train":
            fields["animation_speed"] = {
                "type": "integer",
                "minimum": MIN_STEAM_TRAIN_SPEED,
                "maximum": MAX_STEAM_TRAIN_SPEED,
            }
            fields["words"] = {
                "type": "string",
                "maximumLength": MAX_STEAM_TRAIN_WORDS_LENGTH,
            }
        if feed_id == "departures":
            for field, metadata in DEPARTURE_NUMERIC_FIELDS.items():
                fields[field] = {
                    "type": "integer",
                    "minimum": metadata["minimum"],
                    "maximum": metadata["maximum"],
                }
        if feed_id == "queue_times":
            for field, metadata in QUEUE_TIMES_NUMERIC_FIELDS.items():
                fields[field] = {
                    "type": "integer",
                    "minimum": metadata["minimum"],
                    "maximum": metadata["maximum"],
                }
            fields["splash_enabled"] = {"type": "boolean"}
        if feed_id == "weather":
            fields["overview_enabled"] = {"type": "boolean"}
            fields["today_enabled"] = {"type": "boolean"}
            fields["today_duration_seconds"] = {
                "type": "integer",
                "minimum": MIN_SCREEN_DURATION_SECONDS,
                "maximum": MAX_SCREEN_DURATION_SECONDS,
            }
            fields["sun_enabled"] = {"type": "boolean"}
            fields["sun_duration_seconds"] = {
                "type": "integer",
                "minimum": MIN_SCREEN_DURATION_SECONDS,
                "maximum": MAX_SCREEN_DURATION_SECONDS,
            }
        if feed_id == "cubs":
            fields["intro_text"] = {"type": "string", "maximumLength": MAX_SCOUTS_INTRO_TEXT_LENGTH}
        if feed_id == "calendar":
            for field, metadata in CALENDAR_NUMERIC_FIELDS.items():
                fields[field] = {
                    "type": "integer",
                    "minimum": metadata["minimum"],
                    "maximum": metadata["maximum"],
                }
        if feed_id == "football_fixtures":
            for team in ("sporting_cp", "millwall", "portugal", "england"):
                fields[team + "_enabled"] = {"type": "boolean"}
            fields["lookahead_days"] = {"type": "integer", "minimum": 1, "maximum": MAX_FOOTBALL_LOOKAHEAD_DAYS}
            fields["animation_speed"] = {
                "type": "integer", "minimum": MIN_FOOTBALL_ANIMATION_SPEED,
                "maximum": MAX_FOOTBALL_ANIMATION_SPEED,
            }
        if feed_id == "recycling":
            fields["slide_speed"] = {"type": "integer", "minimum": MIN_RECYCLING_SCROLL_SPEED, "maximum": MAX_RECYCLING_SCROLL_SPEED}
        if feed_id == "sl7_bus":
            fields["heathrow_enabled"] = {"type": "boolean"}
            fields["new_malden_enabled"] = {"type": "boolean"}
            fields["bus_intro_enabled"] = {"type": "boolean"}
            fields["animation_speed"] = {
                "type": "integer", "minimum": MIN_STEAM_TRAIN_SPEED, "maximum": MAX_STEAM_TRAIN_SPEED,
            }
            fields["words"] = {"type": "string", "maximumLength": MAX_STEAM_TRAIN_WORDS_LENGTH}
            fields["layout_mode"] = {"type": "select", "values": ["split_columns", "separate_stops"]}
            fields["no_services_duration_seconds"] = {
                "type": "integer", "minimum": MIN_SCREEN_DURATION_SECONDS, "maximum": MAX_SCREEN_DURATION_SECONDS,
            }
            fields["display_every_cycles"] = {"type": "integer", "minimum": 1, "maximum": 6}
            fields["upcoming_bus_count"] = {"type": "integer", "minimum": MIN_BUS_COUNT, "maximum": MAX_BUS_COUNT}
            fields["stale_after_seconds"] = {"type": "integer", "minimum": MIN_STALE_AFTER_SECONDS, "maximum": MAX_STALE_AFTER_SECONDS}
            fields["destination_scroll_speed"] = {"type": "integer", "minimum": MIN_DESTINATION_SCROLL_SPEED, "maximum": MAX_DESTINATION_SCROLL_SPEED}
        if feed_id in SCREEN_SCHEDULE_FEEDS:
            fields["schedule_windows"] = {"type": "array", "maximumItems": MAX_SCHEDULE_WINDOWS, "items": {"cron": "five-field numeric cron", "duration_minutes": {"minimum": 1, "maximum": MAX_SCHEDULE_WINDOW_MINUTES}}}
        mutable_fields = list(definition["mutable_fields"])
        advanced_fields = list(definition.get("advanced_fields", ()))
        if feed_id in SCREEN_SCHEDULE_FEEDS:
            mutable_fields.append("schedule_windows")
            advanced_fields.append("schedule_windows")
        if definition.get("rides"):
            fields["rides"] = {"type": "array", "items": {"type": "string"}, "ordered": True}
        feeds[feed_id] = {
            "label": definition["label"],
            "provider": definition["provider"],
            "mutable_fields": mutable_fields,
            **({"display_group": definition["display_group"]} if definition.get("display_group") else {}),
            "fields": fields,
            **({"advanced_fields": advanced_fields} if advanced_fields else {}),
            **({"park_id": definition["park_id"]} if "park_id" in definition else {}),
            **({"virtual": True} if definition.get("virtual") else {}),
        }
    return {
        "feeds": feeds,
        "display": {
            "label": "Display",
            "provider": "MatrixPortal",
            "mutable_fields": ["brightness_percent"],
            "fields": {
                "brightness_percent": {
                    "type": "select",
                    "values": list(DISPLAY_BRIGHTNESS_LEVELS),
                },
            },
        },
    }


def validate_display_patch(patch: Any) -> dict[str, int]:
    if not isinstance(patch, dict) or set(patch) != {"brightness_percent"}:
        raise RuntimeConfigValidationError("display patch must contain brightness_percent only")
    percent = patch["brightness_percent"]
    if isinstance(percent, bool) or not isinstance(percent, int) or percent not in DISPLAY_BRIGHTNESS_LEVELS:
        allowed = ", ".join(str(value) for value in DISPLAY_BRIGHTNESS_LEVELS)
        raise RuntimeConfigValidationError(f"display.brightness_percent must be one of {allowed}")
    return {"brightness_percent": percent}


def _normalize_number(value: Any) -> Any:
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    if isinstance(value, dict):
        return {key: _normalize_number(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_number(item) for item in value]
    return value


def _validate_integer(feed_id: str, field: str, value: Any, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeConfigValidationError(f"{feed_id}.{field} must be an integer")
    if not minimum <= value <= maximum:
        raise RuntimeConfigValidationError(
            f"{feed_id}.{field} must be between {minimum} and {maximum}"
        )
    return value


def validate_feed_patch(
    feed_id: str,
    patch: Any,
    available_rides: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    if feed_id not in FEED_REGISTRY:
        raise RuntimeConfigValidationError(f"unknown feed_id: {feed_id}")
    if not isinstance(patch, dict) or not patch:
        raise RuntimeConfigValidationError("patch must be a non-empty JSON object")
    definition = FEED_REGISTRY[feed_id]
    allowed = set(definition["mutable_fields"])
    if feed_id in SCREEN_SCHEDULE_FEEDS:
        allowed.add("schedule_windows")
    unknown = set(patch) - allowed
    if unknown:
        raise RuntimeConfigValidationError(
            f"{feed_id} contains unknown or non-mutable fields: {', '.join(sorted(unknown))}"
        )

    result: dict[str, Any] = {}
    if "schedule_windows" in patch:
        windows = patch["schedule_windows"]
        if not isinstance(windows, list) or len(windows) > MAX_SCHEDULE_WINDOWS:
            raise RuntimeConfigValidationError(f"{feed_id}.schedule_windows must be a list of at most {MAX_SCHEDULE_WINDOWS} windows")
        checked = []
        for index, window in enumerate(windows):
            if not isinstance(window, dict) or set(window) != {"cron", "duration_minutes"}:
                raise RuntimeConfigValidationError(f"{feed_id}.schedule_windows[{index}] must contain cron and duration_minutes")
            cron = window["cron"]
            if not isinstance(cron, str) or len(cron) > 100 or not cron.strip():
                raise RuntimeConfigValidationError(f"{feed_id}.schedule_windows[{index}].cron must be non-empty cron text")
            try:
                parse_cron_schedule(cron)
            except ValueError as error:
                raise RuntimeConfigValidationError(f"{feed_id}.schedule_windows[{index}].cron: {error}") from error
            duration = _validate_integer(feed_id, f"schedule_windows[{index}].duration_minutes", window["duration_minutes"], 1, MAX_SCHEDULE_WINDOW_MINUTES)
            checked.append({"cron": cron.strip(), "duration_minutes": duration})
        result["schedule_windows"] = checked
    if "enabled" in patch:
        if not isinstance(patch["enabled"], bool):
            raise RuntimeConfigValidationError(f"{feed_id}.enabled must be boolean")
        result["enabled"] = patch["enabled"]
    if "poll_seconds" in patch:
        result["poll_seconds"] = _validate_integer(
            feed_id, "poll_seconds", patch["poll_seconds"],
            MIN_CUBS_POLL_SECONDS if feed_id == "cubs" else (MIN_INSULT_POLL_SECONDS if feed_id == "insult_of_hour" else MIN_POLL_SECONDS),
            MAX_CUBS_POLL_SECONDS if feed_id == "cubs" else MAX_POLL_SECONDS
        )
    if "screen_duration_seconds" in patch:
        result["screen_duration_seconds"] = _validate_integer(
            feed_id,
            "screen_duration_seconds",
            patch["screen_duration_seconds"],
            MIN_FLASH_SCREEN_DURATION_SECONDS if FEED_REGISTRY[feed_id].get("flash") else MIN_SCREEN_DURATION_SECONDS,
            MAX_FLASH_SCREEN_DURATION_SECONDS if FEED_REGISTRY[feed_id].get("flash") else MAX_SCREEN_DURATION_SECONDS,
        )
    if "animation_speed" in patch:
        minimum, maximum = (
            (MIN_FOOTBALL_ANIMATION_SPEED, MAX_FOOTBALL_ANIMATION_SPEED)
            if feed_id == "football_fixtures"
            else (MIN_STEAM_TRAIN_SPEED, MAX_STEAM_TRAIN_SPEED)
        )
        result["animation_speed"] = _validate_integer(
            feed_id,
            "animation_speed",
            patch["animation_speed"],
            minimum,
            maximum,
        )
    if "words" in patch:
        words = patch["words"]
        if not isinstance(words, str):
            raise RuntimeConfigValidationError(f"{feed_id}.words must be a string")
        words = words.strip()
        if any(ord(char) < 32 or ord(char) > 126 for char in words):
            raise RuntimeConfigValidationError(
                f"{feed_id}.words must contain printable ASCII characters only"
            )
        if len(words) > MAX_STEAM_TRAIN_WORDS_LENGTH:
            raise RuntimeConfigValidationError(
                f"{feed_id}.words must be at most {MAX_STEAM_TRAIN_WORDS_LENGTH} characters"
            )
        result["words"] = words
    for field in ("overview_enabled", "today_enabled", "sun_enabled"):
        if field in patch:
            if not isinstance(patch[field], bool):
                raise RuntimeConfigValidationError(f"{feed_id}.{field} must be boolean")
            result[field] = patch[field]
    for field in ("today_duration_seconds", "sun_duration_seconds"):
        if field in patch:
            result[field] = _validate_integer(
                feed_id, field, patch[field], MIN_SCREEN_DURATION_SECONDS, MAX_SCREEN_DURATION_SECONDS
            )
    for field, metadata in DEPARTURE_NUMERIC_FIELDS.items():
        if field in patch:
            result[field] = _validate_integer(
                feed_id,
                field,
                patch[field],
                metadata["minimum"],
                metadata["maximum"],
            )
    for field, metadata in QUEUE_TIMES_NUMERIC_FIELDS.items():
        if field in patch:
            result[field] = _validate_integer(
                feed_id,
                field,
                patch[field],
                metadata["minimum"],
                metadata["maximum"],
            )
    if feed_id == "cubs" and "intro_text" in patch:
        intro_text = patch["intro_text"]
        if not isinstance(intro_text, str) or not intro_text.strip():
            raise RuntimeConfigValidationError("cubs.intro_text must be non-empty text")
        if len(intro_text) > MAX_SCOUTS_INTRO_TEXT_LENGTH or any(ord(char) < 32 or ord(char) > 126 for char in intro_text):
            raise RuntimeConfigValidationError("cubs.intro_text must be at most 48 printable ASCII characters")
        result["intro_text"] = intro_text.strip()
    for field, metadata in CALENDAR_NUMERIC_FIELDS.items():
        if field in patch:
            result[field] = _validate_integer(
                feed_id,
                field,
                patch[field],
                metadata["minimum"],
                metadata["maximum"],
            )
    if feed_id == "football_fixtures":
        for team in ("sporting_cp", "millwall", "portugal", "england"):
            field = team + "_enabled"
            if field in patch:
                if not isinstance(patch[field], bool):
                    raise RuntimeConfigValidationError(f"{feed_id}.{field} must be boolean")
                result[field] = patch[field]
    if feed_id == "football_fixtures" and "lookahead_days" in patch:
        result["lookahead_days"] = _validate_integer(
            feed_id, "lookahead_days", patch["lookahead_days"], 1, MAX_FOOTBALL_LOOKAHEAD_DAYS
        )
    if feed_id == "recycling":
        for field, minimum, maximum in (
            ("slide_speed", MIN_RECYCLING_SCROLL_SPEED, MAX_RECYCLING_SCROLL_SPEED),
        ):
            if field in patch:
                result[field] = _validate_integer(feed_id, field, patch[field], minimum, maximum)
    if feed_id == "sl7_bus":
        if "layout_mode" in patch:
            if patch["layout_mode"] not in ("split_columns", "separate_stops") or not isinstance(patch["layout_mode"], str):
                raise RuntimeConfigValidationError("sl7_bus.layout_mode must be split_columns or separate_stops")
            result["layout_mode"] = patch["layout_mode"]
        for field in ("heathrow_enabled", "new_malden_enabled", "bus_intro_enabled"):
            if field in patch:
                if not isinstance(patch[field], bool):
                    raise RuntimeConfigValidationError(f"{feed_id}.{field} must be boolean")
                result[field] = patch[field]
        ranges = {
            "no_services_duration_seconds": (MIN_SCREEN_DURATION_SECONDS, MAX_SCREEN_DURATION_SECONDS),
            "display_every_cycles": (1, 6),
            "upcoming_bus_count": (MIN_BUS_COUNT, MAX_BUS_COUNT),
            "stale_after_seconds": (MIN_STALE_AFTER_SECONDS, MAX_STALE_AFTER_SECONDS),
            "destination_scroll_speed": (MIN_DESTINATION_SCROLL_SPEED, MAX_DESTINATION_SCROLL_SPEED),
        }
        for field, (minimum, maximum) in ranges.items():
            if field in patch:
                result[field] = _validate_integer(feed_id, field, patch[field], minimum, maximum)
    if "splash_enabled" in patch:
        if not isinstance(patch["splash_enabled"], bool):
            raise RuntimeConfigValidationError(f"{feed_id}.splash_enabled must be boolean")
        result["splash_enabled"] = patch["splash_enabled"]
    if "rides" in patch:
        raw_rides = patch["rides"]
        if not isinstance(raw_rides, list) or any(not isinstance(name, str) for name in raw_rides):
            raise RuntimeConfigValidationError(f"{feed_id}.rides must be an array of strings")
        rides = [name.strip() for name in raw_rides]
        if any(not name for name in rides):
            raise RuntimeConfigValidationError(f"{feed_id}.rides cannot contain empty names")
        folded = [name.casefold() for name in rides]
        if len(folded) != len(set(folded)):
            raise RuntimeConfigValidationError(f"{feed_id}.rides cannot contain duplicates")
        if available_rides is not None:
            canonical = {name.casefold(): name for name in available_rides}
            unknown_rides = [name for name in rides if name.casefold() not in canonical]
            if unknown_rides:
                raise RuntimeConfigValidationError(
                    f"{feed_id}.rides contains unavailable rides: {', '.join(unknown_rides)}"
                )
            rides = [canonical[name.casefold()] for name in rides]
        result["rides"] = rides
    return result


def validate_runtime_config(value: Any) -> dict[str, Any]:
    """Validate a complete persisted config without accepting arbitrary fields."""
    if not isinstance(value, dict):
        raise RuntimeConfigValidationError("runtime configuration must be an object")
    defaults = default_runtime_config({})
    raw_display = value.get("display", copy.deepcopy(defaults["display"]))
    display = validate_display_patch(raw_display)
    raw_feeds = value.get("feeds")
    if not isinstance(raw_feeds, dict):
        raise RuntimeConfigValidationError("feeds must be an object")
    raw_feeds = copy.deepcopy(raw_feeds)
    supported_feed_ids = set(FEED_REGISTRY)
    supplied_feed_ids = set(raw_feeds)
    missing_feed_ids = supported_feed_ids - supplied_feed_ids
    unknown_feed_ids = supplied_feed_ids - supported_feed_ids
    # The five original v1 feeds must already exist in saved configurations.
    # Every other registered feed was introduced later and can be backfilled
    # from its safe default. Derive these additions from the registry so that
    # introducing another screen cannot break old DynamoDB configurations.
    original_feed_ids = {"departures", "thorpe_park", "chessington", "weather", "calendar"}
    if unknown_feed_ids or missing_feed_ids.intersection(original_feed_ids):
        raise RuntimeConfigValidationError("feeds must contain exactly the supported v1 feed IDs")
    for feed_id in missing_feed_ids:
        raw_feeds[feed_id] = copy.deepcopy(defaults["feeds"][feed_id])

    feeds: dict[str, Any] = {}
    for feed_id, default_feed in defaults["feeds"].items():
        raw_value = raw_feeds[feed_id]
        if not isinstance(raw_value, dict):
            raise RuntimeConfigValidationError(f"{feed_id} must be an object")
        raw = copy.deepcopy(raw_value)
        legacy_cron = raw.pop("cron_schedule", "")
        if feed_id in SCREEN_SCHEDULE_FEEDS:
            raw.setdefault("schedule_windows", ([{"cron": legacy_cron, "duration_minutes": 1}] if legacy_cron else []))
        if feed_id == "recycling":
            raw.pop("days_before_collection", None)
        # Read old persisted configurations, but never expose or accept new
        # writes to the retired display-frequency setting.
        if feed_id != "sl7_bus":
            raw.pop("display_every_cycles", None)
        if feed_id == "departures":
            for field, metadata in DEPARTURE_NUMERIC_FIELDS.items():
                raw.setdefault(field, metadata["default"])
        if feed_id == "calendar":
            for field, metadata in CALENDAR_NUMERIC_FIELDS.items():
                raw.setdefault(field, metadata["default"])
        if feed_id == "weather":
            raw.setdefault("overview_enabled", True)
            raw.setdefault("screen_duration_seconds", DEFAULT_WEATHER_SCREEN_DURATION_SECONDS)
            raw.setdefault("today_enabled", True)
            raw.setdefault("today_duration_seconds", DEFAULT_WEATHER_TODAY_DURATION_SECONDS)
            raw.setdefault("sun_enabled", True)
            raw.setdefault("sun_duration_seconds", DEFAULT_WEATHER_SUN_DURATION_SECONDS)
        if feed_id == "sl7_bus":
            # Upgrade saved admin settings from before the optional bus intro
            # controls were introduced. Keep all existing SL7 settings intact.
            raw.setdefault("bus_intro_enabled", True)
            raw.setdefault("animation_speed", DEFAULT_STEAM_TRAIN_SPEED)
            raw.setdefault("words", DEFAULT_BUS_INTRO_WORDS)
            raw.setdefault("layout_mode", "split_columns")
            # Previous versions allowed up to five rows, but the actual
            # 32-pixel matrix can show at most three legible rows.
            raw["upcoming_bus_count"] = min(
                MAX_BUS_COUNT, raw.get("upcoming_bus_count", 3)
            ) if isinstance(raw.get("upcoming_bus_count"), int) and not isinstance(raw.get("upcoming_bus_count"), bool) else raw.get("upcoming_bus_count")
        if feed_id == "football_fixtures":
            # Version 100 predates this required field. Backfill only the new
            # field; supplied values still pass normal strict validation.
            raw.setdefault("animation_speed", DEFAULT_FOOTBALL_ANIMATION_SPEED)
            for team in ("sporting_cp", "millwall", "portugal", "england"):
                field = team + "_enabled"
                raw.setdefault(field, default_feed[field])
        if feed_id == "cubs":
            # Accept earlier Cubs configuration and migrate to the new intro.
            raw.pop("visible_event_count", None)
            raw.setdefault("intro_text", DEFAULT_SCOUTS_INTRO_TEXT)
            # Upgrade only the original default; leave custom taglines intact.
            if raw["intro_text"] == "Be Prepared for...":
                raw["intro_text"] = DEFAULT_SCOUTS_INTRO_TEXT
        if feed_id == "insult_of_hour":
            # Older admins accepted a sub-hourly interval. Migrate that saved
            # setting without discarding the rest of the user configuration.
            interval = raw.get("poll_seconds")
            if isinstance(interval, int) and not isinstance(interval, bool):
                raw["poll_seconds"] = max(MIN_INSULT_POLL_SECONDS, interval)
        read_only = {"park_id"} if "park_id" in default_feed else set()
        expected = set(FEED_REGISTRY[feed_id]["mutable_fields"]) | read_only
        if feed_id in SCREEN_SCHEDULE_FEEDS:
            expected.add("schedule_windows")
        # Older saved configs may predate the SL7 frequency control. Keep that
        # migration additive without making the legacy migration test (or an
        # older persisted document) acquire a new key unexpectedly.
        if feed_id == "sl7_bus" and "display_every_cycles" not in raw:
            expected.discard("display_every_cycles")
        if set(raw) != expected:
            raise RuntimeConfigValidationError(f"{feed_id} contains missing or unknown fields")
        normalized = validate_feed_patch(
            feed_id,
            {key: raw[key] for key in expected - read_only},
        )
        if read_only:
            park_id = raw.get("park_id")
            if park_id != FEED_REGISTRY[feed_id]["park_id"]:
                raise RuntimeConfigValidationError(f"{feed_id}.park_id is fixed")
            normalized["park_id"] = park_id
        feeds[feed_id] = normalized

    version = value.get("config_version", 0)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise RuntimeConfigValidationError("config_version must be a non-negative integer")
    updated_at = value.get("updated_at")
    updated_by = value.get("updated_by", "system:unknown")
    if updated_at is not None and not isinstance(updated_at, str):
        raise RuntimeConfigValidationError("updated_at must be a string or null")
    if not isinstance(updated_by, str) or not updated_by:
        raise RuntimeConfigValidationError("updated_by must be a non-empty string")
    return {
        "config_version": version,
        "display": display,
        "feeds": feeds,
        "updated_at": updated_at,
        "updated_by": updated_by,
    }


class RuntimeConfigStore:
    """Single-item DynamoDB store with optimistic concurrency."""

    def __init__(self, table_name: str, table=None, defaults=None, utcnow=None):
        self.table_name = table_name
        self.utcnow = utcnow
        self.defaults = copy.deepcopy(defaults or default_runtime_config())
        if table is None:
            import boto3

            table = boto3.resource("dynamodb").Table(table_name)
        self.table = table

    def load(self) -> dict[str, Any]:
        response = self.table.get_item(Key={"config_id": CONFIG_ID}, ConsistentRead=True)
        item = response.get("Item")
        if not item:
            return copy.deepcopy(self.defaults)
        item = _normalize_number(item)
        item.pop("config_id", None)
        return validate_runtime_config(item)

    def _upgrade_legacy_chessington_defaults(self, current: dict[str, Any]) -> dict[str, Any]:
        """Expand the untouched three-ride seed without overriding user-managed config."""
        if current.get("updated_by") != "system:defaults":
            return current
        rides = current.get("feeds", {}).get("chessington", {}).get("rides")
        if rides != list(LEGACY_DEFAULT_CHESSINGTON_RIDES):
            return current

        upgraded = copy.deepcopy(current)
        upgraded["feeds"]["chessington"]["rides"] = list(DEFAULT_CHESSINGTON_RIDES)
        upgraded["config_version"] = current["config_version"] + 1
        upgraded["updated_at"] = _iso_now(self.utcnow)
        item = {"config_id": CONFIG_ID, **upgraded}
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="config_version = :expected",
                ExpressionAttributeValues={":expected": current["config_version"]},
            )
            return upgraded
        except Exception as error:
            if _is_conditional_failure(error):
                return self.load()
            raise

    def ensure(self) -> dict[str, Any]:
        current = self.load()
        if current["config_version"] != 0:
            return self._upgrade_legacy_chessington_defaults(current)
        seeded = copy.deepcopy(current)
        seeded["config_version"] = 1
        seeded["updated_at"] = _iso_now(self.utcnow)
        seeded["updated_by"] = "system:defaults"
        item = {"config_id": CONFIG_ID, **seeded}
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(config_id)")
            return seeded
        except Exception as error:
            if _is_conditional_failure(error):
                return self._upgrade_legacy_chessington_defaults(self.load())
            raise

    def patch_feed(
        self,
        feed_id: str,
        patch: Any,
        *,
        expected_version: int,
        updated_by: str,
        available_rides: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        current = self.load()
        if current["config_version"] != expected_version:
            raise RuntimeConfigConflict(
                f"configuration version is {current['config_version']}, not {expected_version}"
            )
        normalized_patch = validate_feed_patch(feed_id, patch, available_rides)
        next_config = copy.deepcopy(current)
        next_config["feeds"][feed_id].update(normalized_patch)
        next_config["config_version"] = expected_version + 1
        next_config["updated_at"] = _iso_now(self.utcnow)
        next_config["updated_by"] = updated_by
        item = {"config_id": CONFIG_ID, **next_config}
        try:
            if expected_version == 0:
                self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(config_id)")
            else:
                self.table.put_item(
                    Item=item,
                    ConditionExpression="config_version = :expected",
                    ExpressionAttributeValues={":expected": expected_version},
                )
        except Exception as error:
            if _is_conditional_failure(error):
                raise RuntimeConfigConflict("configuration changed concurrently") from error
            raise
        return next_config, list(normalized_patch)

    def patch_display(
        self,
        patch: Any,
        *,
        expected_version: int,
        updated_by: str,
    ) -> tuple[dict[str, Any], list[str]]:
        current = self.load()
        if current["config_version"] != expected_version:
            raise RuntimeConfigConflict(
                f"configuration version is {current['config_version']}, not {expected_version}"
            )
        normalized_patch = validate_display_patch(patch)
        next_config = copy.deepcopy(current)
        next_config["display"].update(normalized_patch)
        next_config["config_version"] = expected_version + 1
        next_config["updated_at"] = _iso_now(self.utcnow)
        next_config["updated_by"] = updated_by
        item = {"config_id": CONFIG_ID, **next_config}
        try:
            if expected_version == 0:
                self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(config_id)")
            else:
                self.table.put_item(
                    Item=item,
                    ConditionExpression="config_version = :expected",
                    ExpressionAttributeValues={":expected": expected_version},
                )
        except Exception as error:
            if _is_conditional_failure(error):
                raise RuntimeConfigConflict("configuration changed concurrently") from error
            raise
        return next_config, list(normalized_patch)


def _is_conditional_failure(error: Exception) -> bool:
    response = getattr(error, "response", {}) or {}
    code = str((response.get("Error") or {}).get("Code") or "")
    return code == "ConditionalCheckFailedException"
