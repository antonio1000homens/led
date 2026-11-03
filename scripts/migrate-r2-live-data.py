#!/usr/bin/env python3
"""Seed, verify, or restore the two LED live objects between S3 and R2."""

import argparse
import hashlib
import json
import os
import re
import sys

KEYS = ("state/feed-cache.json", "api/screens")


def make_clients(args):
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise SystemExit("Install boto3 and botocore to use this migration helper") from exc
    s3 = boto3.client("s3", region_name=args.aws_region)
    response = boto3.client("ssm", region_name=args.aws_region).get_parameter(
        Name=args.credentials_parameter, WithDecryption=True
    )
    credentials = json.loads(response["Parameter"]["Value"])
    config_args = {"signature_version": "s3v4"}
    try:
        config = Config(
            **config_args,
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        )
    except TypeError:
        config = Config(**config_args)
    r2 = boto3.client(
        "s3",
        endpoint_url=f"https://{args.account_id}.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id=credentials["access_key_id"],
        aws_secret_access_key=credentials["secret_access_key"],
        config=config,
    )
    return s3, r2


def read_object(client, bucket, key):
    response = client.get_object(Bucket=bucket, Key=key)
    data = response["Body"].read()
    metadata = {name: response[name] for name in ("ContentType", "CacheControl") if response.get(name)}
    return data, metadata


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("seed", "verify", "restore"))
    parser.add_argument("--s3-bucket", default=os.environ.get("STATE_BUCKET"))
    parser.add_argument("--r2-bucket", default=os.environ.get("LED_R2_BUCKET_NAME") or os.environ.get("R2_BUCKET_NAME", "led-live-state"))
    parser.add_argument("--account-id", default=os.environ.get("CLOUDFLARE_ACCOUNT_ID"))
    parser.add_argument("--aws-region", default=os.environ.get("AWS_REGION", "eu-west-2"))
    parser.add_argument("--credentials-parameter", default=os.environ.get(
        "R2_CREDENTIALS_PARAMETER_NAME", "/led/deploy/cloudflare/r2-s3-credentials"))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", args.r2_bucket):
        parser.error("R2 bucket must be 3-63 lowercase letters, digits and hyphens, starting/ending alphanumeric")
    if not args.s3_bucket or not args.account_id:
        parser.error("--s3-bucket/STATE_BUCKET and --account-id/CLOUDFLARE_ACCOUNT_ID are required")
    s3, r2 = make_clients(args)
    source, destination = (s3, r2) if args.action in ("seed", "verify") else (r2, s3)
    source_bucket, destination_bucket = (args.s3_bucket, args.r2_bucket) if source is s3 else (args.r2_bucket, args.s3_bucket)
    mismatches = []
    for key in KEYS:
        data, metadata = read_object(source, source_bucket, key)
        if args.action != "verify":
            params = {"Bucket": destination_bucket, "Key": key, "Body": data, **metadata}
            if destination is s3:
                params["ServerSideEncryption"] = "AES256"
            destination.put_object(**params)
        copied, _ = read_object(destination, destination_bucket, key)
        if digest(data) != digest(copied):
            mismatches.append(key)
        else:
            print(f"{key}: sha256 {digest(data)} matches")
    if mismatches:
        print("Content mismatch: " + ", ".join(mismatches), file=sys.stderr)
        return 1
    print(f"{args.action} complete: {len(KEYS)} live objects verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
