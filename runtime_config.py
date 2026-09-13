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

CONFIG_ID = "runtime"
MIN_POLL_SECONDS = 60
MAX_POLL_SECONDS = 86400
MIN_SCREEN_DURATION_SECONDS = 2
MAX_SCREEN_DURATION_SECONDS = 300

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
DEFAULT_CHESSINGTON_RIDES = (
    "Vampire",
    "Dragon's Fury",
    "Mandrill Mayhem",
)

FEED_REGISTRY = {
    "departures": {
        "label": "Departures",
        "provider": "national_rail",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
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
        "mutable_fields": ("enabled", "poll_seconds"),
        "screen_duration": False,
    },
    "calendar": {
        "label": "Calendar",
        "provider": "todoist",
        "mutable_fields": ("enabled", "poll_seconds", "screen_duration_seconds"),
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


def _int_env(env: dict[str, str], name: str, default: int, minimum: int = MIN_POLL_SECONDS) -> int:
    try:
        value = int(env.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return max(minimum, value)


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
    return {
        "config_version": 0,
        "feeds": {
            "departures": {
                "enabled": True,
                "poll_seconds": _int_env(env, "LED_CACHE_SECONDS", 60),
                "screen_duration_seconds": 8,
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
            },
            "calendar": {
                "enabled": calendar_enabled,
                "poll_seconds": _int_env(env, "LED_TODOIST_CACHE_SECONDS", 300),
                "screen_duration_seconds": _int_env(
                    env, "LED_CALENDAR_DURATION_SECONDS", 10, minimum=MIN_SCREEN_DURATION_SECONDS
                ),
            },
        },
        "updated_at": None,
        "updated_by": "system:defaults",
    }


def schema_metadata() -> dict[str, Any]:
    feeds = {}
    for feed_id, definition in FEED_REGISTRY.items():
        fields: dict[str, Any] = {
            "enabled": {"type": "boolean"},
            "poll_seconds": {
                "type": "integer",
                "minimum": MIN_POLL_SECONDS,
                "maximum": MAX_POLL_SECONDS,
            },
        }
        if definition.get("screen_duration"):
            fields["screen_duration_seconds"] = {
                "type": "integer",
                "minimum": MIN_SCREEN_DURATION_SECONDS,
                "maximum": MAX_SCREEN_DURATION_SECONDS,
            }
        if definition.get("rides"):
            fields["rides"] = {"type": "array", "items": {"type": "string"}, "ordered": True}
        feeds[feed_id] = {
            "label": definition["label"],
            "provider": definition["provider"],
            "mutable_fields": list(definition["mutable_fields"]),
            "fields": fields,
            **({"park_id": definition["park_id"]} if "park_id" in definition else {}),
        }
    return {"feeds": feeds}


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
    unknown = set(patch) - allowed
    if unknown:
        raise RuntimeConfigValidationError(
            f"{feed_id} contains unknown or non-mutable fields: {', '.join(sorted(unknown))}"
        )

    result: dict[str, Any] = {}
    if "enabled" in patch:
        if not isinstance(patch["enabled"], bool):
            raise RuntimeConfigValidationError(f"{feed_id}.enabled must be boolean")
        result["enabled"] = patch["enabled"]
    if "poll_seconds" in patch:
        result["poll_seconds"] = _validate_integer(
            feed_id, "poll_seconds", patch["poll_seconds"], MIN_POLL_SECONDS, MAX_POLL_SECONDS
        )
    if "screen_duration_seconds" in patch:
        result["screen_duration_seconds"] = _validate_integer(
            feed_id,
            "screen_duration_seconds",
            patch["screen_duration_seconds"],
            MIN_SCREEN_DURATION_SECONDS,
            MAX_SCREEN_DURATION_SECONDS,
        )
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
    raw_feeds = value.get("feeds")
    if not isinstance(raw_feeds, dict):
        raise RuntimeConfigValidationError("feeds must be an object")
    if set(raw_feeds) != set(FEED_REGISTRY):
        raise RuntimeConfigValidationError("feeds must contain exactly the supported v1 feed IDs")

    feeds: dict[str, Any] = {}
    for feed_id, default_feed in defaults["feeds"].items():
        raw = raw_feeds[feed_id]
        if not isinstance(raw, dict):
            raise RuntimeConfigValidationError(f"{feed_id} must be an object")
        read_only = {"park_id"} if "park_id" in default_feed else set()
        expected = set(FEED_REGISTRY[feed_id]["mutable_fields"]) | read_only
        if set(raw) != expected:
            raise RuntimeConfigValidationError(f"{feed_id} contains missing or unknown fields")
        normalized = validate_feed_patch(
            feed_id,
            {key: raw[key] for key in FEED_REGISTRY[feed_id]["mutable_fields"]},
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

    def ensure(self) -> dict[str, Any]:
        current = self.load()
        if current["config_version"] != 0:
            return current
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
                return self.load()
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


def _is_conditional_failure(error: Exception) -> bool:
    response = getattr(error, "response", {}) or {}
    code = str((response.get("Error") or {}).get("Code") or "")
    return code == "ConditionalCheckFailedException"
