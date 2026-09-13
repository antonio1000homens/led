"""Cloudflare Access authenticated runtime control API for the LED service."""

from __future__ import annotations

import copy
import json
import os
import re
from typing import Any

from queue_times import QueueTimesProvider
from runtime_config import (
    FEED_REGISTRY,
    RuntimeConfigConflict,
    RuntimeConfigStore,
    RuntimeConfigValidationError,
    default_runtime_config,
    schema_metadata,
)

STATE_KEY = "state/feed-cache.json"
SCREENS_KEY = "api/screens"
MAX_BODY_BYTES = 32768
_JWK_CLIENTS: dict[str, Any] = {}


class AuthenticationError(RuntimeError):
    pass


class StatusStore:
    """Read-only access to publisher state required by status/options endpoints."""

    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3

            client = boto3.client("s3")
        self.client = client

    def _load(self, key: str, default: Any) -> Any:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            response = getattr(error, "response", {}) or {}
            code = str((response.get("Error") or {}).get("Code") or "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return copy.deepcopy(default)
            raise
        return json.loads(response["Body"].read().decode("utf-8"))

    def feed_state(self) -> dict[str, Any]:
        payload = self._load(STATE_KEY, {"feeds": {}})
        feeds = payload.get("feeds") if isinstance(payload, dict) else None
        return feeds if isinstance(feeds, dict) else {}

    def screens_state(self) -> dict[str, Any]:
        payload = self._load(SCREENS_KEY, {})
        return payload if isinstance(payload, dict) else {}


class PublisherInvoker:
    def __init__(self, function_name: str, client=None):
        self.function_name = function_name
        if client is None:
            import boto3

            client = boto3.client("lambda")
        self.client = client

    def invoke(self) -> None:
        self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=b'{"source":"runtime-control-api"}',
        )


def _headers(event: dict[str, Any]) -> dict[str, str]:
    return {str(name).lower(): str(value) for name, value in (event.get("headers") or {}).items()}


def _response(status: int, payload: Any = None, *, version: int | None = None):
    headers = {"content-type": "application/json", "cache-control": "no-store"}
    if version is not None:
        headers["etag"] = f'"{version}"'
    body = "" if payload is None else json.dumps(payload, separators=(",", ":"))
    return {"statusCode": status, "headers": headers, "body": body}


