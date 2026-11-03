#!/usr/bin/env python3
"""Render the LED R2 Worker config using the same settings as CloudFormation."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

WORKER_DIR = Path(__file__).resolve().parents[1] / "workers" / "led-live-data"
BUCKET_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\Z")
HOST_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+\Z")


def render(bucket: str, domain: str, zone: str) -> str:
    if not BUCKET_PATTERN.fullmatch(bucket):
        raise ValueError("R2 bucket must be 3-63 lowercase letters/digits/hyphens, starting and ending alphanumeric")
    if not HOST_PATTERN.fullmatch(domain) or not HOST_PATTERN.fullmatch(zone):
        raise ValueError("Worker domain and Cloudflare zone must be valid lowercase DNS names")
    if domain != zone and not domain.endswith("." + zone):
        raise ValueError("Worker domain must belong to the configured Cloudflare zone")
    source = (WORKER_DIR / "wrangler.toml").read_text(encoding="utf-8")
    updates = {
        "bucket_name": bucket,
        "pattern": domain + "/api/screens",
        "zone_name": zone,
    }
    for key, value in updates.items():
        source, count = re.subn(
            rf'(?m)^{key} = "[^"]+"$', lambda _: f'{key} = "{value}"', source
        )
        if count != 1:
            raise ValueError(f"Expected exactly one {key} setting in the Wrangler template")
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", default=os.environ.get("LED_R2_BUCKET_NAME", "led-live-state"))
    parser.add_argument("--domain", default=os.environ.get("DOMAIN_NAME", "led.alf-broadcast.co.uk"))
    parser.add_argument("--zone", default=os.environ.get("ZONE_NAME", "alf-broadcast.co.uk"))
    parser.add_argument("--output", type=Path, default=WORKER_DIR / "wrangler.generated.toml")
    args = parser.parse_args()
    try:
        generated = render(args.bucket, args.domain, args.zone)
    except ValueError as exc:
        parser.error(str(exc))
    args.output.write_text(generated, encoding="utf-8")
    print(f"Generated Worker config for {args.domain} using R2 bucket {args.bucket}")


if __name__ == "__main__":
    main()
