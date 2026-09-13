#!/usr/bin/env python3
"""Create or update one Cloudflare DNS record without logging credentials."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.cloudflare.com/client/v4"
ACCOUNT_ID_RE = re.compile(r"^[0-9a-fA-F]{32}$")


def request(token, method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=20) as response:
        body = json.load(response)
    if not body.get("success"):
        raise RuntimeError("Cloudflare API request failed")
    return body.get("result")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--account-name", default="Windsor")
    parser.add_argument("--zone", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--proxied", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("CF_DEPLOY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("CF_DEPLOY_API_TOKEN is required")

    account_id = args.account_id.strip()
    expected_account_name = args.account_name.strip()
    if not ACCOUNT_ID_RE.fullmatch(account_id):
        raise SystemExit("Cloudflare account ID is invalid")

    zone_name = args.zone.rstrip(".")
    record_name = args.name.rstrip(".")
    content = args.content.rstrip(".")

    zones = request(
        token,
        "GET",
        "/zones?"
        + urlencode(
            {
                "name": zone_name,
                "status": "active",
                "account.id": account_id,
            }
        ),
    )
    if len(zones or []) != 1:
        raise SystemExit("Cloudflare zone was not found in the required account")

    zone = zones[0]
    account = zone.get("account") or {}
    if account.get("id") != account_id:
        raise SystemExit("Cloudflare zone account mismatch")
    if expected_account_name and str(account.get("name") or "").casefold() != expected_account_name.casefold():
        raise SystemExit("Cloudflare zone is not in the Windsor account")

    zone_id = zone["id"]
    query = urlencode({"type": args.type.upper(), "name": record_name})
    records = request(token, "GET", f"/zones/{zone_id}/dns_records?{query}")
    payload = {
        "type": args.type.upper(),
        "name": record_name,
        "content": content,
        "ttl": 1,
        "proxied": bool(args.proxied),
    }
    if records:
        record = records[0]
        if (
            record.get("content", "").rstrip(".") == content
            and bool(record.get("proxied")) == bool(args.proxied)
        ):
            print(f"DNS record already current: {record_name}")
            return
        request(token, "PUT", f"/zones/{zone_id}/dns_records/{record['id']}", payload)
        print(f"Updated DNS record: {record_name}")
    else:
        request(token, "POST", f"/zones/{zone_id}/dns_records", payload)
        print(f"Created DNS record: {record_name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
