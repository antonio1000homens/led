#!/usr/bin/env python3
"""Authorize the LED Todoist integration and store OAuth state in SSM Parameter Store.

The default parameter is a Standard SecureString:
    /led/todoist/oauth

For a new authorization, add this redirect URI to the Todoist integration:
    http://127.0.0.1:8765/callback

For migrations from the previous Secrets Manager implementation, pass
--migrate-secret-id with the existing secret ARN/name. Client secrets and
OAuth tokens are never printed.
"""

from __future__ import annotations

import argparse
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen
import webbrowser


AUTHORIZE_URL = "https://app.todoist.com/oauth/authorize"
TOKEN_URL = "https://api.todoist.com/oauth/access_token"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"
DEFAULT_REGION = "eu-west-2"
DEFAULT_SCOPE = "data:read"
DEFAULT_PARAMETER_NAME = "/led/todoist/oauth"


class BootstrapError(RuntimeError):
    pass


def aws(args, region, profile=None, input_text=None):
    command = ["aws"]
    if profile:
        command.extend(["--profile", profile])
    command.extend(["--region", region])
    command.extend(args)
    try:
        result = subprocess.run(
            command,
            input=input_text,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as error:
        raise BootstrapError("AWS CLI is required") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or "AWS CLI command failed").strip().splitlines()[-1]
        raise BootstrapError(detail) from error
    return result.stdout.strip()


