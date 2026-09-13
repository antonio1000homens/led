#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN_NAME="${DOMAIN_NAME:-led.alf-broadcast.co.uk}"
ZONE_NAME="${ZONE_NAME:-alf-broadcast.co.uk}"
ACM_REGION="${ACM_REGION:-us-east-1}"
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:?CLOUDFLARE_ACCOUNT_ID is required and must be the Windsor Cloudflare account ID}"
CLOUDFLARE_ACCOUNT_NAME="Windsor"

if [[ -z "${CF_DEPLOY_API_TOKEN:-}" ]]; then
  echo "CF_DEPLOY_API_TOKEN is required." >&2
  exit 1
fi

upsert_dns() {
  python3 "${ROOT_DIR}/scripts/cloudflare_dns.py" \
    --account-id "${CLOUDFLARE_ACCOUNT_ID}" \
    --account-name "${CLOUDFLARE_ACCOUNT_NAME}" \
    --zone "${ZONE_NAME}" \
    "$@"
}

if [[ -n "${CERTIFICATE_ARN:-}" ]]; then
  read -r VALIDATION_NAME VALIDATION_TYPE VALIDATION_VALUE < <(
    aws acm describe-certificate \
      --region "${ACM_REGION}" \
      --certificate-arn "${CERTIFICATE_ARN}" \
      --query 'Certificate.DomainValidationOptions[0].ResourceRecord.[Name,Type,Value]' \
      --output text
  )
  if [[ -z "${VALIDATION_NAME:-}" || "${VALIDATION_NAME}" == "None" ]]; then
    echo "ACM validation record is not available yet." >&2
    exit 1
  fi
  upsert_dns \
    --name "${VALIDATION_NAME}" \
    --type "${VALIDATION_TYPE}" \
    --content "${VALIDATION_VALUE}"
fi

if [[ -n "${CLOUDFRONT_DOMAIN:-}" ]]; then
  upsert_dns \
    --name "${DOMAIN_NAME}" \
    --type CNAME \
    --content "${CLOUDFRONT_DOMAIN}" \
    --proxied
fi

if [[ -z "${CERTIFICATE_ARN:-}" && -z "${CLOUDFRONT_DOMAIN:-}" ]]; then
  echo "Set CERTIFICATE_ARN and/or CLOUDFRONT_DOMAIN." >&2
  exit 1
fi
