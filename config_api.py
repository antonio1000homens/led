"""Authenticated admin configuration API for LED screen rotation settings."""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

CONFIG_KEY = "state/config.json"

DEFAULT_DISPLAY_CONFIG = {
    "version": 1,
    "themeParks": {
        "thorpePark": {
            "enabled": True,
            "entriesPerPage": 3,
            "pageDurationSeconds": 3,
            "iterations": 1,
        },
        "chessington": {
            "enabled": True,
            "entriesPerPage": 3,
            "pageDurationSeconds": 3,
            "iterations": 1,
        },
    },
}

PARK_KEYS = ("thorpePark", "chessington")
BOUNDS = {
    "entriesPerPage": (1, 10),
    "pageDurationSeconds": (1, 60),
    "iterations": (1, 10),
}


def validate_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("configuration must be an object")
    allowed_top = {"version", "themeParks"}
    if set(value) - allowed_top:
        raise ValueError("configuration contains unknown fields")
    parks = value.get("themeParks")
    if not isinstance(parks, dict) or set(parks) != set(PARK_KEYS):
        raise ValueError("themeParks must contain thorpePark and chessington")
    result = {"version": 1, "themeParks": {}}
    for key in PARK_KEYS:
        park = parks[key]
        if not isinstance(park, dict):
            raise ValueError(f"{key} must be an object")
        allowed = {"enabled", *BOUNDS}
        if set(park) != allowed:
            raise ValueError(f"{key} contains missing or unknown fields")
        if not isinstance(park["enabled"], bool):
            raise ValueError(f"{key}.enabled must be boolean")
        normalized = {"enabled": park["enabled"]}
        for field, (minimum, maximum) in BOUNDS.items():
            raw = park[field]
            if isinstance(raw, bool) or not isinstance(raw, int) or not minimum <= raw <= maximum:
                raise ValueError(f"{key}.{field} must be an integer between {minimum} and {maximum}")
            normalized[field] = raw
        result["themeParks"][key] = normalized
    return result


class ConfigStore:
    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3
            client = boto3.client("s3")
        self.client = client

    def load(self) -> dict[str, Any]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=CONFIG_KEY)
        except Exception as error:
            meta = getattr(error, "response", {}) or {}
            code = str((meta.get("Error") or {}).get("Code") or "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return json.loads(json.dumps(DEFAULT_DISPLAY_CONFIG))
            raise
        return validate_config(json.loads(response["Body"].read().decode("utf-8")))

    def save(self, value: Any) -> dict[str, Any]:
        config = validate_config(value)
        self.client.put_object(
            Bucket=self.bucket,
            Key=CONFIG_KEY,
            Body=json.dumps(config, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-store",
            ServerSideEncryption="AES256",
        )
        return config


def _response(status: int, payload: dict[str, Any]):
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json", "cache-control": "no-store"},
        "body": json.dumps(payload, separators=(",", ":")),
    }


def _authorized(event: dict[str, Any], expected: str) -> bool:
    headers = event.get("headers") or {}
    supplied = ""
    for name, value in headers.items():
        if str(name).lower() == "authorization":
            supplied = str(value or "")
            break
    prefix = "Bearer "
    if not supplied.startswith(prefix) or not expected:
        return False
    return hmac.compare_digest(supplied[len(prefix):], expected)


def lambda_handler(event, context):
    del context
    token = os.environ.get("ADMIN_TOKEN", "")
    if not _authorized(event or {}, token):
        return _response(401, {"error": "unauthorized"})
    method = str(((event or {}).get("requestContext") or {}).get("http", {}).get("method") or (event or {}).get("httpMethod") or "").upper()
    store = ConfigStore(os.environ["STATE_BUCKET"])
    if method == "GET":
        return _response(200, store.load())
    if method == "PUT":
        body = (event or {}).get("body") or ""
        if len(body) > 16384:
            return _response(413, {"error": "request too large"})
        try:
            value = json.loads(body)
            saved = store.save(value)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            return _response(400, {"error": str(error)})
        return _response(200, saved)
    return _response(405, {"error": "method not allowed"})
