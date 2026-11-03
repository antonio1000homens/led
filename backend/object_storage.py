"""JSON object storage for the publisher's small live state objects."""

from __future__ import annotations

import json
import os
import copy
import time
from typing import Any

class JsonObjectStore:
    def __init__(self, bucket: str, client: Any, *, server_side_encryption: bool):
        self.bucket = bucket
        self.client = client
        self.server_side_encryption = server_side_encryption

    def get_json(self, key: str, default: Any) -> Any:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            response = getattr(error, "response", {}) or {}
            code = str((response.get("Error") or {}).get("Code") or "")
            if code in ("NoSuchKey", "404", "NotFound"):
                return copy.deepcopy(default)
            raise
        with response["Body"] as body:
            return json.loads(body.read().decode("utf-8"))

    def get_bytes(self, key: str) -> tuple[bytes, dict[str, str]]:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        with response["Body"] as body:
            data = body.read()
        metadata = {}
        for source, target in (("ContentType", "ContentType"), ("CacheControl", "CacheControl")):
            if response.get(source):
                metadata[target] = str(response[source])
        return data, metadata

    def put_bytes(self, key: str, data: bytes, metadata: dict[str, str] | None = None) -> None:
        args = {"Bucket": self.bucket, "Key": key, "Body": data}
        args.update(metadata or {})
        if self.server_side_encryption:
            args["ServerSideEncryption"] = "AES256"
        self.client.put_object(**args)

    def put_json(self, key: str, payload: Any, *, cache_control: str) -> None:
        self.put_bytes(
            key,
            json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            {"ContentType": "application/json", "CacheControl": cache_control},
        )


class MirroredJsonObjectStore:
    """Read from the primary and best-effort mirror each successful write."""

    def __init__(self, primary: JsonObjectStore, mirror: JsonObjectStore, mirror_name: str):
        self.primary = primary
        self.mirror = mirror
        self.mirror_name = mirror_name

    def get_json(self, key: str, default: Any) -> Any:
        return self.primary.get_json(key, default)

    def put_json(self, key: str, payload: Any, *, cache_control: str) -> None:
        self.primary.put_json(key, payload, cache_control=cache_control)
        try:
            self.mirror.put_json(key, payload, cache_control=cache_control)
        except Exception as error:
            # A mirror outage must not stop the active publisher or screen API.
            print(json.dumps({
                "event": "object_store_mirror_failed",
                "backend": self.mirror_name,
                "key": key,
                "error_class": type(error).__name__,
            }, separators=(",", ":")))


def _r2_credentials(parameter_name: str, ssm_client: Any = None) -> tuple[str, str]:
    if ssm_client is None:
        import boto3
        ssm_client = boto3.client("ssm")
    response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
    value = json.loads(response["Parameter"]["Value"])
    access_key_id = str(value.get("access_key_id", "")).strip()
    secret_access_key = str(value.get("secret_access_key", "")).strip()
    if not access_key_id or not secret_access_key:
        raise ValueError("R2 S3 credentials parameter is missing required fields")
    return access_key_id, secret_access_key


class RefreshingR2Client:
    """Refresh credentials in warm Lambda containers and retry once on auth errors."""

    AUTH_ERROR_CODES = {"AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch", "ExpiredToken", "InvalidToken"}

    def __init__(self, account_id: str, parameter_name: str, *, ssm_client: Any = None,
                 refresh_seconds: int = 300, clock=None, client_factory=None):
        self.account_id = account_id
        self.parameter_name = parameter_name
        self.ssm_client = ssm_client
        self.refresh_seconds = refresh_seconds
        self.clock = clock or time.monotonic
        self.client_factory = client_factory
        self._client = None
        self._refresh_at = 0.0

    def _current_client(self, *, force: bool = False):
        now = self.clock()
        if force or self._client is None or now >= self._refresh_at:
            access_key_id, secret_access_key = _r2_credentials(self.parameter_name, self.ssm_client)
            if self.client_factory is not None:
                client = self.client_factory(access_key_id, secret_access_key)
            else:
                import boto3
                from botocore.config import Config

                config_args = {"signature_version": "s3v4"}
                try:
                    config = Config(
                        **config_args,
                        request_checksum_calculation="when_required",
                        response_checksum_validation="when_required",
                    )
                except TypeError:
                    config = Config(**config_args)
                client = boto3.client(
                    "s3",
                    endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
                    region_name="auto",
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    config=config,
                )
            self._client = client
            self._refresh_at = now + self.refresh_seconds
        return self._client

    def _call(self, operation: str, **kwargs):
        client = self._current_client()
        try:
            return getattr(client, operation)(**kwargs)
        except Exception as error:
            response = getattr(error, "response", {}) or {}
            code = str((response.get("Error") or {}).get("Code") or "")
            if code not in self.AUTH_ERROR_CODES:
                raise
            # Credentials may have been revoked before the periodic refresh.
            # Retry once using the latest value; do not log credential material.
            return getattr(self._current_client(force=True), operation)(**kwargs)

    def get_object(self, **kwargs):
        return self._call("get_object", **kwargs)

    def put_object(self, **kwargs):
        return self._call("put_object", **kwargs)


def _r2_client(account_id: str, parameter_name: str, ssm_client: Any = None, r2_client: Any = None):
    if r2_client is not None:
        return r2_client
    return RefreshingR2Client(account_id, parameter_name, ssm_client=ssm_client)


def create_json_object_store(
    bucket: str,
    env: dict[str, str] | None = None,
    *,
    s3_client: Any = None,
    ssm_client: Any = None,
    r2_client: Any = None,
):
    env = dict(os.environ if env is None else env)
    primary_name = env.get("STATE_STORAGE_BACKEND", "s3").strip().lower()
    mirror_name = env.get("STATE_STORAGE_MIRROR", "none").strip().lower()
    r2_bucket = env.get("R2_BUCKET_NAME", "led-live-state").strip()
    account_id = env.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    parameter_name = env.get(
        "R2_CREDENTIALS_PARAMETER_NAME", "/led/deploy/cloudflare/r2-s3-credentials"
    ).strip()

    if primary_name not in ("s3", "r2"):
        raise ValueError("STATE_STORAGE_BACKEND must be s3 or r2")
    if mirror_name not in ("none", "s3", "r2"):
        raise ValueError("STATE_STORAGE_MIRROR must be none, s3 or r2")
    if mirror_name == primary_name:
        raise ValueError("STATE_STORAGE_MIRROR must differ from STATE_STORAGE_BACKEND")

    if s3_client is None:
        import boto3
        s3_client = boto3.client("s3")

    def backend(name: str) -> JsonObjectStore:
        if name == "s3":
            return JsonObjectStore(bucket, s3_client, server_side_encryption=True)
        if not account_id:
            raise ValueError("CLOUDFLARE_ACCOUNT_ID is required for R2 storage")
        if not r2_bucket:
            raise ValueError("R2_BUCKET_NAME is required for R2 storage")
        return JsonObjectStore(
            r2_bucket,
            _r2_client(account_id, parameter_name, ssm_client, r2_client),
            server_side_encryption=False,
        )

    primary = backend(primary_name)
    if mirror_name == "none":
        return primary
    return MirroredJsonObjectStore(primary, backend(mirror_name), mirror_name)