def _request_method(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    return str((request_context.get("http") or {}).get("method") or event.get("httpMethod") or "").upper()


def _request_path(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    return str(event.get("rawPath") or (request_context.get("http") or {}).get("path") or event.get("path") or "")


def _request_id(event: dict[str, Any]) -> str:
    request_context = event.get("requestContext") or {}
    return str(request_context.get("requestId") or (request_context.get("http") or {}).get("requestId") or "unknown")


def _jwt_client(team_domain: str):
    try:
        import jwt
    except ImportError as error:  # pragma: no cover - packaging failure guard
        raise AuthenticationError("JWT validation dependency is unavailable") from error
    certs_url = team_domain.rstrip("/") + "/cdn-cgi/access/certs"
    client = _JWK_CLIENTS.get(certs_url)
    if client is None:
        client = jwt.PyJWKClient(certs_url, cache_keys=True, lifespan=3600)
        _JWK_CLIENTS[certs_url] = client
    return client


def authenticate_access(event: dict[str, Any], env: dict[str, str] | None = None) -> tuple[str, dict[str, Any]]:
    """Validate the Access application JWT and return an audit-safe identity."""
    env = dict(os.environ if env is None else env)
    team_domain = env.get("CF_ACCESS_TEAM_DOMAIN", "").strip().rstrip("/")
    audience = env.get("CF_ACCESS_AUD", "").strip()
    if not team_domain or not audience:
        raise AuthenticationError("Cloudflare Access validation is not configured")
    token = _headers(event).get("cf-access-jwt-assertion", "").strip()
    if not token:
        raise AuthenticationError("missing Cloudflare Access assertion")
    try:
        import jwt

        signing_key = _jwt_client(team_domain).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=team_domain,
            options={"require": ["exp", "iss", "aud"]},
        )
    except Exception as error:
        raise AuthenticationError("invalid Cloudflare Access assertion") from error

    email = str(claims.get("email") or "").strip().lower()
    if email:
        return f"human:{email}", claims
    service_id = str(claims.get("service_token_id") or claims.get("common_name") or "").strip()
    if service_id:
        return f"machine:{service_id}", claims
    raise AuthenticationError("Access assertion does not contain an attributable identity")


def _expected_version(event: dict[str, Any], body: dict[str, Any]) -> int:
    raw = _headers(event).get("if-match", "").strip()
    if raw:
        raw = raw.removeprefix("W/").strip().strip('"')
    elif "config_version" in body:
        raw = str(body.pop("config_version"))
    else:
        raise RuntimeConfigValidationError("If-Match or config_version is required")
    try:
        version = int(raw)
    except (TypeError, ValueError) as error:
        raise RuntimeConfigValidationError("configuration version must be an integer") from error
    if version < 0:
        raise RuntimeConfigValidationError("configuration version must be non-negative")
    return version


def _known_rides_from_state(feed_id: str, status_store: StatusStore) -> list[str]:
    feed = status_store.feed_state().get(feed_id) or {}
    data = feed.get("data") if isinstance(feed, dict) else None
    rides = data.get("rides") if isinstance(data, dict) else None
    if not isinstance(rides, list):
        return []
    return [
        str(ride.get("name") or "").strip()
        for ride in rides
        if isinstance(ride, dict) and str(ride.get("name") or "").strip()
    ]


def ride_options(feed_id: str, config: dict[str, Any], status_store: StatusStore, provider_factory=QueueTimesProvider) -> list[str]:
    definition = FEED_REGISTRY.get(feed_id) or {}
    if not definition.get("rides"):
        raise RuntimeConfigValidationError(f"{feed_id} does not expose ride choices")
    choices = _known_rides_from_state(feed_id, status_store)
    if not choices:
        try:
            choices = [ride["name"] for ride in provider_factory(definition["park_id"]).fetch()]
        except Exception:
            # Keep the control plane usable during an upstream outage, but only
            # allow already configured names until fresh choices are available.
            choices = list(config["feeds"][feed_id].get("rides") or [])
    seen = set()
    ordered = []
    for name in choices:
        key = name.casefold()
        if key not in seen:
            seen.add(key)
            ordered.append(name)
    return ordered


def _config_payload(config: dict[str, Any], status_store: StatusStore) -> dict[str, Any]:
    metadata = schema_metadata()
    for feed_id, definition in FEED_REGISTRY.items():
        if definition.get("rides"):
            metadata["feeds"][feed_id]["available_rides"] = ride_options(feed_id, config, status_store)
    return {**config, "schema": metadata}


def _feed_health(enabled: bool, state: dict[str, Any]) -> str:
    if not enabled:
        return "disabled"
    if not state or state.get("data") is None:
        return "unavailable"
    if state.get("stale"):
        return "stale"
    return "ok"


def _status_payload(config: dict[str, Any], status_store: StatusStore) -> dict[str, Any]:
    feed_state = status_store.feed_state()
    feeds = {}
    for feed_id, definition in FEED_REGISTRY.items():
        effective = config["feeds"][feed_id]
        state = feed_state.get(feed_id) or {}
        feeds[feed_id] = {
            "enabled": effective["enabled"],
            "provider": definition["provider"],
            "health": _feed_health(effective["enabled"], state),
            "last_successful_refresh": state.get("last_success_at"),
            "last_attempted_refresh": state.get("last_attempt_at"),
            "stale": bool(state.get("stale")) if effective["enabled"] else False,
            "poll_seconds": effective["poll_seconds"],
        }
    screens = status_store.screens_state()
    return {
        "config_version": config["config_version"],
        "feeds": feeds,
        "screens": {
            "generated_at": screens.get("fetched_at"),
            "config_version": screens.get("config_version"),
        },
    }


def _audit(identity: str, feed_id: str, fields: list[str], previous_version: int, new_version: int, request_id: str) -> None:
    print(
        json.dumps(
            {
                "event": "runtime_config_mutation",
                "identity": identity,
                "feed_id": feed_id,
                "fields": fields,
                "previous_config_version": previous_version,
                "new_config_version": new_version,
                "request_id": request_id,
            },
            separators=(",", ":"),
        )
    )


def lambda_handler(event, context):
    del context
    event = event or {}
    try:
        identity, _claims = authenticate_access(event)
    except AuthenticationError as error:
        return _response(401, {"error": str(error)})

    table_name = os.environ.get("RUNTIME_CONFIG_TABLE", "").strip()
    bucket = os.environ.get("STATE_BUCKET", "").strip()
    publisher_name = os.environ.get("PUBLISHER_FUNCTION_NAME", "").strip()
    if not table_name or not bucket or not publisher_name:
        return _response(500, {"error": "control plane is not fully configured"})

    store = RuntimeConfigStore(table_name, defaults=default_runtime_config())
    status_store = StatusStore(bucket)
    method = _request_method(event)
    path = _request_path(event).rstrip("/") or "/"

    try:
        if method == "GET" and path == "/api/control/v1/config":
            config = store.ensure()
            return _response(200, _config_payload(config, status_store), version=config["config_version"])

        if method == "GET" and path == "/api/control/v1/status":
            config = store.ensure()
            return _response(200, _status_payload(config, status_store), version=config["config_version"])

        options_match = re.fullmatch(r"/api/control/v1/feeds/([^/]+)/options", path)
        if method == "GET" and options_match:
            feed_id = options_match.group(1)
            config = store.ensure()
            choices = ride_options(feed_id, config, status_store)
            return _response(
                200,
                {"feed_id": feed_id, "options": [{"value": name, "label": name} for name in choices]},
                version=config["config_version"],
            )

        patch_match = re.fullmatch(r"/api/control/v1/feeds/([^/]+)", path)
        if method == "PATCH" and patch_match:
            body_text = event.get("body") or ""
            if len(body_text.encode("utf-8")) > MAX_BODY_BYTES:
                return _response(413, {"error": "request too large"})
            try:
                body = json.loads(body_text)
            except (TypeError, json.JSONDecodeError):
                return _response(400, {"error": "body must be valid JSON"})
            if not isinstance(body, dict):
                return _response(400, {"error": "body must be a JSON object"})
            expected = _expected_version(event, body)
            feed_id = patch_match.group(1)
            config = store.ensure()
            choices = ride_options(feed_id, config, status_store) if "rides" in body else None
            updated, fields = store.patch_feed(
                feed_id,
                body,
                expected_version=expected,
                updated_by=identity,
                available_rides=choices,
            )
            _audit(identity, feed_id, fields, expected, updated["config_version"], _request_id(event))
            PublisherInvoker(publisher_name).invoke()
            return _response(200, _config_payload(updated, status_store), version=updated["config_version"])

        return _response(404, {"error": "not found"})
    except RuntimeConfigConflict as error:
        return _response(412, {"error": str(error)})
    except RuntimeConfigValidationError as error:
        return _response(400, {"error": str(error)})
    except Exception:
        # Do not leak provider/AWS responses or credentials to control clients.
        print(json.dumps({"event": "control_api_failure", "request_id": _request_id(event)}))
        return _response(500, {"error": "control request failed"})
