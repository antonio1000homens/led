#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOMAIN_NAME="${DOMAIN_NAME:-led.alf-broadcast.co.uk}"
ZONE_NAME="${ZONE_NAME:-alf-broadcast.co.uk}"
ACM_REGION="${ACM_REGION:-us-east-1}"

if [[ -z "${CF_DEPLOY_API_TOKEN:-}" ]]; then
  echo "CF_DEPLOY_API_TOKEN is required." >&2
  exit 1
fi

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
  python3 "${ROOT_DIR}/scripts/cloudflare_dns.py" \
    --zone "${ZONE_NAME}" \
    --name "${VALIDATION_NAME}" \
    --type "${VALIDATION_TYPE}" \
    --content "${VALIDATION_VALUE}"
fi

if [[ -n "${CLOUDFRONT_DOMAIN:-}" ]]; then
  python3 "${ROOT_DIR}/scripts/cloudflare_dns.py" \
    --zone "${ZONE_NAME}" \
    --name "${DOMAIN_NAME}" \
    --type CNAME \
    --content "${CLOUDFRONT_DOMAIN}"
fi

if [[ -z "${CERTIFICATE_ARN:-}" && -z "${CLOUDFRONT_DOMAIN:-}" ]]; then
  echo "Set CERTIFICATE_ARN and/or CLOUDFRONT_DOMAIN." >&2
  exit 1
fi
