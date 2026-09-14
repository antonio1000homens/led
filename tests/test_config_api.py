import copy
import json
import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

import config_api
from runtime_config import default_runtime_config


class FakeSigningKey:
    def __init__(self, key):
        self.key = key


class FakeJwkClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        del token
        return FakeSigningKey(self.key)


class FakeStatusStore:
    def __init__(self):
        ride = lambda name: {"name": name, "open": True, "wait_minutes": 10}
        self.feeds = {
            "thorpe_park": {"data": {"rides": [ride("Hyperia"), ride("Stealth")]}, "stale": False},
            "chessington": {"data": {"rides": [ride("Vampire"), ride("Mandrill Mayhem")]}, "stale": False},
        }

    def feed_state(self):
        return copy.deepcopy(self.feeds)

    def screens_state(self):
        return {"fetched_at": "2026-09-13T18:00:00Z", "config_version": 4}


class FakeRuntimeStore:
    def __init__(self):
        self.config = default_runtime_config({})
        self.config.update(config_version=4, updated_at="2026-09-13T17:00:00Z", updated_by="human:old@example.com")
        self.calls = []

    def ensure(self):
        return copy.deepcopy(self.config)

    def patch_feed(self, feed_id, body, **kwargs):
        self.calls.append((feed_id, copy.deepcopy(body), kwargs))
        updated = copy.deepcopy(self.config)
        updated["feeds"][feed_id].update(body)
        updated["config_version"] = kwargs["expected_version"] + 1
        updated["updated_by"] = kwargs["updated_by"]
        self.config = updated
        return copy.deepcopy(updated), list(body)


class FakeInvoker:
    calls = 0

    def __init__(self, function_name):
        self.function_name = function_name

    def invoke(self):
        type(self).calls += 1


class ConfigApiTests(unittest.TestCase):
    def setUp(self):
        self.team = "https://example.cloudflareaccess.com"
        self.audience = "a" * 32
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

    def token(self, **overrides):
        claims = {
            "iss": self.team,
            "aud": [self.audience],
            "exp": int(time.time()) + 120,
            "iat": int(time.time()) - 1,
            "type": "app",
            "email": "admin@example.com",
            "sub": "user-123",
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test"})

    def authenticate(self, token):
        event = {"headers": {"Cf-Access-Jwt-Assertion": token}}
        env = {"CF_ACCESS_TEAM_DOMAIN": self.team, "CF_ACCESS_AUD": self.audience}
        with patch.object(config_api, "_jwt_client", return_value=FakeJwkClient(self.public_key)):
            return config_api.authenticate_access(event, env)

    def test_access_jwt_accepts_human_and_service_token_identities(self):
        identity, _ = self.authenticate(self.token())
        self.assertEqual(identity, "human:admin@example.com")
        service = self.token(email=None, sub="", common_name="ha-client.access")
        identity, _ = self.authenticate(service)
        self.assertEqual(identity, "machine:ha-client.access")

    def test_access_jwt_rejects_bad_audience_issuer_expiry_and_missing_assertion(self):
        for token in (
            self.token(aud=["wrong"]),
            self.token(iss="https://other.cloudflareaccess.com"),
            self.token(exp=int(time.time()) - 10),
        ):
            with self.assertRaises(config_api.AuthenticationError):
                self.authenticate(token)
        with self.assertRaises(config_api.AuthenticationError):
            config_api.authenticate_access({}, {"CF_ACCESS_TEAM_DOMAIN": self.team, "CF_ACCESS_AUD": self.audience})

    def test_session_bootstrap_redirects_after_access_auth_without_runtime_dependencies(self):
        event = {
            "rawPath": "/api/control/v1/session",
            "requestContext": {"http": {"method": "GET"}},
            "headers": {},
        }
        with patch.dict(config_api.os.environ, {}, clear=True), \
             patch.object(config_api, "authenticate_access", return_value=("human:admin@example.com", {})):
            response = config_api.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 302)
        self.assertEqual(response["headers"]["location"], "/admin?access=1")
        self.assertEqual(response["headers"]["cache-control"], "no-store")

    def test_patch_requires_concurrency_version_and_triggers_async_rebuild(self):
        runtime = FakeRuntimeStore()
        status = FakeStatusStore()
        FakeInvoker.calls = 0
        event = {
            "rawPath": "/api/control/v1/feeds/thorpe_park",
            "requestContext": {"http": {"method": "PATCH"}, "requestId": "req-1"},
            "headers": {"If-Match": '"4"'},
            "body": json.dumps({"enabled": False, "poll_seconds": 600, "rides": ["Stealth", "Hyperia"]}),
        }
        env = {
            "RUNTIME_CONFIG_TABLE": "table",
            "STATE_BUCKET": "bucket",
            "PUBLISHER_FUNCTION_NAME": "publisher",
        }
        with patch.dict(config_api.os.environ, env, clear=True), \
             patch.object(config_api, "authenticate_access", return_value=("human:admin@example.com", {})), \
             patch.object(config_api, "RuntimeConfigStore", return_value=runtime), \
             patch.object(config_api, "StatusStore", return_value=status), \
             patch.object(config_api, "PublisherInvoker", FakeInvoker):
            response = config_api.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 200)
        payload = json.loads(response["body"])
        self.assertEqual(payload["config_version"], 5)
        self.assertEqual(payload["feeds"]["thorpe_park"]["rides"], ["Stealth", "Hyperia"])
        self.assertEqual(runtime.calls[0][2]["expected_version"], 4)
        self.assertEqual(FakeInvoker.calls, 1)

    def test_patch_without_if_match_is_rejected(self):
        runtime = FakeRuntimeStore()
        event = {
            "rawPath": "/api/control/v1/feeds/departures",
            "requestContext": {"http": {"method": "PATCH"}},
            "headers": {},
            "body": json.dumps({"enabled": False}),
        }
        env = {"RUNTIME_CONFIG_TABLE": "table", "STATE_BUCKET": "bucket", "PUBLISHER_FUNCTION_NAME": "publisher"}
        with patch.dict(config_api.os.environ, env, clear=True), \
             patch.object(config_api, "authenticate_access", return_value=("machine:ha.access", {})), \
             patch.object(config_api, "RuntimeConfigStore", return_value=runtime), \
             patch.object(config_api, "StatusStore", return_value=FakeStatusStore()):
            response = config_api.lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)
        self.assertIn("If-Match", json.loads(response["body"])["error"])

    def test_status_does_not_expose_secrets_or_provider_error_bodies(self):
        config = default_runtime_config({})
        config["config_version"] = 7
        store = FakeStatusStore()
        store.feeds["departures"] = {
            "last_attempt_at": "2026-09-13T17:59:00Z",
            "last_success_at": None,
            "stale": True,
            "data": None,
            "provider_error": "SECRET upstream body",
        }
        payload = config_api._status_payload(config, store)
        encoded = json.dumps(payload)
        self.assertNotIn("SECRET", encoded)
        self.assertEqual(payload["feeds"]["departures"]["health"], "unavailable")


if __name__ == "__main__":
    unittest.main()