def exchange_code(client_id, client_secret, code, redirect_uri):
    data = urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")
    request = Request(
        TOKEN_URL,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "led-information-board-oauth-bootstrap/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise BootstrapError("Todoist rejected the authorization-code exchange") from error
    except Exception as error:
        raise BootstrapError("Todoist authorization-code exchange failed") from error
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise BootstrapError("Todoist returned an invalid token response")
    if not payload.get("refresh_token"):
        raise BootstrapError(
            "Todoist did not issue a refresh token. Enable refresh tokens for this integration and authorize again."
        )
    return payload


def parse_callback(value, expected_state):
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if query.get("state", [""])[0] != expected_state:
        raise BootstrapError("Todoist OAuth state did not match; authorization was aborted")
    error = query.get("error", [""])[0]
    if error:
        raise BootstrapError("Todoist authorization failed: " + error)
    code = query.get("code", [""])[0]
    if not code:
        raise BootstrapError("Todoist callback did not contain an authorization code")
    return code


def wait_for_local_callback(redirect_uri, expected_state, authorize_url, timeout=300):
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or ""
    if parsed.scheme != "http" or host not in ("127.0.0.1", "localhost"):
        raise BootstrapError("Automatic callback requires an http://127.0.0.1 or http://localhost redirect URI")
    port = parsed.port or 80
    callback_path = parsed.path or "/"
    result = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            incoming = urlparse(self.path)
            status = 200
            message = "Todoist authorization complete. You can close this tab."
            try:
                if incoming.path != callback_path:
                    raise BootstrapError("Unexpected callback path")
                result["code"] = parse_callback(self.path, expected_state)
            except Exception as error:
                result["error"] = error
                status = 400
                message = "Todoist authorization failed. Return to the terminal for details."
            body = message.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            del format, args

    server = HTTPServer((host, port), Handler)
    server.timeout = 1
    deadline = time.monotonic() + timeout
    print("Opening Todoist authorization in your browser...")
    print("If the browser does not open, visit this URL:")
    print(authorize_url)
    webbrowser.open(authorize_url)
    while "code" not in result and "error" not in result and time.monotonic() < deadline:
        server.handle_request()
    server.server_close()
    if "error" in result:
        raise BootstrapError(str(result["error"]))
    if "code" not in result:
        raise BootstrapError("Timed out waiting for the Todoist OAuth callback")
    return result["code"]


def validate_oauth_payload(payload):
    if not isinstance(payload, dict):
        raise BootstrapError("Todoist OAuth payload is not a JSON object")
    required = ("client_id", "client_secret", "refresh_token")
    if any(not str(payload.get(name) or "").strip() for name in required):
        raise BootstrapError("Todoist OAuth payload is missing client_id, client_secret or refresh_token")
    return payload


def load_secrets_manager_secret(secret_id, region, profile):
    value = aws(
        [
            "secretsmanager",
            "get-secret-value",
            "--secret-id",
            secret_id,
            "--query",
            "SecretString",
            "--output",
            "text",
        ],
        region,
        profile,
    )
    try:
        return validate_oauth_payload(json.loads(value))
    except json.JSONDecodeError as error:
        raise BootstrapError("Existing Secrets Manager Todoist secret is not valid JSON") from error


def persist_parameter(parameter_name, payload, region, profile):
    validate_oauth_payload(payload)
    request = {
        "Name": parameter_name,
        "Description": "Todoist OAuth client credentials and rotating tokens for the LED publisher.",
        "Value": json.dumps(payload, separators=(",", ":")),
        "Type": "SecureString",
        "Tier": "Standard",
        "Overwrite": True,
    }
    fd, path = tempfile.mkstemp(prefix="led-todoist-ssm-", suffix=".json")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(request, handle, separators=(",", ":"))
        aws(
            [
                "ssm",
                "put-parameter",
                "--cli-input-json",
                "file://" + path,
                "--query",
                "Version",
                "--output",
                "text",
            ],
            region,
            profile,
        )
    finally:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Todoist OAuth for the LED backend")
    parser.add_argument("--client-id", default=os.getenv("TODOIST_CLIENT_ID", ""))
    parser.add_argument("--redirect-uri", default=os.getenv("TODOIST_REDIRECT_URI", DEFAULT_REDIRECT_URI))
    parser.add_argument("--scope", default=DEFAULT_SCOPE)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", DEFAULT_REGION))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE", ""))
    parser.add_argument(
        "--parameter-name",
        default=os.getenv("TODOIST_OAUTH_PARAMETER_NAME", DEFAULT_PARAMETER_NAME),
        help="SSM SecureString parameter name (default: /led/todoist/oauth)",
    )
    parser.add_argument(
        "--migrate-secret-id",
        default="",
        help="Copy OAuth JSON from the previous Secrets Manager secret instead of authorizing again",
    )
    parser.add_argument("--manual", action="store_true", help="Paste the final callback URL instead of starting a localhost listener")
    args = parser.parse_args()

    parameter_name = args.parameter_name.strip()
    if not parameter_name.startswith("/"):
        raise BootstrapError("SSM parameter name must start with /")

    if args.migrate_secret_id.strip():
        payload = load_secrets_manager_secret(args.migrate_secret_id.strip(), args.region, args.profile or None)
        persist_parameter(parameter_name, payload, args.region, args.profile or None)
        print("Todoist OAuth migration completed successfully.")
        print("Credentials and rotating tokens were copied to SSM Parameter Store Standard SecureString:")
        print(parameter_name)
        print("Deploy the SSM-backed LED stack, verify Todoist, then schedule the old Secrets Manager secret for deletion.")
        return

    client_id = args.client_id.strip() or input("Todoist client ID: ").strip()
    client_secret = os.getenv("TODOIST_CLIENT_SECRET", "").strip() or getpass("Todoist client secret: ").strip()
    if not client_id or not client_secret:
        raise BootstrapError("Todoist client ID and client secret are required")

    state = secrets.token_urlsafe(32)
    authorize_url = AUTHORIZE_URL + "?" + urlencode(
        {
            "client_id": client_id,
            "scope": args.scope,
            "state": state,
            "response_type": "code",
            "redirect_uri": args.redirect_uri,
        }
    )

    if args.manual:
        print("Open this Todoist authorization URL:")
        print(authorize_url)
        webbrowser.open(authorize_url)
        callback = input("Paste the complete redirected callback URL: ").strip()
        code = parse_callback(callback, state)
    else:
        code = wait_for_local_callback(args.redirect_uri, state, authorize_url)

    token = exchange_code(client_id, client_secret, code, args.redirect_uri)
    try:
        expires_in = max(1, int(token.get("expires_in") or 3600))
    except (TypeError, ValueError):
        expires_in = 3600
    now = int(time.time())
    parameter_payload = {
        "version": 1,
        "client_id": client_id,
        "client_secret": client_secret,
        "access_token": str(token["access_token"]),
        "refresh_token": str(token["refresh_token"]),
        "token_type": str(token.get("token_type") or "Bearer"),
        "scope": str(token.get("scope") or args.scope),
        "expires_at": now + expires_in,
        "authorized_at": now,
    }
    persist_parameter(parameter_name, parameter_payload, args.region, args.profile or None)
    print("Todoist OAuth bootstrap completed successfully.")
    print("Credentials and rotating tokens were stored in SSM Parameter Store Standard SecureString:")
    print(parameter_name)
    print("You can now set LED_CALENDAR_SOURCE=todoist and deploy the LED stack.")


if __name__ == "__main__":
    try:
        main()
    except BootstrapError as error:
        raise SystemExit("ERROR: " + str(error))
