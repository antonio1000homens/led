#!/usr/bin/env python3
"""Create or update one Cloudflare DNS record without logging credentials."""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API = "https://api.cloudflare.com/client/v4"


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
    parser.add_argument("--zone", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--proxied", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("CF_DEPLOY_API_TOKEN", "").strip()
    if not token:
        raise SystemExit("CF_DEPLOY_API_TOKEN is required")

    zone_name = args.zone.rstrip(".")
    record_name = args.name.rstrip(".")
    content = args.content.rstrip(".")

    zones = request(token, "GET", "/zones?" + urlencode({"name": zone_name, "status": "active"}))
    if not zones:
        raise SystemExit("Cloudflare zone was not found")
    zone_id = zones[0]["id"]

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
